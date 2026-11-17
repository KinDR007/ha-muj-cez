"""Documents calendar tests."""

from datetime import datetime
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

from freezegun.api import FrozenDateTimeFactory
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.muj_cez.calendar import format_amount
from custom_components.muj_cez.const import DOMAIN

from .conftest import PASSWORD, USERNAME

TZ = ZoneInfo("Europe/Prague")


async def _setup(hass: HomeAssistant, freezer: FrozenDateTimeFactory, now: datetime) -> str:
    await hass.config.async_set_time_zone("Europe/Prague")
    freezer.move_to(now)
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=USERNAME, data={CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD}
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    entity_id = er.async_get(hass).async_get_entity_id(
        "calendar", DOMAIN, f"{entry.entry_id}_documents"
    )
    assert entity_id
    return entity_id


def test_unknown_contract_label() -> None:
    from custom_components.muj_cez.api import BillingDocument
    from custom_components.muj_cez.calendar import document_event

    doc = BillingDocument(
        doc_type="Platba",
        number="1",
        issue_date=None,
        due_date=None,
        amount=1.0,
        agreement_id="000099999999",
        contract_name="Smlouva 99999999",
    )
    assert "Smlouva: 99999999\n" in document_event(doc).description + "\n"


def test_format_amount() -> None:
    assert format_amount(1450) == "1 450,00"
    assert format_amount(-4385.23) == "−4 385,23"
    assert format_amount(None) == "?"


async def test_events_in_range(
    hass: HomeAssistant, mock_client: AsyncMock, freezer: FrozenDateTimeFactory
) -> None:
    entity_id = await _setup(hass, freezer, datetime(2026, 11, 10, 12, tzinfo=TZ))
    result = await hass.services.async_call(
        "calendar",
        "get_events",
        {
            "entity_id": entity_id,
            "start_date_time": datetime(2026, 3, 1, tzinfo=TZ),
            "end_date_time": datetime(2026, 3, 6, tzinfo=TZ),
        },
        blocking=True,
        return_response=True,
    )
    events = result[entity_id]["events"]
    summaries = [e["summary"] for e in events]
    assert "Faktura −4 385,23 Kč" in summaries
    invoice = next(e for e in events if e["summary"].startswith("Faktura"))
    assert invoice["start"] == "2026-03-05"
    assert "Vystaveno: 19.02.2026" in invoice["description"]
    assert "Smlouva: Testovací 123 (11111111)" in invoice["description"]
    # Range end is exclusive.
    result = await hass.services.async_call(
        "calendar",
        "get_events",
        {
            "entity_id": entity_id,
            "start_date_time": datetime(2026, 3, 6, tzinfo=TZ),
            "end_date_time": datetime(2026, 3, 15, tzinfo=TZ),
        },
        blocking=True,
        return_response=True,
    )
    assert all(e["start"] != "2026-03-05" for e in result[entity_id]["events"])
    # Event starting exactly at range end is excluded.
    result = await hass.services.async_call(
        "calendar",
        "get_events",
        {
            "entity_id": entity_id,
            "start_date_time": datetime(2026, 3, 4, tzinfo=TZ),
            "end_date_time": datetime(2026, 3, 5, tzinfo=TZ),
        },
        blocking=True,
        return_response=True,
    )
    assert all(e["start"] != "2026-03-05" for e in result[entity_id]["events"])


async def test_state_next_event(
    hass: HomeAssistant, mock_client: AsyncMock, freezer: FrozenDateTimeFactory
) -> None:
    entity_id = await _setup(hass, freezer, datetime(2026, 11, 16, 12, tzinfo=TZ))
    state = hass.states.get(entity_id)
    # Advance due today and still unpaid.
    assert state.state == STATE_ON
    assert state.attributes["message"].startswith("Záloha 1 450,00 Kč (neuhrazeno")
    assert state.attributes["start_time"].startswith("2026-11-16")


async def test_state_off_between_events(
    hass: HomeAssistant, mock_client: AsyncMock, freezer: FrozenDateTimeFactory
) -> None:
    entity_id = await _setup(hass, freezer, datetime(2026, 11, 20, 12, tzinfo=TZ))
    state = hass.states.get(entity_id)
    assert state.state == STATE_OFF
    assert state.attributes["start_time"].startswith("2026-12-15")
