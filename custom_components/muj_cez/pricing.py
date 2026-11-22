"""Invoices of the account parsed into price items, kept for the price breakdown view.

Store `muj_cez.<entry>.invoices`:

  {"invoices": {"<number>": {"agreement": ..., "issued": ..., "invoice": {...}}},
   "failed": {"<number>": "<last try date>"}}

  "pricelists": {"<doc id>": {"ean": ..., "name": ..., "pricelist": {...}}}
  "checked": {"<consumption point uid>": "<date of the last check>"}

Each consumption point (with the production point of its place) is checked per its
period (weekly .. yearly, by default the length of its billing period) and daily during
INVOICE_WATCH_DAYS after its billing period ended until the settlement is stored.

Settlements do not change, so each one is downloaded once: the CSV data file when the
portal has it, else the PDF. Documents without a parseable breakdown are tried again
after RETRY_DAYS. The first run fetches HISTORY_YEARS back (a few requests per invoice).
"""

from __future__ import annotations

import asyncio
import io
import logging
from datetime import date, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.storage import Store
from homeassistant.requirements import async_process_requirements

from . import invoice as inv
from . import invoice_gas as inv_gas
from . import pricelist as pl
from . import pricelist_gas as pl_gas
from .api import CezClient, CezData, CezError, InvoiceSimulation, SupplyPoint
from .const import DOMAIN, INVOICE_PERIOD_DAYS, PYPDF_REQUIREMENT, STORAGE_VERSION

_LOGGER = logging.getLogger(__name__)

HISTORY_YEARS = 4
RETRY_DAYS = 7
REQUEST_PAUSE = 0.5
INVOICE_WATCH_DAYS = 30


def suggested_period(simulation: InvoiceSimulation | None) -> str:
    """Invoice check period fitting the billing period of the point."""
    if simulation is None or not simulation.period_from or not simulation.period_to:
        return "monthly"
    days = (simulation.period_to - simulation.period_from).days
    if days <= 40:
        return "monthly"
    if days <= 100:
        return "quarterly"
    return "yearly"


def invoice_due(
    period: str,
    last_check: date | None,
    today: date,
    period_from: date | None = None,
    settled: bool = False,
) -> bool:
    """Whether the invoices of a point are checked today.

    period_from: start of the current billing period; during INVOICE_WATCH_DAYS after it
    the settlement of the previous one is expected, checked daily until stored.
    """
    if last_check is None:
        return True
    if last_check >= today:
        return False
    if (
        period_from is not None
        and not settled
        and period_from <= today < period_from + timedelta(days=INVOICE_WATCH_DAYS)
    ):
        return True
    return (today - last_check).days >= INVOICE_PERIOD_DAYS.get(period, 30)


def pdf_fragments(data: bytes) -> list[tuple[int, float, float, str]]:
    """Positioned text fragments (page, y, x, text) of all pages (blocking, executor)."""
    from pypdf import PdfReader

    out: list[tuple[int, float, float, str]] = []
    for index, page in enumerate(PdfReader(io.BytesIO(data)).pages):

        def visit(text: str, cm: list[float], tm: list[float], _fd: Any, _fs: Any, i=index) -> None:
            if text.strip():
                x = tm[4] * cm[0] + tm[5] * cm[2] + cm[4]
                y = tm[4] * cm[1] + tm[5] * cm[3] + cm[5]
                out.append((i, round(y, 1), round(x, 1), text))

        page.extract_text(visitor_text=visit)
    return out


def pdf_text(data: bytes) -> str:
    """Text of all pages (blocking, run in the executor)."""
    from pypdf import PdfReader

    return "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(data)).pages)


