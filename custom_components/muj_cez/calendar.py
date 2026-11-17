"""Calendar of all accounting documents (invoices, advances, payments, ...)."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .api import BillingDocument, strip_zeros
from .coordinator import MujCezConfigEntry, MujCezCoordinator
from .entity import account_device_info

PARALLEL_UPDATES = 0


def format_amount(value: float | None) -> str:
    """Czech number format: 1 450,00."""
    if value is None:
        return "?"
    text = f"{abs(value):,.2f}".replace(",", " ").replace(".", ",")
    return f"−{text}" if value < 0 else text


def _fmt_date(value: date | None) -> str | None:
    return value.strftime("%d.%m.%Y") if value else None


def document_event(doc: BillingDocument) -> CalendarEvent:
    summary = f"{doc.doc_type} {format_amount(doc.amount)} Kč"
    if doc.balance > 0:
        summary += f" (neuhrazeno {format_amount(doc.balance)} Kč)"
    number = strip_zeros(doc.agreement_id)
    contract = doc.contract_name or ""
    if number and number not in contract:
        contract = f"{contract} ({number})".strip()
    elif number and contract == f"Smlouva {number}":
        contract = number
    lines = [
        ("Smlouva", contract or None),
        ("Typ dokladu", doc.doc_type),
        ("Číslo dokladu", doc.number),
        ("Částka", f"{format_amount(doc.amount)} Kč"),
        ("Vystaveno", _fmt_date(doc.issue_date)),
        ("Splatnost", _fmt_date(doc.due_date)),
        ("Zúčtováno", _fmt_date(doc.settlement_date)),
        ("Zbývá uhradit", f"{format_amount(doc.balance)} Kč" if doc.balance > 0 else None),
        ("Variabilní symbol", doc.variable_symbol),
    ]
    start = doc.event_date or date.min
    return CalendarEvent(
        start=start,
        end=start + timedelta(days=1),
        summary=summary,
        description="\n".join(f"{k}: {v}" for k, v in lines if v),
        uid=f"{doc.agreement_id}_{doc.number}_{doc.doc_type}_{start.isoformat()}",
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MujCezConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([MujCezDocumentsCalendar(entry.runtime_data)])


class MujCezDocumentsCalendar(CoordinatorEntity[MujCezCoordinator], CalendarEntity):
    """All documents of all contracts, one all-day event per document."""

    _attr_has_entity_name = True
    _attr_translation_key = "documents"

    def __init__(self, coordinator: MujCezCoordinator) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_documents"
        self._attr_device_info = account_device_info(entry)

    @property
    def _documents(self) -> list[BillingDocument]:
        data = self.coordinator.data
        return [d for d in (data.documents if data else []) if d.event_date]

    @property
    def available(self) -> bool:
        return self.coordinator.data is not None

    @property
    def event(self) -> CalendarEvent | None:
        """Current or next upcoming document."""
        today = dt_util.now().date()
        upcoming = [d for d in self._documents if d.event_date >= today]
        return document_event(upcoming[0]) if upcoming else None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        def day_start(day: date) -> datetime:
            return dt_util.start_of_local_day(day)

        # All-day event [day, day+1) overlaps the requested [start_date, end_date).
        return [
            document_event(d)
            for d in self._documents
            if day_start(d.event_date) < end_date
            and day_start(d.event_date + timedelta(days=1)) > start_date
        ]
