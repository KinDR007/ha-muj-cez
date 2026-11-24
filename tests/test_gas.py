"""Gas supply point next to the electricity one (shapes from a real diagnostics dump)."""

from __future__ import annotations

import dataclasses
import json
from datetime import date, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.muj_cez as integration
from custom_components.muj_cez import api, dashboard
from custom_components.muj_cez.const import (
    CONF_DASHBOARD,
    CONF_REFERENCE_SENSOR,
    DASHBOARD_NEW,
    DOMAIN,
)

from .conftest import PASSWORD, UID, USERNAME, FakeDip, load, sample_data
from .test_dashboard import _assert_entities_exist, _tabs

TZ = ZoneInfo("Europe/Prague")
GAS_UID = "0000111111110002222222859100000000000009"
GAS_EAN = "27ZG100000000009"


def _reading(day: date, value: float, device: str = "G1") -> api.MeterReadingPoint:
    return api.MeterReadingPoint(day, value, "Odečet distributorem", device)


def gas_data() -> api.CezData:
    """Electricity point of the sample data plus a gas point (meter in m³, no HDO)."""
    data = sample_data()
    spd = data.supply_points[UID]
    gas = dataclasses.replace(
        spd,
        supply_point=dataclasses.replace(
            spd.supply_point,
            uid=GAS_UID,
            ean=GAS_EAN,
            commodity="P1",
            product="PLYN_NA_NEURCITO_P",
            continuous_measurement=True,
        ),
        meter_reading=api.MeterReading(
            date(2026, 3, 23), 152.0, None, "Odečet distributorem", "G2"
        ),
        readings=[
            _reading(date(2019, 3, 25), 316.0),
            _reading(date(2019, 8, 1), 328.0),
            _reading(date(2020, 3, 27), 23.0, "G2"),  # meter exchanged
            _reading(date(2025, 3, 24), 127.0, "G2"),
            _reading(date(2026, 3, 23), 152.0, "G2"),
        ],
        contract=api.ContractInfo(
            tariff_code="MOO",
            circuit_breaker=0.0,
            phase=0,
            product="P_PLYN_NA_NEURCITO",
            contract_end=None,
            price_change_date=date(2026, 11, 22),
            double_tariff=False,
        ),
        simulation=dataclasses.replace(spd.simulation, unit_prices={}, gas_kwh_per_m3=10.6935),
        sim_items=[],
    )
    return dataclasses.replace(data, supply_points={UID: spd, GAS_UID: gas})


@pytest.fixture(autouse=True)
def no_settle(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(integration, "DASHBOARD_SETTLE", 0)


async def _setup(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    mock_client: AsyncMock,
    options: dict[str, Any] | None = None,
    before: Any = None,
) -> MockConfigEntry:
    await hass.config.async_set_time_zone("Europe/Prague")
    freezer.move_to(datetime(2026, 11, 16, 12, 0, tzinfo=TZ))
    assert await async_setup_component(hass, "lovelace", {})
    mock_client.fetch_all.return_value = gas_data()
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=USERNAME,
        data={CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD},
        options={CONF_DASHBOARD: DASHBOARD_NEW, **(options or {})},
    )
    entry.add_to_hass(hass)
    if before:
        before(entry)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    return entry


def _entity(hass: HomeAssistant, uid: str, key: str, domain: str = "sensor") -> str | None:
    return er.async_get(hass).async_get_entity_id(domain, DOMAIN, f"{uid}_{key}")


