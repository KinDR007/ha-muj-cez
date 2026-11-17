"""Entities of PV accounts: production point, smart meter sensors, export comparison."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.muj_cez import api
from custom_components.muj_cez.const import CONF_REFERENCE_EXPORT_SENSOR, DOMAIN

from .conftest import PASSWORD, USERNAME, load
from .test_grid import PV_UID, SV_UID

TZ = ZoneInfo("Europe/Prague")


def pv_data() -> api.CezData:
    cons, prod = api.parse_supply_points(load("pv_supply_points.json"))
    return api.CezData(
        supply_points={
            cons.uid: api.SupplyPointData(supply_point=cons),
            prod.uid: api.SupplyPointData(
                supply_point=prod, payouts=api.parse_payouts(load("pv_payouts.json"))
            ),
        }
    )


async def fake_fetch_all(today: date, grid_cache: dict[str, Any] | None = None) -> api.CezData:
    if grid_cache is not None:
        grid_cache["0004444444"] = {
            "uid": PV_UID,
            "import_from": "2025-01-01",
            "export_from": "2025-01-01",
            "import": {"2026-10-01": 10.0, "2026-11-01": 5.0, "2026-11-15": 7.0},
            "export": {"2026-10-01": 22.13, "2026-11-01": 1.0},
        }
    return pv_data()


@pytest.fixture
async def entry(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> MockConfigEntry:
    await hass.config.async_set_time_zone("Europe/Prague")
    freezer.move_to(datetime(2026, 11, 16, 12, 0, tzinfo=TZ))
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=USERNAME,
        data={CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD},
        options={CONF_REFERENCE_EXPORT_SENSOR: "sensor.export_energy"},
    )
    entry.add_to_hass(hass)
    return entry


def _entity(hass: HomeAssistant, uid: str, key: str) -> str | None:
    return er.async_get(hass).async_get_entity_id("sensor", DOMAIN, f"{uid}_{key}")


def _state(hass: HomeAssistant, uid: str, key: str) -> Any:
    entity_id = _entity(hass, uid, key)
    assert entity_id, key
    return hass.states.get(entity_id)


async def test_pv_entities(
    hass: HomeAssistant, entry: MockConfigEntry, mock_client: AsyncMock
) -> None:
    mock_client.fetch_all.side_effect = fake_fetch_all
    # Left over by an older version: consumption sensor on the production point.
    stale = er.async_get(hass).async_get_or_create(
        "sensor", DOMAIN, f"{SV_UID}_invoice_balance", config_entry=entry
    )
    ha_daily = {date(2026, 10, 1): 23.0, date(2026, 11, 1): 1.0}
    with patch(
        "custom_components.muj_cez.coordinator.async_get_daily_energy",
        AsyncMock(return_value=ha_daily),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    # Consumption point: smart meter sensors.
    assert _state(hass, PV_UID, "grid_import_month").state == "12.0"
    assert _state(hass, PV_UID, "grid_import_year").state == "22.0"
    assert _state(hass, PV_UID, "grid_export_month").state == "1.0"
    year = _state(hass, PV_UID, "grid_export_year")
    assert year.state == "23.13"
    assert year.attributes["last_day"] == "2026-11-01"
    info = _state(hass, PV_UID, "grid_data_date")
    assert info.state == "2026-11-15"
    assert info.attributes["months"][-1]["month"] == "2026-11"
    assert info.attributes["export_comparison"][0]["diff_pct"] == 3.9
    assert info.attributes["export_reference_sensor"] == "sensor.export_energy"
    assert "import_comparison" not in info.attributes
    assert _entity(hass, PV_UID, "consumption_comparison")

    # Production point: payouts, no consumption-only entities.
    assert _state(hass, SV_UID, "last_payout").state == "73.13"
    payout = _state(hass, SV_UID, "last_payout")
    assert payout.attributes["export_kwh"] == 22.13
    assert payout.attributes["price_per_kwh"] == 3.3
    assert _state(hass, SV_UID, "payout_price").state == "3.3"
    assert _state(hass, SV_UID, "payout_year").state == str(
        round(sum(p.amount for p in api.parse_payouts(load("pv_payouts.json"))), 2)
    )
    assert _entity(hass, SV_UID, "ean")
    for key in ("invoice_balance", "current_advance", "meter_reading", "consumption_comparison"):
        assert _entity(hass, SV_UID, key) is None, key
    assert _entity(hass, SV_UID, "grid_import_month") is None
    assert er.async_get(hass).async_get(stale.entity_id) is None


async def test_no_smart_meter_entities_without_data(
    hass: HomeAssistant, entry: MockConfigEntry, mock_client: AsyncMock
) -> None:
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    uid = next(iter(mock_client.fetch_all.return_value.supply_points))
    assert _entity(hass, uid, "invoice_balance")
    for key in ("grid_import_month", "grid_export_year", "grid_data_date", "last_payout"):
        assert _entity(hass, uid, key) is None, key