class InvoiceStore:
    """Parsed settlements of one config entry."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self.hass = hass
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry_id}.invoices"
        )
        self._data: dict[str, Any] | None = None
        self._lock = asyncio.Lock()
        # Consumption points checked by the last async_update.
        self.checked_now: list[str] = []

    async def async_remove(self) -> None:
        """Delete the stored invoices and price lists."""
        await self._store.async_remove()
        self._data = None

    async def _pdf_ready(self) -> bool:
        """Install pypdf on first use (only needed for the price breakdown)."""
        try:
            await async_process_requirements(
                self.hass, DOMAIN, [PYPDF_REQUIREMENT], is_built_in=False
            )
        except HomeAssistantError as err:
            _LOGGER.warning("Cannot install %s for PDF invoices: %s", PYPDF_REQUIREMENT, err)
            return False
        return True

    async def _load(self) -> dict[str, Any]:
        if self._data is None:
            data = await self._store.async_load() or {}
            self._data = {
                "invoices": data.get("invoices") or {},
                "failed": data.get("failed") or {},
                "pricelists": data.get("pricelists") or {},
                "checked": data.get("checked") or {},
            }
        return self._data

    def _settled(self, store: dict[str, Any], agreement: str, since: date | None) -> bool:
        """A settlement of the agreement issued since the date is stored."""
        if since is None:
            return False
        start = since.isoformat()
        return any(
            item.get("agreement") == agreement and str(item.get("issued") or "")[:10] >= start
            for item in store["invoices"].values()
        )

    async def async_update(
        self,
        client: CezClient,
        data: CezData,
        today: date,
        periods: dict[str, str] | None = None,
        only: str | None = None,
    ) -> int:
        """Download and parse new settlements of the points that are due.

        periods: check period per consumption point uid chosen by the user (else the
        suggested one); only: check just this consumption point now (manual refresh).
        Returns the number of newly stored invoices.
        """
        store = await self._load()
        checked: dict[str, str] = store.setdefault("checked", {})
        points = [spd for spd in data.supply_points.values() if spd.supply_point.invoiced]
        due = []
        for spd in points:
            sp = spd.supply_point
            if only is not None:
                if sp.uid == only:
                    due.append(spd)
                continue
            last = checked.get(sp.uid)
            period_from = spd.simulation.period_from if spd.simulation else None
            if invoice_due(
                (periods or {}).get(sp.uid) or suggested_period(spd.simulation),
                date.fromisoformat(last) if last else None,
                today,
                period_from,
                self._settled(store, sp.agreement_id, period_from),
            ):
                due.append(spd)
        self.checked_now = [spd.supply_point.uid for spd in due]
        if not due:
            return 0
        places = {spd.supply_point.place_id for spd in due if spd.supply_point.place_id}
        agreements = {spd.supply_point.agreement_id: "INV" for spd in due}
        gas = {spd.supply_point.agreement_id for spd in due if spd.supply_point.gas}
        for spd in data.supply_points.values():
            sp = spd.supply_point
            if sp.production and sp.agreement_id and sp.place_id in places:
                agreements[sp.agreement_id] = "SLF"
        added = await self._update_invoices(client, agreements, today, gas)
        for spd in due:
            sp = spd.supply_point
            if sp.place_id:
                try:
                    await self._update_pricelists(client, sp, today)
                except CezError as err:
                    _LOGGER.debug("Price lists %s: %s", sp.ean, err)
            checked[sp.uid] = today.isoformat()
        async with self._lock:
            await self._store.async_save(store)
        return added

    async def _update_pricelists(self, client: CezClient, sp: SupplyPoint, today: date) -> None:
        """Download new product price lists (PDF tables) of a consumption point; gas price
        lists by pricelist_gas, electricity ones by pricelist."""
        docs = await client.get_price_lists(sp)
        async with self._lock:
            store = await self._load()
            for doc in docs:
                key = doc["doc_id"]
                if key in store["pricelists"]:
                    continue
                failed = store["failed"].get(f"cen:{key}")
                if failed and date.fromisoformat(failed) > today - timedelta(days=RETRY_DAYS):
                    continue
                data = await client.get_document_pdf(doc["guid"])
                parsed = None
                if data and await self._pdf_ready():
                    fragments = await self.hass.async_add_executor_job(pdf_fragments, data)
                    parsed = (pl_gas if sp.gas else pl).parse(fragments)
                if parsed is None:
                    store["failed"][f"cen:{key}"] = today.isoformat()
                else:
                    store["failed"].pop(f"cen:{key}", None)
                    store["pricelists"][key] = {
                        "ean": sp.ean,
                        "name": doc.get("name"),
                        "valid_from": doc.get("valid_from"),
                        "pricelist": parsed.as_dict(),
                    }
                await self._store.async_save(store)
                await asyncio.sleep(REQUEST_PAUSE)

    async def async_pricelists(self, ean: str) -> list[pl.PriceList]:
        store = await self._load()
        return [
            pl.PriceList.from_dict(item["pricelist"])
            for item in store["pricelists"].values()
            if item.get("ean") == ean and item["pricelist"].get("commodity") != "gas"
        ]

    async def async_gas_pricelists(self, ean: str) -> list[pl_gas.GasPriceList]:
        store = await self._load()
        return [
            pl_gas.GasPriceList.from_dict(item["pricelist"])
            for item in store["pricelists"].values()
            if item.get("ean") == ean and item["pricelist"].get("commodity") == "gas"
        ]

    async def _update_invoices(
        self,
        client: CezClient,
        agreements: dict[str, str],
        today: date,
        gas: set[str] | None = None,
    ) -> int:
        async with self._lock:
            store = await self._load()
            rows = await client.get_invoice_rows(date(today.year - HISTORY_YEARS, 1, 1))
            added = 0
            for row in rows:
                number = row["billingReceivablesAndPayablesAccountDocumentNumber"]
                agreement = row.get("agreementIdIsu")
                if agreements.get(agreement) != row.get("billingAccountingDocumentType2"):
                    continue
                if number in store["invoices"]:
                    continue
                failed = store["failed"].get(number)
                if failed and date.fromisoformat(failed) > today - timedelta(days=RETRY_DAYS):
                    continue
                try:
                    parsed = await self._fetch(client, number, row, agreement in (gas or ()))
                except CezError as err:
                    _LOGGER.debug("Invoice %s: %s", number, err)
                    parsed = None
                if parsed is None or not parsed.items:
                    store["failed"][number] = today.isoformat()
                else:
                    store["failed"].pop(number, None)
                    type_text = row.get("billingAccountingDocumentTypeText")
                    if issued := row.get("billingAccountingDocumentDate"):
                        parsed.issued = date.fromisoformat(issued[:10])
                    parsed.corrective = parsed.corrective or inv.is_corrective_type(type_text)
                    store["invoices"][number] = {
                        "agreement": agreement,
                        "issued": issued,
                        "type": type_text,
                        "invoice": parsed.as_dict(),
                    }
                    added += 1
                await self._store.async_save(store)
                await asyncio.sleep(REQUEST_PAUSE)
            return added

    async def _fetch(
        self, client: CezClient, number: str, row: dict[str, Any], gas: bool = False
    ) -> inv.Invoice | None:
        """Parsed settlement: gas invoices by invoice_gas (PDF only), electricity by invoice."""
        if gas:
            data = await client.get_invoice_pdf(row)
            if not data or not await self._pdf_ready():
                return None
            text = await self.hass.async_add_executor_job(pdf_text, data)
            return inv_gas.parse_pdf_text(number, text)
        if row.get("billingAccountingDocumentType2") == "INV":
            text = await client.get_invoice_csv(row)
            if text:
                parsed = inv.parse_csv(number, text)
                if parsed.items:
                    return parsed
        data = await client.get_invoice_pdf(row)
        if not data or not await self._pdf_ready():
            return None
        text = await self.hass.async_add_executor_job(pdf_text, data)
        if inv.is_payout_text(text):
            return inv.parse_payout_pdf_text(number, text)
        return inv.parse_pdf_text(number, text)

    async def async_invoices(self, agreements: set[str]) -> list[inv.Invoice]:
        store = await self._load()
        result = []
        for item in store["invoices"].values():
            if item.get("agreement") not in agreements:
                continue
            parsed = inv.Invoice.from_dict(item["invoice"])
            # Entries stored by the first version keep the date and type in the wrapper only.
            if parsed.issued is None and item.get("issued"):
                parsed.issued = date.fromisoformat(item["issued"][:10])
            parsed.corrective = parsed.corrective or inv.is_corrective_type(item.get("type"))
            result.append(parsed)
        return result