async def test_gas_sensors(
    hass: HomeAssistant, mock_client: AsyncMock, freezer: FrozenDateTimeFactory
) -> None:
    await _setup(hass, freezer, mock_client)
    state = hass.states.get(_entity(hass, GAS_UID, "gas_meter_reading"))
    assert state.state == "152.0"
    assert state.attributes["unit_of_measurement"] == "m³"
    assert state.attributes["device_class"] == "gas"
    assert state.attributes["state_class"] == "total_increasing"
    assert state.attributes["reading_date"] == date(2026, 3, 23)
    assert [r["consumption"] for r in state.attributes["readings"]] == [
        None,
        12.0,
        None,
        104.0,
        25.0,
    ]
    assert state.attributes["kwh_per_m3"] == 10.6935
    assert hass.states.get(_entity(hass, GAS_UID, "gas_meter_number")).state == "G2"
    # Consumption and costs stay in kWh.
    consumption = hass.states.get(_entity(hass, GAS_UID, "last_period_consumption"))
    assert consumption.attributes["unit_of_measurement"] == "kWh"
    for key in ("meter_reading", "meter_number", "circuit_breaker", "current_price"):
        assert _entity(hass, GAS_UID, key) is None, key
        assert _entity(hass, UID, key) is not None, key
    for key in ("gas_meter_reading", "gas_meter_number"):
        assert _entity(hass, UID, key) is None, key
    # Invoices of both points are parsed (gas by invoice_gas).
    assert _entity(hass, GAS_UID, "refresh_invoices", "button") is not None
    assert _entity(hass, UID, "refresh_invoices", "button") is not None


async def test_old_gas_entities_removed(
    hass: HomeAssistant, mock_client: AsyncMock, freezer: FrozenDateTimeFactory
) -> None:
    """kWh meter reading and circuit breaker of a gas point created before 1.6 are removed."""

    def register(entry: MockConfigEntry) -> None:
        registry = er.async_get(hass)
        for key in ("meter_reading", "circuit_breaker", "meter_number"):
            registry.async_get_or_create("sensor", DOMAIN, f"{GAS_UID}_{key}", config_entry=entry)

    await _setup(hass, freezer, mock_client, before=register)
    for key in ("meter_reading", "circuit_breaker", "meter_number"):
        assert _entity(hass, GAS_UID, key) is None, key
    assert _entity(hass, UID, "meter_reading") is not None


async def test_gas_without_hdo_and_reference(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    fake_dip: type[FakeDip],
    freezer: FrozenDateTimeFactory,
) -> None:
    fake_dip.signals_data = {"*": load("dip_signals.json")}
    asked: list[str] = []
    signals = FakeDip.signals

    async def record(self: FakeDip, ean: str) -> Any:
        asked.append(ean)
        return await signals(self, ean)

    daily = {date(2026, 2, 18) + timedelta(days=i): 4.0 for i in range(272)}
    with (
        patch.object(FakeDip, "signals", record),
        patch("custom_components.muj_cez.coordinator.async_get_daily_energy", return_value=daily),
    ):
        await _setup(hass, freezer, mock_client, {CONF_REFERENCE_SENSOR: "sensor.grid_import"})
    assert GAS_EAN not in asked and asked
    assert _entity(hass, GAS_UID, "hdo_tariff") is None
    assert _entity(hass, UID, "hdo_tariff") is not None
    gas = hass.states.get(_entity(hass, GAS_UID, "consumption_comparison"))
    assert gas.attributes["reference_sensor"] is None
    assert all(m["ha_kwh"] is None for m in gas.attributes["months"])
    power = hass.states.get(_entity(hass, UID, "consumption_comparison"))
    assert power.attributes["reference_sensor"] == "sensor.grid_import"


async def test_gas_dashboard_tab(
    hass: HomeAssistant, mock_client: AsyncMock, freezer: FrozenDateTimeFactory
) -> None:
    await _setup(hass, freezer, mock_client)
    config = await hass.data[LOVELACE_DATA].dashboards["muj-cez"].async_load(False)
    views = {v["path"]: v for v in config["views"]}
    data = mock_client.fetch_all.return_value
    path = dashboard.point_path(data.supply_points[GAS_UID].supply_point)
    gas = views[path]
    assert gas["title"].startswith("🔥 ") and gas["title"].endswith(" · 0000009")
    tabs = _tabs(gas)
    assert list(tabs) == ["Přehled", "Ceny", "Odečet"]
    assert tabs["Odečet"]["cards"][0]["ean"] == GAS_EAN
    text = json.dumps(tabs["Přehled"], ensure_ascii=False)
    ids = _assert_entities_exist(hass, text)
    assert _entity(hass, GAS_UID, "gas_meter_reading") in ids
    assert "Odečty plynoměru" in text
    for heading in ("Kontrola měření", "Tarif HDO a cena"):
        assert heading not in text, heading
    # The electricity tab is unchanged: contract with the meter and the reading check.
    power = [v for p, v in views.items() if p != path]
    assert len(power) == 1 and power[0]["title"].startswith("⚡ ")
    power_text = json.dumps(_tabs(power[0])["Přehled"], ensure_ascii=False)
    assert "Kontrola měření" in power_text and "Odečty plynoměru" not in power_text
    assert "Odečet" in _tabs(power[0])


