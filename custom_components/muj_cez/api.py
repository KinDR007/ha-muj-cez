"""Client for the Muj CEZ customer portal API (muj.cez.cz).

Independent of Home Assistant so it can be tested and used standalone.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import re
import secrets
import time
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any
from urllib.parse import parse_qs, urljoin, urlparse

import aiohttp

from . import grid as gridlib

_LOGGER = logging.getLogger(__name__)

BASE_URL = "https://muj.cez.cz"
CONFIG_URL = f"{BASE_URL}/col/config.js"
REDIRECT_URI = f"{BASE_URL}/col"
DEFAULT_AUTHORIZE_URL = "https://auth.cez.cz/oauth2/authorize"
DEFAULT_TOKEN_URL = "https://api.cez.cz/token"
DEFAULT_API_URL = f"{BASE_URL}/col-api/prod/1.0"
PARTNER_HEADER = "X-COL-PARTNER"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
TIMEOUT = aiohttp.ClientTimeout(total=60)
MAX_REDIRECTS = 15
TOKEN_EXPIRY_MARGIN = 60

# Meter reading type used by the portal for simulated (future) readings.
SIMULATED_READING_TYPE = "Odečet pro použití v simulaci faktury"

# Smart meter data: re-check availability monthly, re-fetch last days (late corrections).
GRID_RECHECK_DAYS = 30
GRID_REFETCH_DAYS = 3


class CezError(Exception):
    """Base error."""


class CezAuthError(CezError):
    """Invalid credentials or rejected login."""


class CezConnectionError(CezError):
    """Network or unexpected server response."""


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class SupplyPoint:
    uid: str
    ean: str
    name: str
    address: str
    product: str
    commodity: str
    advance_amount: float | None
    advance_frequency: str | None
    agreement_id: str = ""
    continuous_measurement: bool | None = None
    electronic_invoicing: str | None = None
    # Production supply point (PV feed-in, monthly payout) instead of consumption.
    production: bool = False
    # Consumption place shared by the consumption and production point of one address.
    place_id: str = ""
    # Raw supply point code as used in API paths (may carry a suffix, e.g. "  SV").
    code: str = ""


@dataclass
class InvoiceSimulation:
    total_amount: float | None
    cost_with_tax: float | None
    cost_without_tax: float | None
    recommended_advance: float | None
    period_from: date | None
    period_to: date | None
    consumption_kwh: float | None
    consumption_measured_kwh: float | None
    consumption_estimated_kwh: float | None
    calculated_at: str | None
    customer_number: str | None = None
    # Last day covered by real meter readings; later consumption is estimated.
    measured_until: date | None = None
    # Variable price per kWh incl. VAT by register ("VT", "NT") from the latest item.
    unit_prices: dict[str, float] = field(default_factory=dict)


@dataclass
class AdvancePlan:
    next_due_date: date | None
    next_amount: float | None
    unpaid_amount: float
    paid_count: int
    total_count: int
    items: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ConsumptionPeriod:
    date_from: date | None
    date_to: date | None
    consumption_kwh: float | None
    consumption_ht_kwh: float | None
    consumption_lt_kwh: float | None
    amount: float | None


@dataclass
class MeterReading:
    reading_date: date | None
    value_ht: float | None
    value_lt: float | None
    reading_type: str | None
    device: str | None


@dataclass
class ContractInfo:
    tariff_code: str | None
    circuit_breaker: float | None
    phase: int | None
    product: str | None
    contract_end: date | None
    price_change_date: date | None
    double_tariff: bool | None
    distribution_rate: str | None = None
    recommended_distribution_rate: str | None = None


@dataclass
class AdvanceSettings:
    is_sipo: bool | None
    min_amount: float | None
    max_amount: float | None
    remaining_payments: int | None
    variable_symbol: str | None = None
    bank_account: str | None = None


@dataclass
class BillingDocument:
    doc_type: str
    number: str | None
    issue_date: date | None
    due_date: date | None
    amount: float | None
    agreement_id: str = ""
    contract_name: str | None = None
    variable_symbol: str | None = None
    balance: float = 0.0
    settlement_date: date | None = None

    @property
    def event_date(self) -> date | None:
        """Date shown in the calendar: due date, else issue date."""
        return self.due_date or self.issue_date

    @property
    def is_invoice(self) -> bool:
        return self.doc_type.startswith("Faktura")

    @property
    def is_payment(self) -> bool:
        return self.doc_type == "Platba"

    def as_dict(self) -> dict[str, Any]:
        return {
            "type": self.doc_type,
            "number": self.number,
            "contract": strip_zeros(self.agreement_id),
            "contract_name": self.contract_name,
            "issue_date": self.issue_date.isoformat() if self.issue_date else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "settlement_date": self.settlement_date.isoformat() if self.settlement_date else None,
            "amount": self.amount,
            "balance": self.balance,
            "variable_symbol": self.variable_symbol,
        }


@dataclass
class BillingPeriod:
    """One billing (settlement) period; the current one is predicted."""

    date_from: date | None
    date_to: date | None
    consumption_kwh: float | None
    cost: float | None
    paid: float | None
    settlement: float | None
    settlement_date: date | None
    predicted: bool = False
    # Advances for the whole period: closed = credited in the settlement (cost - settlement),
    # current = advance plan total; remaining = still to be paid in the current period.
    advances_total: float | None = None
    advances_remaining: float | None = None
    advances_remaining_count: int | None = None
    # Amount of one remaining advance when all remaining advances are equal.
    advances_installment: float | None = None

    @property
    def avg_price(self) -> float | None:
        if self.cost is None or not self.consumption_kwh:
            return None
        return round(self.cost / self.consumption_kwh, 2)

    def as_dict(self) -> dict[str, Any]:
        return {
            "from": self.date_from.isoformat() if self.date_from else None,
            "to": self.date_to.isoformat() if self.date_to else None,
            "consumption_kwh": self.consumption_kwh,
            "cost": self.cost,
            "paid": self.paid,
            "settlement": self.settlement,
            "settlement_date": self.settlement_date.isoformat() if self.settlement_date else None,
            "avg_price": self.avg_price,
            "predicted": self.predicted,
            "advances_total": self.advances_total,
            "advances_remaining": self.advances_remaining,
            "advances_remaining_count": self.advances_remaining_count,
            "advances_installment": self.advances_installment,
        }


@dataclass
class BillingSummary:
    last_invoice: BillingDocument | None
    last_payment: BillingDocument | None
    overdue_amount: float
    open_amount: float


@dataclass
class Outage:
    start_date: date | None
    start_time: str | None
    end: str | None
    reason: str | None
    cancelled: bool


@dataclass
class MonthValue:
    """One month of the current billing period as split by the portal simulation."""

    date_from: date
    date_to: date
    consumption_kwh: float | None
    cost: float | None
    estimated: bool

    @property
    def month(self) -> str:
        return self.date_from.strftime("%Y-%m")


@dataclass
class SimulationItem:
    """One simulation invoice item: energy VT / NT (MWh) or fixed monthly charges."""

    date_from: date
    date_to: date
    kind: str  # "vt", "nt" or "fixed"
    mwh: float
    amount: float  # without VAT
    amount_with_tax: float


@dataclass
class MeterReadingPoint:
    reading_date: date
    value: float
    reading_type: str | None
    device: str | None = None


@dataclass
class Payout:
    """Monthly payout for energy fed into the grid (production supply point)."""

    date_from: date
    date_to: date
    amount: float | None

    @property
    def month(self) -> str:
        return self.date_from.strftime("%Y-%m")


@dataclass
class SupplyPointData:
    supply_point: SupplyPoint
    simulation: InvoiceSimulation | None = None
    advance_plan: AdvancePlan | None = None
    last_period: ConsumptionPeriod | None = None
    meter_reading: MeterReading | None = None
    contract: ContractInfo | None = None
    advance_settings: AdvanceSettings | None = None
    billing: BillingSummary | None = None
    outages: list[Outage] | None = None
    periods: list[BillingPeriod] | None = None
    months: list[MonthValue] | None = None
    readings: list[MeterReadingPoint] | None = None
    payouts: list[Payout] | None = None
    # Simulation invoice items of the current billing period (price breakdown).
    sim_items: list[SimulationItem] | None = None


@dataclass
class CezData:
    supply_points: dict[str, SupplyPointData]
    unread_messages: int | None = None
    # All accounting documents of all contracts on the account, sorted by event date.
    documents: list[BillingDocument] = field(default_factory=list)
    # Per supply point uid: comparison with the HA reference sensor (filled by coordinator).
    comparison: dict[str, dict[str, Any]] = field(default_factory=dict)
    # Per consumption place id: smart meter grid import/export summary (filled by coordinator).
    grid: dict[str, dict[str, Any]] = field(default_factory=dict)
    # Per EAN: HDO schedule from the ČEZ Distribuce portal (filled by coordinator).
    hdo: dict[str, dict[str, Any]] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Parsing (pure functions)
# ---------------------------------------------------------------------------


def _val(obj: Any) -> Any:
    """Unwrap a CodebookEntryDto ({"@class": ..., "value": ...})."""
    if isinstance(obj, dict):
        return obj.get("value")
    return obj


def _float(obj: Any) -> float | None:
    if obj is None or obj == "":
        return None
    try:
        return float(obj)
    except (TypeError, ValueError):
        return None


def strip_zeros(value: Any) -> str | None:
    """Strip leading zeros from SAP identifiers ("000012345678" -> "12345678")."""
    if value is None:
        return None
    text = str(value).strip().lstrip("0")
    return text or None


def _date(obj: Any) -> date | None:
    if not obj or not isinstance(obj, str):
        return None
    try:
        return date.fromisoformat(obj[:10])
    except ValueError:
        return None


def parse_supply_points(data: list[dict[str, Any]]) -> list[SupplyPoint]:
    result = []
    for sp in data or []:
        uid = sp.get("supplyPointUniqueId")
        code = str(sp.get("supplyPointCode") or "")
        # Production points have a suffix ("859182400512345678  SV").
        ean = code.split()[0] if code.split() else ""
        if not uid or not ean:
            continue
        sp_type = sp.get("supplyPointType")
        production = (
            isinstance(sp_type, dict)
            and (sp_type.get("entrySystemSpecificId") == "VYR" or sp_type.get("value") == "Výroba")
        ) or code.rstrip().endswith(" SV")
        addr = sp.get("address") or {}
        street = _val(addr.get("addressStreet")) or ""
        number = addr.get("addressLandRegistryNumber") or ""
        if addr.get("addressHouseNumber"):
            number = f"{number}/{addr['addressHouseNumber']}"
        city = _val(addr.get("addressCity")) or ""
        address = ", ".join(p for p in (f"{street} {number}".strip(), city) if p)
        contract = sp.get("contract") or {}
        result.append(
            SupplyPoint(
                uid=uid,
                ean=ean,
                name=_supply_point_name(
                    sp.get("consumptionPlaceName")
                    or contract.get("contractName")
                    or address
                    or ean,
                    production,
                ),
                address=address,
                product=sp.get("Product") or "",
                commodity=_val(sp.get("supplyPointCommodity")) or "",
                advance_amount=_float(contract.get("contractAdvancePaymentAmount")),
                advance_frequency=_val(contract.get("contractAdvancePaymentFrequency")),
                agreement_id=(sp.get("agreement") or {}).get("agreementIdIsu") or "",
                continuous_measurement=sp.get("supplyPointIsContinuousMeasurement"),
                electronic_invoicing=(sp.get("agreement") or {}).get(
                    "agreementElectronicInvoicingTypeId"
                ),
                production=production,
                place_id=str(sp.get("consumptionPlaceIdIsu") or ""),
                code=code,
            )
        )
    return result


def _supply_point_name(name: str, production: bool) -> str:
    return f"{name} výroba" if production else name


def parse_payouts(data: list[dict[str, Any]]) -> list[Payout]:
    """Monthly payouts of a production point (consumption history holds CZK, kWh are 0)."""
    result = []
    for row in data if isinstance(data, list) else []:
        start, end = _date(row.get("dateFrom")), _date(row.get("dateTo"))
        if start is None or end is None:
            continue
        result.append(
            Payout(date_from=start, date_to=end, amount=_float(row.get("consumptionAmount")))
        )
    return sorted(result, key=lambda p: p.date_from)


def parse_simulation(data: dict[str, Any]) -> InvoiceSimulation | None:
    if not data or not isinstance(data, dict):
        return None
    header = (data.get("invoiceSimulationDetailHeader") or [{}])[0]
    items = data.get("invoiceSimulationInvoiceItem") or []
    consumption = data.get("invoiceSimulationConsumption") or []

    def _sum(rows: list[dict[str, Any]], key: str) -> float | None:
        vals = [_float(r.get(key)) for r in rows]
        vals = [v for v in vals if v is not None]
        return round(sum(vals), 2) if vals else None

    estimated = [r for r in consumption if "odhad" in str(_val(r.get("meterReadingKind"))).lower()]
    measured = [r for r in consumption if r not in estimated]
    return InvoiceSimulation(
        total_amount=_float(header.get("invoiceSimulationTotalAmount")),
        cost_with_tax=_sum(items, "invoiceItemAmountWithTax"),
        cost_without_tax=_sum(items, "invoiceItemAmountWithoutTax"),
        recommended_advance=_float(data.get("invoiceSimulationFirstRecommendedAdvancePayment")),
        period_from=_date(data.get("invoiceSimulationBillingPeriodFrom")),
        period_to=_date(data.get("invoiceSimulationBillingPeriodTo")),
        consumption_kwh=_sum(consumption, "consumptionValue"),
        consumption_measured_kwh=_sum(measured, "consumptionValue"),
        consumption_estimated_kwh=_sum(estimated, "consumptionValue"),
        calculated_at=data.get("invoiceSimulationOriginDate"),
        customer_number=strip_zeros(
            ((data.get("invoiceSimulationShort") or [{}])[0]).get("partnerIdCrm")
        ),
        measured_until=max(
            (d for d in (_date(r.get("consumptionPeriodTo")) for r in measured) if d),
            default=None,
        ),
        unit_prices=parse_unit_prices(items),
    )


def parse_unit_prices(items: list[dict[str, Any]]) -> dict[str, float]:
    """Price per kWh with VAT of the latest energy item of each register (VT / NT).

    Energy items cover energy, distribution and other per-kWh charges, so this is the
    price of one more kWh in that tariff (fixed monthly fees excluded).
    """
    latest: dict[str, tuple[date, float]] = {}
    for item in items:
        kind = str(_val(item.get("invoiceItemType")) or "")
        if not kind.startswith(ENERGY_ITEM_PREFIX):
            continue
        register = kind.removeprefix(ENERGY_ITEM_PREFIX).strip()
        unit = _val(item.get("invoiceItemInvoiceQuantityUnit")) or "Megawatthodina"
        kwh = (_float(item.get("invoiceItemConsumption")) or 0.0) * UNIT_FACTORS.get(unit, 1000.0)
        amount = _float(item.get("invoiceItemAmountWithTax"))
        end = _date(item.get("invoiceItemPeriodTo")) or date.min
        if register not in ("VT", "NT") or kwh <= 0 or amount is None:
            continue
        if register not in latest or end >= latest[register][0]:
            latest[register] = (end, round(amount / kwh, 4))
    return {register: price for register, (_end, price) in latest.items()}


ENERGY_ITEM_PREFIX = "Zúčtování spotřeby"
UNIT_FACTORS = {"Megawatthodina": 1000.0, "Kilowatthodina": 1.0}


# Settlement document types: consumption invoice, payout self-billing (production point).
INVOICE_TYPES = ("INV", "SLF")


def invoice_filter(row: dict[str, Any]) -> dict[str, Any]:
    """Document filter of a settlement as the portal builds it (billings/extended row).

    Header and snapshot ids of a document change over time, so the row must be fresh.
    """
    rtt = row.get("billingSourceSystem") == "RTT"
    params = [
        ("PARTNER_ID_CRM", row.get("partnerIdCrm")),
        ("HEADER_ID", str(row.get("billingAccountingDocumentHeaderId"))),
        ("ACCOUNT_DOCUMENT_NUMBER", row.get("billingReceivablesAndPayablesAccountDocumentNumber")),
        ("SNAPSHOT_ID", row.get("billingBalanceSnapshotId")),
        ("CONTRACT_ID_ISU", row.get("agreementIdIsu")),
        ("SOURCE_SYSTEM", "SAP_R3_RT130" if rtt else "SAP_R3_RQ140"),
    ]
    return {
        "documentDomain": "INVOICES",
        "documentParams": [{"key": k, "value": v} for k, v in params],
    }


SIM_ITEM_KINDS = {"ZUCT_SPOTR_VT": "vt", "ZUCT_SPOTR_NT": "nt", "ZUCT_STAL_PLAT_EE": "fixed"}


def parse_simulation_items(data: Any) -> list[SimulationItem]:
    """Simulation items with amounts (zero "other items" rows are left out)."""
    if not isinstance(data, dict):
        return []
    items = []
    for item in data.get("invoiceSimulationInvoiceItem") or []:
        code = item.get("invoiceItemType")
        kind = SIM_ITEM_KINDS.get(code.get("entryId", "") if isinstance(code, dict) else "")
        start = _date(item.get("invoiceItemPeriodFrom"))
        end = _date(item.get("invoiceItemPeriodTo"))
        if not kind or not start or not end:
            continue
        unit = _val(item.get("invoiceItemInvoiceQuantityUnit")) or "Megawatthodina"
        qty = (_float(item.get("invoiceItemConsumption")) or 0.0) * UNIT_FACTORS.get(unit, 1000.0)
        items.append(
            SimulationItem(
                date_from=start,
                date_to=end,
                kind=kind,
                mwh=round(qty / 1000, 6),
                amount=_float(item.get("invoiceItemAmountWithoutTax")) or 0.0,
                amount_with_tax=_float(item.get("invoiceItemAmountWithTax")) or 0.0,
            )
        )
    return sorted(items, key=lambda i: (i.date_from, i.kind))


def parse_simulation_months(data: dict[str, Any]) -> list[MonthValue]:
    """Monthly split of the current billing period from simulation invoice items.

    Consumption comes from energy items ("Zúčtování spotřeby VT/NT", MWh); cost is the
    sum of all items of the month including fixed fees, with VAT. A month is estimated
    when it ends after the last real meter reading.
    """
    if not isinstance(data, dict):
        return []
    sim = parse_simulation(data)
    measured_until = sim.measured_until if sim else None
    months: dict[tuple[date, date], dict[str, float]] = {}
    for item in data.get("invoiceSimulationInvoiceItem") or []:
        start = _date(item.get("invoiceItemPeriodFrom"))
        end = _date(item.get("invoiceItemPeriodTo"))
        if not start or not end:
            continue
        acc = months.setdefault((start, end), {"kwh": 0.0, "cost": 0.0, "has_kwh": 0.0})
        acc["cost"] += _float(item.get("invoiceItemAmountWithTax")) or 0.0
        if str(_val(item.get("invoiceItemType")) or "").startswith(ENERGY_ITEM_PREFIX):
            unit = _val(item.get("invoiceItemInvoiceQuantityUnit")) or "Megawatthodina"
            qty = _float(item.get("invoiceItemConsumption")) or 0.0
            acc["kwh"] += qty * UNIT_FACTORS.get(unit, 1000.0)
            acc["has_kwh"] = 1.0
    return [
        MonthValue(
            date_from=start,
            date_to=end,
            consumption_kwh=round(acc["kwh"], 1) if acc["has_kwh"] else None,
            cost=round(acc["cost"], 2),
            estimated=measured_until is None or end > measured_until,
        )
        for (start, end), acc in sorted(months.items())
    ]


def parse_advance_plan(data: list[dict[str, Any]], today: date) -> AdvancePlan | None:
    if not isinstance(data, list):
        return None
    items = []
    for row in data:
        due = _date(row.get("splatnost"))
        items.append(
            {
                "due_date": due,
                "amount": _float(row.get("castka")),
                "unpaid": _float(row.get("kDoplaceni")) or 0.0,
                "state": row.get("stavText"),
                "paid": row.get("stav") == 1,
            }
        )
    items.sort(key=lambda i: i["due_date"] or date.max)
    upcoming = [i for i in items if i["due_date"] and i["due_date"] >= today and not i["paid"]]
    nxt = upcoming[0] if upcoming else None
    return AdvancePlan(
        next_due_date=nxt["due_date"] if nxt else None,
        next_amount=nxt["amount"] if nxt else None,
        unpaid_amount=round(
            sum(i["unpaid"] for i in items if i["due_date"] and i["due_date"] < today), 2
        ),
        paid_count=sum(1 for i in items if i["paid"]),
        total_count=len(items),
        items=items,
    )


def parse_consumption_periods(data: list[dict[str, Any]]) -> list[ConsumptionPeriod]:
    if not isinstance(data, list):
        return []
    result = [
        ConsumptionPeriod(
            date_from=_date(r.get("dateFrom")),
            date_to=_date(r.get("dateTo")),
            consumption_kwh=_float(r.get("consumptionSum")),
            consumption_ht_kwh=_float(r.get("consumptionHT")),
            consumption_lt_kwh=_float(r.get("consumptionLT")),
            amount=_float(r.get("consumptionAmount")),
        )
        for r in data
        if isinstance(r, dict)
    ]
    result.sort(key=lambda p: p.date_to or date.min)
    return result


def parse_consumption_history(data: list[dict[str, Any]]) -> ConsumptionPeriod | None:
    """Latest closed billing period."""
    periods = parse_consumption_periods(data)
    return periods[-1] if periods else None


def parse_accounts(data: Any) -> tuple[list[str], str | None]:
    """Customer accounts (partner ids) and the default one from /user/token-data."""
    if not isinstance(data, dict):
        return [], None
    partners = [str(p) for p in data.get("partners") or [] if p]
    default = data.get("defaultPartner")
    return partners, str(default) if default else None


def parse_meter_reading_history(data: list[dict[str, Any]], today: date) -> list[MeterReadingPoint]:
    """Real (non-simulated) readings up to today, one per day, oldest first.

    The value is the total of all registers (VT + NT for dual tariff). A day is used
    only when every register the meter has is read that day, so the total is
    comparable between readings. Zero values are skipped; when several reading types
    exist for a day (distributor and self reading), the distributor one wins.
    """
    if not isinstance(data, list):
        return []
    # (day, device, reading type) -> {register: value}
    groups: dict[tuple[date, str, str | None], dict[str, float]] = {}
    registers: dict[str, set[str]] = {}
    for row in data:
        if not isinstance(row, dict):
            continue
        rtype = _val(row.get("meterReadingType"))
        tariff = str(_val(row.get("meterReadingTariff")) or "")
        register = "VT" if "VT" in tariff else "NT" if "NT" in tariff else None
        if rtype == SIMULATED_READING_TYPE or register is None:
            continue
        day = _date(row.get("meterReadingRegisterDate"))
        value = _float(row.get("meterReadingValue"))
        if day is None or day > today or not value:
            continue
        device = (row.get("meterReadingDeviceNumber") or "").lstrip("0")
        groups.setdefault((day, device, rtype), {})[register] = value
        registers.setdefault(device, set()).add(register)
    by_day: dict[date, MeterReadingPoint] = {}
    for (day, device, rtype), values in sorted(groups.items(), key=lambda g: g[0][0]):
        if set(values) != registers[device]:
            continue
        current = by_day.get(day)
        if current is None or "distributor" in str(rtype):
            by_day[day] = MeterReadingPoint(
                reading_date=day,
                value=round(sum(values.values()), 3),
                reading_type=rtype,
                device=device or None,
            )
    return [by_day[d] for d in sorted(by_day)]


def parse_register_readings(
    data: list[dict[str, Any]], today: date
) -> tuple[dict[str, list[tuple[date, float]]], str | None]:
    """Real readings per register ({"vt": [(day, kWh)], "nt": [...]}, oldest first) of the
    current meter and its number. Readings of a replaced meter are left out, as is a
    register whose latest reading is 0 (NT of a single tariff meter)."""
    rows: list[tuple[str, date, float, str]] = []
    for row in data if isinstance(data, list) else []:
        if not isinstance(row, dict) or _val(row.get("meterReadingType")) == SIMULATED_READING_TYPE:
            continue
        tariff = str(_val(row.get("meterReadingTariff")) or "")
        register = "vt" if "VT" in tariff else "nt" if "NT" in tariff else None
        day = _date(row.get("meterReadingRegisterDate"))
        value = _float(row.get("meterReadingValue"))
        if register is None or day is None or day > today or value is None:
            continue
        rows.append((register, day, value, (row.get("meterReadingDeviceNumber") or "").lstrip("0")))
    device = max(((d, dev) for _r, d, _v, dev in rows if dev), default=(None, None))[1]
    out: dict[str, dict[date, float]] = {}
    for register, day, value, dev in rows:
        if dev and dev != device:
            continue
        values = out.setdefault(register, {})
        values[day] = max(values.get(day, 0.0), value)
    return {reg: sorted(v.items()) for reg, v in out.items() if v[max(v)] > 0}, device


def parse_meter_readings(data: list[dict[str, Any]], today: date) -> MeterReading | None:
    """Return the latest real (non-simulated) reading not later than today.

    VT and NT registers are separate rows with the same date. A row with value 0
    is ignored when a non-zero reading exists for the same register on an
    earlier date (self-readings sometimes report 0 for an unused register).
    """
    if not isinstance(data, list):
        return None
    real = []
    for row in data:
        if _val(row.get("meterReadingType")) == SIMULATED_READING_TYPE:
            continue
        d = _date(row.get("meterReadingRegisterDate"))
        if d is None or d > today:
            continue
        real.append((d, row))
    if not real:
        return None

    def latest(register: str) -> tuple[date, dict[str, Any]] | None:
        rows = [(d, r) for d, r in real if register in str(_val(r.get("meterReadingTariff")))]
        nonzero = [(d, r) for d, r in rows if (_float(r.get("meterReadingValue")) or 0) > 0]
        pool = nonzero or rows
        return max(pool, key=lambda x: x[0]) if pool else None

    ht = latest("VT")
    lt = latest("NT")
    ref = ht or lt
    if ref is None:
        return None
    lt_value = _float(lt[1].get("meterReadingValue")) if lt else None
    return MeterReading(
        reading_date=ref[0],
        value_ht=_float(ht[1].get("meterReadingValue")) if ht else None,
        value_lt=lt_value if lt_value else None,
        reading_type=_val(ref[1].get("meterReadingType")),
        device=(ref[1].get("meterReadingDeviceNumber") or "").lstrip("0") or None,
    )


def parse_contract_info(
    data: dict[str, Any], rate: dict[str, Any] | None = None
) -> ContractInfo | None:
    """Combine product-calculator supply point detail and distribution rate banner."""
    if not isinstance(data, dict):
        data = {}
    rate = rate if isinstance(rate, dict) else {}
    if not data and not rate:
        return None
    phase = data.get("phase")
    return ContractInfo(
        tariff_code=data.get("tariffType") or None,
        circuit_breaker=_float(data.get("circuitBreakerValue")),
        phase=phase if isinstance(phase, int) else None,
        product=data.get("productCrm") or None,
        contract_end=_date(data.get("contractPlannedEndDate")),
        price_change_date=_date(data.get("priceIncreaseDate")),
        double_tariff=data.get("hasDoubleTariff"),
        distribution_rate=_val(rate.get("currentSupplyPointDistributionRate")) or None,
        recommended_distribution_rate=_val(rate.get("recommendedSupplyPointDistributionRate"))
        or None,
    )


def parse_advance_settings(
    settings: dict[str, Any], events: list[dict[str, Any]] | None = None
) -> AdvanceSettings | None:
    if not isinstance(settings, dict) or not settings:
        return None
    event = events[0] if isinstance(events, list) and events else {}
    account = event.get("bankAccountFullNumber")
    bank = _val(event.get("bankAccountBankCode"))
    remaining = settings.get("advancePaymentChangeRemainingPayments")
    return AdvanceSettings(
        is_sipo=settings.get("isSipo"),
        min_amount=_float(settings.get("advancePaymentChangeFromLimit")),
        max_amount=_float(settings.get("advancePaymentChangeToLimit")),
        remaining_payments=remaining if isinstance(remaining, int) else None,
        variable_symbol=event.get("paymentPrescriptionVariableSymbol") or None,
        bank_account=f"{account}/{bank}" if account and bank else None,
    )


def parse_documents(
    data: list[dict[str, Any]], contract_names: dict[str, str] | None = None
) -> list[BillingDocument]:
    """All accounting documents (all contracts, all types), sorted by event date.

    Amount: invoices carry `billingTotalAmount` (negative = refund to customer);
    other documents carry `billingEColClearingAmount`. Payments are returned as
    positive amounts paid by the customer.
    """
    if not isinstance(data, list):
        return []
    names = contract_names or {}
    docs = []
    for row in data:
        if not isinstance(row, dict):
            continue
        doc_type = row.get("billingAccountingDocumentTypeText") or ""
        total = _float(row.get("billingTotalAmount"))
        clearing = _float(row.get("billingEColClearingAmount"))
        if doc_type == "Platba" and clearing is not None:
            amount: float | None = -clearing
        elif total:
            amount = total
        else:
            amount = clearing
        agreement = row.get("agreementIdIsu") or ""
        docs.append(
            BillingDocument(
                doc_type=doc_type,
                number=row.get("billingAccountingDocumentNumber") or None,
                issue_date=_date(row.get("billingAccountingDocumentDate")),
                due_date=_date(row.get("billingMaturityDate")),
                amount=amount,
                agreement_id=agreement,
                contract_name=names.get(agreement)
                or (f"Smlouva {strip_zeros(agreement)}" if strip_zeros(agreement) else None),
                variable_symbol=row.get("billingVariableSymbol") or None,
                balance=_float(row.get("billingBalance")) or 0.0,
                settlement_date=_date(row.get("billingSettlementDate")),
            )
        )
    docs.sort(key=lambda d: (d.event_date or date.min, d.number or ""))
    return docs


def summarize_billing(
    docs: list[BillingDocument], agreement_id: str, today: date
) -> BillingSummary | None:
    """Summarize accounting documents of one agreement (contract account)."""
    rows = [d for d in docs if d.agreement_id == agreement_id]
    if not rows:
        return None

    def newest(items: list[BillingDocument]) -> BillingDocument | None:
        return max(items, key=lambda d: d.issue_date or date.min, default=None)

    overdue = open_ = 0.0
    for d in rows:
        if d.balance <= 0:
            continue
        open_ += d.balance
        if d.due_date and d.due_date < today:
            overdue += d.balance
    return BillingSummary(
        last_invoice=newest([d for d in rows if d.is_invoice]),
        last_payment=newest([d for d in rows if d.is_payment and (d.amount or 0) > 0]),
        overdue_amount=round(overdue, 2),
        open_amount=round(open_, 2),
    )


def parse_billings(
    data: list[dict[str, Any]], agreement_id: str, today: date
) -> BillingSummary | None:
    if not isinstance(data, list):
        return None
    return summarize_billing(parse_documents(data), agreement_id, today)


# Invoice settling a period is issued shortly after the period ends.
SETTLEMENT_WINDOW_DAYS = 90


def build_billing_periods(
    history: list[ConsumptionPeriod],
    docs: list[BillingDocument],
    agreement_id: str,
    simulation: InvoiceSimulation | None,
    advance_plan: AdvancePlan | None = None,
) -> list[BillingPeriod]:
    """Closed periods from consumption history + documents, plus the predicted current one.

    paid: customer payments dated within the period (approximation of advances paid).
    settlement: first invoice issued within SETTLEMENT_WINDOW_DAYS after period end
    (negative = overpayment refunded).
    advances_total: cost - settlement, i.e. everything credited as advances (payments,
    state contributions, carried over overpayments); for the current period the advance
    plan total when known.
    """
    mine = [d for d in docs if d.agreement_id == agreement_id]

    def paid_between(start: date | None, end: date | None) -> float | None:
        """Sum of payments in the period; None when no payment is known."""
        if start is None or end is None:
            return None
        amounts = [
            d.amount or 0
            for d in mine
            if d.is_payment and d.issue_date and start <= d.issue_date <= end
        ]
        return round(sum(amounts), 2) if amounts else None

    def credited(cost: float | None, settlement: float | None) -> float | None:
        if cost is None or settlement is None:
            return None
        return round(cost - settlement, 2)

    periods = []
    for h in sorted(history, key=lambda p: p.date_from or date.min):
        settlement = None
        if h.date_to:
            window_end = date.fromordinal(h.date_to.toordinal() + SETTLEMENT_WINDOW_DAYS)
            invoices = [
                d
                for d in mine
                if d.is_invoice and d.issue_date and h.date_to < d.issue_date <= window_end
            ]
            settlement = min(invoices, key=lambda d: d.issue_date) if invoices else None
        periods.append(
            BillingPeriod(
                date_from=h.date_from,
                date_to=h.date_to,
                consumption_kwh=h.consumption_kwh,
                cost=h.amount,
                paid=paid_between(h.date_from, h.date_to),
                settlement=settlement.amount if settlement else None,
                settlement_date=settlement.issue_date if settlement else None,
                advances_total=credited(h.amount, settlement.amount if settlement else None),
            )
        )
    if simulation and simulation.period_from:
        start, end = simulation.period_from, simulation.period_to or date.max
        plan = [
            i
            for i in (advance_plan.items if advance_plan else [])
            if i["due_date"] and start <= i["due_date"] <= end and i["amount"] is not None
        ]
        unpaid = [i for i in plan if not i["paid"]]
        installments = {i["unpaid"] or i["amount"] for i in unpaid}
        periods.append(
            BillingPeriod(
                date_from=simulation.period_from,
                date_to=simulation.period_to,
                consumption_kwh=simulation.consumption_kwh,
                cost=simulation.cost_with_tax,
                paid=paid_between(simulation.period_from, simulation.period_to),
                settlement=simulation.total_amount,
                settlement_date=None,
                predicted=True,
                advances_total=round(sum(i["amount"] for i in plan), 2)
                if plan
                else credited(simulation.cost_with_tax, simulation.total_amount),
                advances_remaining=round(sum(i["unpaid"] or i["amount"] for i in unpaid), 2)
                if plan
                else None,
                advances_remaining_count=len(unpaid) if plan else None,
                advances_installment=installments.pop() if len(installments) == 1 else None,
            )
        )
    return periods


COMMODITY_NAMES = {"E1": "elektřina", "P1": "plyn"}


def contract_names(
    supply_points: list[SupplyPoint], historical: list[dict[str, Any]] | None
) -> dict[str, str]:
    """Map agreement id -> human readable contract label.

    Active contracts use the supply point name; historical (terminated) ones use the
    address or supply point code with commodity. Unknown agreements are left out.
    """
    names: dict[str, str] = {}
    for row in historical if isinstance(historical, list) else []:
        if not isinstance(row, dict):
            continue
        agreement = (row.get("agreement") or {}).get("agreementIdIsu")
        if not agreement:
            continue
        addr = row.get("address") or {}
        street = (
            f"{_val(addr.get('addressStreet')) or ''} {addr.get('addressLandRegistryNumber') or ''}"
        )
        label = row.get("consumptionPlaceName") or street.strip() or row.get("supplyPointCode")
        commodity = _val(row.get("supplyPointCommodity")) or ""
        kind = COMMODITY_NAMES.get(commodity, commodity)
        names[agreement] = f"{label} ({kind}, ukončeno)" if kind else f"{label} (ukončeno)"
    for sp in supply_points:
        if sp.agreement_id:
            names[sp.agreement_id] = sp.name
    return names


def parse_outages(data: dict[str, Any], ean: str) -> list[Outage] | None:
    """Planned distribution outages for one supply point (cancelled ones excluded)."""
    if not isinstance(data, dict) or not isinstance(data.get("outages"), list):
        return None
    result = []
    for row in data["outages"]:
        if not isinstance(row, dict) or row.get("supplyPointCode") not in (None, "", ean):
            continue
        cancelled = bool(row.get("cancelled")) or bool(row.get("cancellationDate"))
        if cancelled:
            continue
        result.append(
            Outage(
                start_date=_date(row.get("manipulationStartDate")),
                start_time=row.get("manipulationStartTime"),
                end=row.get("manipulationEndTime"),
                reason=row.get("deviceReliefReasonText") or row.get("deviceReliefReason"),
                cancelled=cancelled,
            )
        )
    result.sort(key=lambda o: (o.start_date or date.max, o.start_time or ""))
    return result


def parse_unread_messages(data: dict[str, Any]) -> int | None:
    if not isinstance(data, dict):
        return None
    value = data.get("unreadTotal")
    return value if isinstance(value, int) else None


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


def _pkce_pair() -> tuple[str, str]:
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


class CezClient:
    """Async client. `session` is used for API calls; login uses its own cookie jar."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        username: str,
        password: str,
        partner: str | None = None,
    ) -> None:
        self._session = session
        # Customer account (business partner) when the ČEZ ID has several (shared access);
        # sent as X-COL-PARTNER like the web does, None = the portal's default account.
        self.partner = partner
        self._username = username
        self._password = password
        self._client_id: str | None = None
        self._authorize_url = DEFAULT_AUTHORIZE_URL
        self._token_url = DEFAULT_TOKEN_URL
        self._api_url = DEFAULT_API_URL
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._expires_at = 0.0
        self._lock = asyncio.Lock()

    # --- auth -------------------------------------------------------------

    async def _load_config(self) -> None:
        """Read client_id and endpoints from the SPA runtime config."""
        try:
            async with self._session.get(
                CONFIG_URL, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT
            ) as resp:
                resp.raise_for_status()
                text = await resp.text()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise CezConnectionError(f"Cannot load portal config: {err}") from err
        cfg = dict(re.findall(r'(\w+):\s*"([^"]*)"', text))
        self._client_id = cfg.get("REACT_APP_CONSUMER_KEY")
        if not self._client_id:
            raise CezConnectionError("client_id not found in portal config")
        self._authorize_url = cfg.get("REACT_APP_AUTHORIZATION_ENDPOINT", self._authorize_url)
        self._token_url = cfg.get("REACT_APP_TOKEN_ENDPOINT", self._token_url)
        self._api_url = cfg.get("REACT_APP_API_URL", self._api_url)

    async def _login(self) -> None:
        await self._load_config()
        verifier, challenge = _pkce_pair()
        scope = f"openid device_{uuid.uuid4()}"
        headers = {"User-Agent": USER_AGENT, "Accept-Language": "cs-CZ,cs;q=0.9"}
        jar = aiohttp.CookieJar()
        try:
            async with aiohttp.ClientSession(cookie_jar=jar, headers=headers, timeout=TIMEOUT) as s:
                async with s.get(
                    self._authorize_url,
                    params={
                        "client_id": self._client_id,
                        "redirect_uri": REDIRECT_URI,
                        "scope": scope,
                        "response_type": "code",
                        "code_challenge": challenge,
                        "code_challenge_method": "S256",
                    },
                ) as resp:
                    page = await resp.text()
                    login_url = str(resp.url)
                execution = re.search(r'name="execution"\s+value="([^"]+)"', page)
                if not execution:
                    raise CezConnectionError("Login form not found")
                action = re.search(r'id="fm1"[^>]*action="([^"]+)"', page)
                post_url = urljoin(login_url, action.group(1) if action else "login")
                if "?" not in post_url:
                    post_url += "?" + urlparse(login_url).query

                async with s.post(
                    post_url,
                    data={
                        "username": self._username,
                        "password": self._password,
                        "execution": execution.group(1),
                        "_eventId": "submit",
                        "geolocation": "",
                    },
                    allow_redirects=False,
                ) as resp:
                    status, location, url = resp.status, resp.headers.get("Location"), resp.url
                    body = await resp.text()

                code = None
                for _ in range(MAX_REDIRECTS):
                    if not location:
                        break
                    if location.startswith(REDIRECT_URI):
                        code = parse_qs(urlparse(location).query).get("code", [None])[0]
                        break
                    async with s.get(urljoin(str(url), location), allow_redirects=False) as resp:
                        status, location, url = resp.status, resp.headers.get("Location"), resp.url
                        body = await resp.text()

                if not code:
                    if 'id="fm1"' in body:
                        raise CezAuthError("Invalid username or password")
                    raise CezConnectionError(f"Login did not return auth code (HTTP {status})")

                async with s.post(
                    self._token_url,
                    data={
                        "grant_type": "authorization_code",
                        "code": code,
                        "client_id": self._client_id,
                        "redirect_uri": REDIRECT_URI,
                        "code_verifier": verifier,
                        "scope": scope,
                    },
                ) as resp:
                    if resp.status in (400, 401):
                        raise CezAuthError(f"Token exchange rejected (HTTP {resp.status})")
                    resp.raise_for_status()
                    self._store_token(await resp.json(content_type=None))
        except (aiohttp.ClientError, TimeoutError) as err:
            raise CezConnectionError(f"Login failed: {err}") from err
        _LOGGER.debug("Logged in to Muj CEZ")

    def _store_token(self, tok: dict[str, Any]) -> None:
        if "access_token" not in tok:
            raise CezAuthError("No access token in response")
        self._access_token = tok["access_token"]
        self._refresh_token = tok.get("refresh_token")
        self._expires_at = time.monotonic() + int(tok.get("expires_in", 900))

    async def _refresh(self) -> bool:
        if not self._refresh_token or not self._client_id:
            return False
        try:
            async with self._session.post(
                self._token_url,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self._refresh_token,
                    "client_id": self._client_id,
                    "redirect_uri": REDIRECT_URI,
                },
                headers={"User-Agent": USER_AGENT},
                timeout=TIMEOUT,
            ) as resp:
                if resp.status != 200:
                    _LOGGER.debug("Token refresh failed: HTTP %s", resp.status)
                    return False
                self._store_token(await resp.json(content_type=None))
                return True
        except (aiohttp.ClientError, TimeoutError, CezAuthError) as err:
            _LOGGER.debug("Token refresh failed: %s", err)
            return False

    async def _ensure_token(self, force: bool = False) -> None:
        async with self._lock:
            if (
                not force
                and self._access_token
                and time.monotonic() < self._expires_at - TOKEN_EXPIRY_MARGIN
            ):
                return
            if not await self._refresh():
                await self._login()

    async def authenticate(self) -> None:
        """Force a full login (used to validate credentials)."""
        async with self._lock:
            await self._login()

    # --- API --------------------------------------------------------------

    async def _get(self, path: str, params: dict[str, str] | None = None) -> Any:
        await self._ensure_token()
        for attempt in range(2):
            try:
                async with self._session.get(
                    f"{self._api_url}{path}",
                    params=params,
                    headers={
                        "User-Agent": USER_AGENT,
                        "Accept": "application/json",
                        "Authorization": f"Bearer {self._access_token}",
                        **({PARTNER_HEADER: self.partner} if self.partner else {}),
                    },
                    timeout=TIMEOUT,
                ) as resp:
                    if resp.status == 401 and attempt == 0:
                        await self._ensure_token(force=True)
                        continue
                    if resp.status != 200:
                        text = await resp.text()
                        raise CezConnectionError(f"GET {path}: HTTP {resp.status} {text[:200]}")
                    text = await resp.text()
                    if not text:
                        return None
                    return await resp.json(content_type=None)
            except (aiohttp.ClientError, TimeoutError) as err:
                raise CezConnectionError(f"GET {path} failed: {err}") from err
        raise CezAuthError("Unauthorized")

    async def _send(self, method: str, path: str, body: Any = None, raw: bool = False) -> Any:
        """POST/GET with JSON body; raw=True returns the response bytes. None on HTTP 404."""
        await self._ensure_token()
        for attempt in range(2):
            try:
                async with self._session.request(
                    method,
                    f"{self._api_url}{path}",
                    json=body,
                    headers={
                        "User-Agent": USER_AGENT,
                        "Accept": "*/*" if raw else "application/json",
                        "Authorization": f"Bearer {self._access_token}",
                        **({PARTNER_HEADER: self.partner} if self.partner else {}),
                    },
                    timeout=TIMEOUT,
                ) as resp:
                    if resp.status == 401 and attempt == 0:
                        await self._ensure_token(force=True)
                        continue
                    if resp.status == 404:
                        return None
                    if resp.status != 200:
                        text = await resp.text()
                        raise CezConnectionError(
                            f"{method} {path}: HTTP {resp.status} {text[:200]}"
                        )
                    data = await resp.read()
                    if raw:
                        return data
                    return json.loads(data) if data else None
            except (aiohttp.ClientError, TimeoutError, ValueError) as err:
                raise CezConnectionError(f"{method} {path} failed: {err}") from err
        raise CezAuthError("Unauthorized")

    async def get_invoice_rows(self, since: date) -> list[dict[str, Any]]:
        """Settlement documents (consumption INV, payout SLF) with current document ids."""
        data = await self._get("/billings/extended", {"dateFrom": since.isoformat()})
        return [
            row
            for row in data or []
            if isinstance(row, dict)
            and row.get("billingAccountingDocumentType2") in INVOICE_TYPES
            and row.get("billingReceivablesAndPayablesAccountDocumentNumber")
        ]

    async def get_invoice_csv(self, row: dict[str, Any]) -> str | None:
        """Data file of a settlement ("Datový soubor.csv"), None when it has none."""
        prepared = await self._send(
            "POST", "/documents/attachment?withRetry=false&force=false", invoice_filter(row)
        )
        key = prepared.get("attachmentKey") if isinstance(prepared, dict) else None
        if not key:
            return None
        data = await self._send("GET", f"/documents/{key}/attachment", raw=True)
        return data.decode("utf-8-sig") if data else None

    async def get_invoice_pdf(self, row: dict[str, Any]) -> bytes | None:
        """PDF of a settlement document, None when the archive has none."""
        docs = await self._send("POST", "/documents", invoice_filter(row))
        guid = next(
            (d.get("documentGuidCol") for d in docs or [] if d.get("documentGuidCol")), None
        )
        return await self.get_document_pdf(guid) if guid else None

    async def get_document_pdf(self, guid: str) -> bytes | None:
        """Download one archived document (PDF) by its documentGuidCol."""
        prepared = await self._send("POST", f"/documents/{guid}/attachment")
        key = prepared.get("attachmentKey") if isinstance(prepared, dict) else None
        if not key:
            return None
        data = await self._send("GET", f"/documents/{key}/attachment", raw=True)
        return data if data and data[:4] == b"%PDF" else None

    async def get_price_lists(self, sp: SupplyPoint) -> list[dict[str, Any]]:
        """Product price lists of a supply point ("Ceník ..." documents, type CEN).

        Items: {"doc_id", "guid", "name", "valid_from", "valid_to"}.
        """
        docs = await self._send(
            "POST",
            "/documents",
            {
                "documentDomain": "SUPPLY_POINT",
                "documentParams": [
                    {"key": "SUPPLY_POINT_ID", "value": sp.place_id},
                    {"key": "CONSUMPTION_PLACE_ID", "value": sp.ean},
                ],
            },
        )
        out = []
        for doc in docs or []:
            params = {p.get("key"): p.get("value") for p in doc.get("documentParams") or []}
            if params.get("DOC_TYPE") == "CEN" and doc.get("documentGuidCol"):
                out.append(
                    {
                        "doc_id": params.get("DOC_ID") or doc["documentGuidCol"],
                        "guid": doc["documentGuidCol"],
                        "name": params.get("DOCUMENT_DESCRIPTION"),
                        "valid_from": (params.get("VALID_FROM") or "")[:10] or None,
                        "valid_to": (params.get("VALID_TO") or "")[:10] or None,
                    }
                )
        return out

    @property
    def session(self) -> aiohttp.ClientSession:
        return self._session

    def with_partner(self, partner: str | None) -> CezClient:
        """Client for another customer account sharing this login (no new sign-in)."""
        other = CezClient(self._session, self._username, self._password, partner)
        for attr in (
            "_client_id",
            "_authorize_url",
            "_token_url",
            "_api_url",
            "_access_token",
            "_refresh_token",
            "_expires_at",
        ):
            setattr(other, attr, getattr(self, attr))
        return other

    async def get_raw(self, path: str, params: dict[str, str] | None = None) -> Any:
        """Raw response of a portal endpoint (diagnostics)."""
        return await self._get(path, params)

    async def get_accounts(self) -> tuple[list[str], str | None]:
        """Customer accounts of the ČEZ ID and the portal's default one."""
        return parse_accounts(await self._get("/user/token-data"))

    async def get_supply_points(self) -> list[SupplyPoint]:
        return parse_supply_points(await self._get("/supply-points/RetrieveSupplyPoints"))

    async def get_simulation(
        self, sp: SupplyPoint
    ) -> tuple[InvoiceSimulation | None, list[MonthValue], list[SimulationItem]]:
        data = await self._get(f"/simulations/invoices/{sp.ean}", {"supplyPointUid": sp.uid})
        return parse_simulation(data), parse_simulation_months(data), parse_simulation_items(data)

    async def get_advance_plan(self, sp: SupplyPoint, today: date) -> AdvancePlan | None:
        return parse_advance_plan(
            await self._get(f"/supply-points/{sp.uid}/ReadAdvancePlan"), today
        )

    async def get_consumption_periods(self, sp: SupplyPoint) -> list[ConsumptionPeriod]:
        """Closed billing periods (same aggregation as the portal uses)."""
        return parse_consumption_periods(
            await self._get(
                f"/supply-points/{sp.uid}/ReadConsumptionHistory", {"aggregation": "year"}
            )
        )

    async def get_meter_reading(
        self, sp: SupplyPoint, today: date
    ) -> tuple[MeterReading | None, list[MeterReadingPoint]]:
        data = await self._get(f"/supply-points/{sp.uid}/ReadMeterReading")
        return parse_meter_readings(data, today), parse_meter_reading_history(data, today)

    async def get_register_readings(
        self, sp: SupplyPoint, today: date
    ) -> tuple[dict[str, list[tuple[date, float]]], str | None]:
        """Real readings per register and the meter number (meter reading form)."""
        data = await self._get(f"/supply-points/{sp.uid}/ReadMeterReading")
        return parse_register_readings(data, today)

    async def get_self_readings(self, sp: SupplyPoint) -> Any:
        """Customer readings with reason and status (one reading per day check)."""
        return await self._get("/self-meter-reading", {"supplyPointCode": sp.ean})

    async def get_reading_consumption(self, sp: SupplyPoint) -> Any:
        """Last billing period consumption and yearly reading limits."""
        return await self._get("/meter-reading-consumption-vals", {"supplyPointCode": sp.ean})

    async def get_reading_types(self, sp: SupplyPoint) -> Any:
        """Reading types (reasons) the customer may choose now."""
        return await self._get("/meter-reading-requests-advanced", {"supplyPointCode": sp.ean})

    async def get_reading_form_config(self, sp: SupplyPoint, reason: str) -> Any:
        """Allowed date range of a reading type (meterReadingMinDate / MaxDate)."""
        return await self._get(
            "/self-meter-reading/form-config",
            {"meterReadingReasonId": reason, "supplyPointCode": sp.ean, "supplyPointUid": sp.uid},
        )

    async def submit_meter_reading(self, body: dict[str, Any]) -> Any:
        """Send a customer meter reading (body from reading.build_request).

        multipart/form-data with the JSON part `selfMeterReadingRequestBody` (photos of
        the display would be the optional parts contentHighTariff / contentLowTariff).
        Returns {activityId, meterReadingImplausible, isAttachmentNeeded}.
        """
        await self._ensure_token()
        path = "/self-meter-reading"
        for attempt in range(2):
            form = aiohttp.FormData()
            form.add_field(
                "selfMeterReadingRequestBody",
                json.dumps(body, ensure_ascii=False),
                content_type="application/json",
                filename="blob",
            )
            try:
                async with self._session.post(
                    f"{self._api_url}{path}",
                    data=form,
                    headers={
                        "User-Agent": USER_AGENT,
                        "Accept": "application/json",
                        "Authorization": f"Bearer {self._access_token}",
                        **({PARTNER_HEADER: self.partner} if self.partner else {}),
                    },
                    timeout=TIMEOUT,
                ) as resp:
                    if resp.status == 401 and attempt == 0:
                        await self._ensure_token(force=True)
                        continue
                    text = await resp.text()
                    _LOGGER.debug(
                        "POST %s (partner %s) body %s -> HTTP %s headers %s response %s",
                        path,
                        self.partner,
                        json.dumps(body, ensure_ascii=False),
                        resp.status,
                        {k: v for k, v in resp.headers.items() if k.lower() != "set-cookie"},
                        text,
                    )
                    if resp.status not in (200, 201):
                        raise CezConnectionError(f"POST {path}: HTTP {resp.status} {text}")
                    return json.loads(text) if text else None
            except (aiohttp.ClientError, TimeoutError, ValueError) as err:
                raise CezConnectionError(f"POST {path} failed: {err}") from err
        raise CezAuthError("Unauthorized")

    async def get_contract_info(
        self, sp: SupplyPoint, annual_consumption: float | None
    ) -> ContractInfo | None:
        detail = await self._get(
            f"/product-calculator/{sp.agreement_id}/supply-point/{sp.ean}",
            {"commodity": sp.commodity},
        )
        try:
            rate = await self._get(
                "/interactive-invoicing/distribution-rate-banner",
                {
                    "supplyPointUid": sp.uid,
                    "supplyPointExpectedAnnualConsumption": str(int(annual_consumption or 0)),
                },
            )
        except CezConnectionError as err:
            _LOGGER.debug("Distribution rate for %s failed: %s", sp.ean, err)
            rate = None
        return parse_contract_info(detail, rate)

    async def get_advance_settings(self, sp: SupplyPoint) -> AdvanceSettings | None:
        settings = await self._get(f"/advance-payments/{sp.uid}/settings")
        try:
            events = await self._get(f"/advance-payments/{sp.uid}/events")
        except CezConnectionError as err:
            _LOGGER.debug("Advance events for %s failed: %s", sp.ean, err)
            events = None
        return parse_advance_settings(settings, events)

    async def get_payouts(self, sp: SupplyPoint) -> list[Payout]:
        return parse_payouts(
            await self._get(
                f"/supply-points/{sp.uid}/ReadConsumptionHistory", {"aggregation": "year"}
            )
        )

    # --- Smart meter data (only for interval metered supply points) ----------

    async def get_grid_availability(self, sp: SupplyPoint, role: str, today: date) -> date | None:
        """First day with interval data for the role, None when the meter has none."""
        midnight = gridlib.local_midnight(today)
        data = await self._get(
            "/tapp/metering/profile-data/time-intervals",
            {
                "supplyPointUid": sp.uid,
                "profileReadingRoleId": role,
                "profileReadingDatetimeFrom": gridlib.iso_utc(midnight - timedelta(days=1100)),
                "profileReadingDatetimeTo": gridlib.iso_utc(midnight),
            },
        )
        return gridlib.parse_availability(data)

    async def get_grid_daily(
        self, sp: SupplyPoint, role: str, start: date, end: date
    ) -> gridlib.DailyValues:
        """Daily kWh for local days start .. end-1 (requests split into windows)."""
        result: gridlib.DailyValues = {}
        for a, b in gridlib.windows(start, end, gridlib.DAILY_WINDOW_DAYS):
            data = await self._get(
                "/tapp/metering/grid-data",
                {
                    "supplyPointUid": sp.uid,
                    "profileReadingRoleId": role,
                    "profileReadingIntervalId": "DEN",
                    "meterReadingUnitId": "KWH",
                    "profileReadingDatetimeFrom": gridlib.iso_utc(gridlib.local_midnight(a)),
                    "profileReadingDatetimeTo": gridlib.iso_utc(gridlib.local_midnight(b)),
                },
            )
            result.update({d: v for d, v in gridlib.parse_daily(data).items() if a <= d < b})
        return result

    async def get_profile_quarters(
        self, sp: SupplyPoint, role: str, start: date, end: date
    ) -> dict[datetime, float]:
        """15 min kWh (UTC interval start) for local days start .. end-1."""
        result: dict[datetime, float] = {}
        for a, b in gridlib.windows(start, end, gridlib.PROFILE_WINDOW_DAYS):
            data = await self._get(
                "/tapp/metering/profile-data",
                {
                    "supplyPointUid": sp.uid,
                    "profileReadingRoleId": role,
                    "profileReadingIntervalId": "HODINA",
                    "meterReadingUnitId": "KWH",
                    "profileReadingDatetimeFrom": gridlib.iso_utc(gridlib.local_midnight(a)),
                    "profileReadingDatetimeTo": gridlib.iso_utc(gridlib.local_midnight(b)),
                },
            )
            result.update(gridlib.parse_quarters(data))
        return result

    async def get_profile(
        self, sp: SupplyPoint, role: str, start: date, end: date
    ) -> dict[datetime, float]:
        """Hourly kWh (UTC hour start) for local days start .. end-1."""
        return gridlib.hourly_from_quarters(await self.get_profile_quarters(sp, role, start, end))

    async def get_spot_prices(self, start: date, end: date) -> dict[datetime, float]:
        """Hourly spot prices (CZK/kWh, UTC hour start) for local days start .. end-1.

        Missing days (HTTP 404 for some windows) are skipped.
        """
        result: dict[datetime, float] = {}
        for a, b in gridlib.windows(start, end, gridlib.SPOT_WINDOW_DAYS):
            params = {
                "pricelistConfigurationUnitId": "MWH",
                "pricelistSpotConfigurationIntervalId": "HODINA",
                "pricelistSpotConfigurationPriceCurrencyId": "CZK",
                "pricelistSpotConfigurationDatetimeFrom": gridlib.iso_utc(
                    gridlib.local_midnight(a)
                ),
                "pricelistSpotConfigurationDatetimeTo": gridlib.iso_utc(gridlib.local_midnight(b)),
            }
            data = await self._optional(
                f"spot prices {a}",
                self._get("/tapp/metering/price-lists/spot-prices-simple", params),
                quiet=True,
            )
            # The portal sometimes answers with other days than requested.
            lo, hi = gridlib.local_midnight(a), gridlib.local_midnight(b)
            result.update(
                {h: v for h, v in gridlib.parse_spot_prices(data).items() if lo <= h < hi}
            )
        return result

    async def update_grid_cache(
        self, sp: SupplyPoint, cache: dict[str, Any], today: date
    ) -> dict[str, Any]:
        """Refresh cached daily import/export of a consumption point.

        The availability (first day with data) is checked once a month; without
        interval data nothing else is requested. Daily values are fetched from the
        last cached day minus a few days (late corrections) up to yesterday.
        """
        checked = _date(cache.get("checked"))
        if checked is None or (today - checked).days >= GRID_RECHECK_DAYS:
            for key, role in (("import", gridlib.ROLE_IMPORT), ("export", gridlib.ROLE_EXPORT)):
                first = await self._optional(
                    f"{key} availability {sp.ean}",
                    self.get_grid_availability(sp, role, today),
                    quiet=True,
                )
                cache[f"{key}_from"] = first.isoformat() if first else None
            cache["checked"] = today.isoformat()
        for key, role in (("import", gridlib.ROLE_IMPORT), ("export", gridlib.ROLE_EXPORT)):
            first = _date(cache.get(f"{key}_from"))
            if first is None:
                continue
            values = cache.get(key) or {}
            start = first
            if values:
                start = max(
                    first, date.fromisoformat(max(values)) - timedelta(days=GRID_REFETCH_DAYS)
                )
            if start >= today:
                continue
            fresh = await self._optional(
                f"{key} daily {sp.ean}", self.get_grid_daily(sp, role, start, today)
            )
            if fresh:
                cache[key] = gridlib.merge_daily(values, fresh)
        return cache

    async def _optional(self, what: str, coro: Any, quiet: bool = False) -> Any:
        """Await an optional call; log and return None on non-auth errors.

        quiet: the endpoint is expected to fail for some accounts (log at debug level).
        """
        try:
            return await coro
        except CezAuthError:
            raise
        except CezError as err:
            (_LOGGER.debug if quiet else _LOGGER.warning)("%s failed: %s", what, err)
            return None

    async def fetch_all(
        self, today: date, grid_cache: dict[str, dict[str, Any]] | None = None
    ) -> CezData:
        """Fetch all data for all supply points of the account.

        A failure of a single optional endpoint is logged and leaves that part empty;
        failure to list supply points raises. With `grid_cache` (place id -> cache,
        updated in place) smart meter daily import/export is refreshed as well.
        """
        supply_points = await self.get_supply_points()
        historical = await self._optional(
            "historical supply points", self._get("/supply-points/historical")
        )
        names = contract_names(supply_points, historical)
        billings = await self._optional(
            "billings", self._get("/billings", {"includeNotPayed": "true"})
        )
        documents = parse_documents(billings, names)
        outages = await self._optional("outages", self._get("/dashboard/supply-point-outages"))
        messages = await self._optional("messages", self._get("/dashboard/messages/summary"))

        result: dict[str, SupplyPointData] = {}
        for sp in supply_points:
            spd = SupplyPointData(supply_point=sp)
            if sp.production:
                await self._fetch_production(spd, documents, outages, today)
                result[sp.uid] = spd
                continue
            if grid_cache is not None and sp.continuous_measurement and sp.place_id:
                place = grid_cache.setdefault(sp.place_id, {})
                if place.get("uid") in (None, sp.uid):
                    place["uid"] = sp.uid
                    await self.update_grid_cache(sp, place, today)
            await self.fetch_readings_and_billing(spd, documents, today)
            spd.contract = await self._optional(
                f"contract info {sp.ean}",
                self.get_contract_info(
                    sp, spd.last_period.consumption_kwh if spd.last_period else None
                ),
            )
            spd.billing = summarize_billing(documents, sp.agreement_id, today)
            spd.outages = parse_outages(outages, sp.ean)
            result[sp.uid] = spd
        return CezData(
            supply_points=result,
            unread_messages=parse_unread_messages(messages),
            documents=documents,
        )

    async def fetch_readings_and_billing(
        self, spd: SupplyPointData, documents: list[BillingDocument], today: date
    ) -> None:
        """Data of a consumption point a meter reading changes: readings, the portal's
        billing simulation, advances and billing periods (also refreshed after sending
        a reading)."""
        sp = spd.supply_point
        spd.simulation, spd.months, spd.sim_items = await self._optional(
            f"simulation {sp.ean}", self.get_simulation(sp)
        ) or (None, None, None)
        spd.advance_plan = await self._optional(
            f"advance plan {sp.ean}", self.get_advance_plan(sp, today)
        )
        history = await self._optional(
            f"consumption history {sp.ean}", self.get_consumption_periods(sp)
        )
        spd.last_period = history[-1] if history else None
        spd.meter_reading, spd.readings = await self._optional(
            f"meter readings {sp.ean}", self.get_meter_reading(sp, today)
        ) or (None, None)
        spd.advance_settings = await self._optional(
            f"advance settings {sp.ean}", self.get_advance_settings(sp)
        )
        spd.periods = build_billing_periods(
            history or [], documents, sp.agreement_id, spd.simulation, spd.advance_plan
        )

    async def _fetch_production(
        self,
        spd: SupplyPointData,
        documents: list[BillingDocument],
        outages: Any,
        today: date,
    ) -> None:
        """Production point: no advances, simulation or distribution rate exist."""
        sp = spd.supply_point
        spd.payouts = await self._optional(f"payouts {sp.ean}", self.get_payouts(sp))
        detail = await self._optional(
            f"contract info {sp.ean}",
            self._get(
                f"/product-calculator/{sp.agreement_id}/supply-point/{sp.code or sp.ean}",
                {"commodity": sp.commodity},
            ),
        )
        spd.contract = parse_contract_info(detail) if detail else None
        spd.billing = summarize_billing(documents, sp.agreement_id, today)
        spd.outages = parse_outages(outages, sp.ean)
