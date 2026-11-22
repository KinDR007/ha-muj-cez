"""Contract details restored from the recorder history when the portal fails."""

from __future__ import annotations

import dataclasses
from datetime import date
from unittest.mock import AsyncMock

import pytest
from homeassistant.components.recorder import Recorder
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.components.recorder.common import (
    async_wait_recording_done,
)

from custom_components.muj_cez import restore
from custom_components.muj_cez.api import ContractInfo
from custom_components.muj_cez.const import DOMAIN

from .conftest import PASSWORD, UID, USERNAME, sample_data


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(recorder_db_url: str, enable_custom_integrations: None) -> None:
    """Recorder database before hass (the recorder tests need it in this order)."""


def test_contract_from_states() -> None:
    rate = State(
        "sensor.x_rate",
        "D57d - Tep. čerpadlo",
        {"tariff_code": "D57D", "recommended": "D57d - Tep. čerpadlo", "double_tariff": True},
    )
    states = {
        "distribution_rate": rate,
        "circuit_breaker": State("sensor.x_breaker", "25.0", {"phase": 3}),
        "contract_end": State("sensor.x_end", "2027-06-27"),
        "price_change_date": State("sensor.x_change", "2027-01-01"),
        "product": State("sensor.x_product", "E_ELE_2_AKCI"),
    }
    assert restore.contract_from_states(states) == ContractInfo(
        tariff_code="D57D",
        circuit_breaker=25.0,
        phase=3,
        product="E_ELE_2_AKCI",
        contract_end=date(2027, 6, 27),
        price_change_date=date(2027, 1, 1),
        double_tariff=True,
        distribution_rate="D57d - Tep. čerpadlo",
        recommended_distribution_rate="D57d - Tep. čerpadlo",
    )
    # Only the tariff code was known: it is not a rate name.
    code_only = State("sensor.x_rate", "MOO", {"tariff_code": "MOO"})
    assert restore.contract_from_states({"distribution_rate": code_only}).distribution_rate is None
    assert restore.contract_from_states({}) is None


async def test_contract_restored_from_history(
    recorder_mock: Recorder, hass: HomeAssistant, mock_client: AsyncMock
) -> None:
    """Reload without cached data while the contract request fails: recorded states."""
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=USERNAME, data={CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD}
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    rate_id = er.async_get(hass).async_get_entity_id("sensor", DOMAIN, f"{UID}_distribution_rate")
    before = hass.states.get(rate_id)
    await async_wait_recording_done(hass)

    await entry.runtime_data.cache.async_remove()  # nothing kept from the last download
    failed = sample_data()
    failed.supply_points[UID] = dataclasses.replace(failed.supply_points[UID], contract=None)
    mock_client.fetch_all.return_value = failed
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    after = hass.states.get(rate_id)
    assert after.state == before.state != "unknown"
    assert after.attributes["tariff_code"] == before.attributes["tariff_code"]
    assert entry.runtime_data.data.supply_points[UID].contract is not None


async def test_cached_data_without_contract_restored(
    recorder_mock: Recorder, hass: HomeAssistant, mock_client: AsyncMock
) -> None:
    """HA start from cached data that lost the contract (outage before 1.6.2)."""
    from homeassistant.core import CoreState

    failed = sample_data()
    good_rate = failed.supply_points[UID].contract.distribution_rate
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=USERNAME, data={CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD}
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    await async_wait_recording_done(hass)
    coordinator = entry.runtime_data
    lost = sample_data()
    lost.supply_points[UID] = dataclasses.replace(lost.supply_points[UID], contract=None)
    await coordinator.cache.async_save_data(lost, coordinator.last_success_time)
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    hass.set_state(CoreState.not_running)  # HA start: cached data are used
    await hass.config_entries.async_setup(entry.entry_id)
    hass.set_state(CoreState.running)
    await hass.async_block_till_done()
    assert mock_client.fetch_all.call_count == 1  # not downloaded again
    assert entry.runtime_data.data.supply_points[UID].contract.distribution_rate == good_rate