async def test_gas_reading_form_and_submit(
    hass: HomeAssistant, hass_ws_client: Any, mock_client: AsyncMock
) -> None:
    """Gas meter reading: m³, no tariffs, usual consumption from a year of readings."""
    today = dt_util.now().date()
    last = today - timedelta(days=40)
    gas_registers = {
        "vt": [
            (last - timedelta(days=364), 2703.0),
            (last - timedelta(days=22), 2852.0),  # summer: 0.36 m³/day only
            (last, 2860.0),
        ]
    }

    async def registers(sp: api.SupplyPoint, _today: date) -> Any:
        if sp.gas:
            return gas_registers, "90000001"
        return {"vt": [(today - timedelta(days=60), 11598.0)]}, "1000000001"

    mock_client.fetch_all.return_value = gas_data()
    mock_client.get_register_readings.side_effect = registers
    # The portal gives no usual consumption for gas.
    mock_client.get_reading_consumption.return_value = {
        "lastConsVT": 0.0, "lastConsNT": 0.0, "LastBillPeriod": 363, "Limits": []
    }  # fmt: skip
    mock_client.submit_meter_reading.return_value = {"activityId": "A2"}
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=USERNAME, data={CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD}
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    ws = await hass_ws_client(hass)
    await ws.send_json({"id": 1, "type": f"{DOMAIN}/reading_form", "entry_id": entry.entry_id})
    points = {p["ean"]: p for p in (await ws.receive_json())["result"]["points"]}
    gas = points[GAS_EAN]
    assert gas["gas"] is True and gas["unit"] == "m³" and not gas["dual_tariff"]
    assert gas["previous"] == {"date": last.isoformat(), "vt": 2860.0}
    assert points[next(e for e in points if e != GAS_EAN)]["unit"] == "kWh"

    base = {
        "entry_id": entry.entry_id,
        "ean": GAS_EAN,
        "reading_type": "diary",
        "date": today.isoformat(),
    }
    # 40 days x (157 m³ / 364 days) x 1.5 = 25.9 m³: 2880 is fine, 2890 unusually high.
    await ws.send_json({"id": 2, "type": f"{DOMAIN}/reading_check", **base, "vt": "2880"})
    check = (await ws.receive_json())["result"]
    assert check["ok"] and not check["warnings"]
    await ws.send_json({"id": 3, "type": f"{DOMAIN}/reading_check", **base, "vt": "2890"})
    assert (await ws.receive_json())["result"]["warnings"][0]["code"] == "high"

    await ws.send_json({"id": 4, "type": f"{DOMAIN}/reading_submit", **base, "vt": "2880"})
    assert (await ws.receive_json())["result"]["sent"] is True
    body = mock_client.submit_meter_reading.await_args.args[0]
    assert body["meterReadingDeviceNumber"] == "90000001"
    assert body["selfMeterReadingHighTariff"]["meterReadingValue"] == 2880


def test_gas_conversion_from_simulation() -> None:
    """kWh per m³ = volume coefficient x calorific value of the latest simulated reading."""
    rows = [
        {"meterReadingGasCombustionHeat": 10.5, "meterReadingGasVolumeCoefficient": 0.97},
        {"meterReadingGasCombustionHeat": 10.9767, "meterReadingGasVolumeCoefficient": 0.9742},
    ]
    assert api.gas_conversion(rows) == round(10.9767 * 0.9742, 4)
    assert api.gas_conversion([{"consumptionValue": 225}]) is None  # electricity
