"""get_documents action tests."""

from datetime import date
from unittest.mock import AsyncMock

import pytest
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.muj_cez.const import DOMAIN

from .conftest import PASSWORD, USERNAME


@pytest.fixture
async def entry(hass: HomeAssistant, mock_client: AsyncMock) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=USERNAME, data={CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD}
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def _call(hass: HomeAssistant, **data) -> dict:
    return await hass.services.async_call(
        DOMAIN, "get_documents", data, blocking=True, return_response=True
    )


async def test_all_documents_newest_first(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    result = await _call(hass, limit=1000)
    assert result["count"] == result["returned"] == 45
    dates = [d["due_date"] or d["issue_date"] for d in result["documents"]]
    assert dates == sorted(dates, reverse=True)


async def test_filters(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    result = await _call(hass, document_type="faktura")
    assert {d["type"] for d in result["documents"]} == {"Faktura"}
    assert result["count"] == 3

    result = await _call(hass, contract="plyn")
    assert result["count"] == 5
    assert {d["contract"] for d in result["documents"]} == {"44444444"}

    result = await _call(hass, contract="00011111111", document_type="Faktura")
    assert result["count"] == 2

    result = await _call(hass, date_from=date(2026, 1, 1), date_to=date(2026, 3, 31))
    assert result["count"] > 0
    for d in result["documents"]:
        assert "2026-01-01" <= (d["due_date"] or d["issue_date"]) <= "2026-03-31"

    result = await _call(hass, unpaid_only=True)
    assert result["count"] == 3
    assert all(d["balance"] > 0 for d in result["documents"])

    result = await _call(hass, limit=2)
    assert result["returned"] == 2
    assert result["count"] == 45


async def test_entry_selection(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    result = await _call(hass, config_entry_id=entry.entry_id, limit=1)
    assert result["returned"] == 1
    with pytest.raises(ServiceValidationError):
        await _call(hass, config_entry_id="missing")


async def test_no_loaded_entry(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    await hass.config_entries.async_unload(entry.entry_id)
    with pytest.raises(ServiceValidationError):
        await _call(hass)
