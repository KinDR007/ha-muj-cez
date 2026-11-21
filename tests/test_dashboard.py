"""Dashboard generation from the shipped template (with and without PV)."""

from __future__ import annotations

import dataclasses
import json
import re
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.muj_cez as integration
from custom_components.muj_cez import dashboard
from custom_components.muj_cez.const import (
    CONF_DASHBOARD,
    CONF_INSTALL_CARDS,
    DASHBOARD_NEW,
    DOMAIN,
)

from .conftest import PASSWORD, USERNAME, FakeDip, load
from .test_grid import PV_UID, SV_UID
from .test_grid_ha import fake_fetch_all

TZ = ZoneInfo("Europe/Prague")
ENTITY = re.compile(r"\b(?:sensor|select|calendar)\.[a-z0-9_]+")


def _assert_entities_exist(hass: HomeAssistant, text: str) -> set[str]:
    """Every referenced entity exists (no unresolved marker, no guessed entity id)."""
    registry = er.async_get(hass)
    ids = set(ENTITY.findall(text)) - {f"sensor.{dashboard.MISSING}"}
    missing = {i for i in ids if registry.async_get(i) is None}
    assert not missing, missing
    return ids


@pytest.fixture(autouse=True)
def no_settle(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(integration, "DASHBOARD_SETTLE", 0)


async def _setup(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    target: str,
    install: bool = False,
    now: datetime = datetime(2026, 11, 16, 12, 0, tzinfo=TZ),
) -> MockConfigEntry:
    await hass.config.async_set_time_zone("Europe/Prague")
    freezer.move_to(now)
    assert await async_setup_component(hass, "lovelace", {})
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=USERNAME,
        data={CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD},
        options={CONF_DASHBOARD: target, CONF_INSTALL_CARDS: install},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    return entry


async def _config(hass: HomeAssistant, url: str | None) -> dict[str, Any]:
    return await hass.data[LOVELACE_DATA].dashboards[url].async_load(False)


async def test_new_dashboard_without_pv(
    hass: HomeAssistant, mock_client: AsyncMock, freezer: FrozenDateTimeFactory
) -> None:
    await _setup(hass, freezer, DASHBOARD_NEW)
    config = await _config(hass, "muj-cez")
    view, prices = config["views"]
    assert view["path"] == "cez"
    assert prices["path"] == "cez-ceny" and prices["icon"] == "mdi:cash-multiple"
    assert not prices.get("subview")  # own tab
    prices_text = json.dumps(prices, ensure_ascii=False)
    assert "muj_cez/prices" in prices_text and "mujcez_" not in prices_text
    _assert_entities_exist(hass, prices_text)
    text = json.dumps(view, ensure_ascii=False)
    assert "mujcez_" not in text  # every marker resolved
    assert len(_assert_entities_exist(hass, text)) > 25
    assert "muj_cez_head" in text and "vrm_head" not in text
    assert {"muj_cez_head", "muj_cez_details"} <= set(config["button_card_templates"])
    template = dashboard.load_template()
    expected = [
        s for s in template["sections"] if not s["requires"] or s["requires"] == ["no_grid"]
    ]
    assert len(view["sections"]) == len(expected)
    assert "Přetoky do sítě" not in text and "Výkup přetoků" not in text
    assert "muj_cez/profile" not in text
    # Custom cards are not installed in the test instance.
    issue = ir.async_get(hass).async_get_issue(DOMAIN, dashboard.ISSUE_CARDS)
    assert issue and "button-card" in issue.translation_placeholders["cards"]


async def test_pv_dashboard_into_existing(
    hass: HomeAssistant, mock_client: AsyncMock, freezer: FrozenDateTimeFactory
) -> None:
    mock_client.fetch_all.side_effect = fake_fetch_all
    await hass.config.async_set_time_zone("Europe/Prague")
    assert await async_setup_component(hass, "lovelace", {})
    collection = dashboard._dashboards_collection(hass)
    await collection.async_create_item({"url_path": "my-home", "title": "Home"})
    await hass.async_block_till_done()
    await (
        hass.data[LOVELACE_DATA]
        .dashboards["my-home"]
        .async_save(
            {
                "views": [{"path": "home", "title": "Home"}, {"path": "cez", "title": "old"}],
                "button_card_templates": {"mine": {"color": "red"}},
            }
        )
    )
    await _setup(hass, freezer, "my-home")
    config = await _config(hass, "my-home")
    assert [v["path"] for v in config["views"]] == ["home", "cez", "cez-ceny"]
    assert config["views"][0] == {"path": "home", "title": "Home"}
    assert "mine" in config["button_card_templates"]
    text = json.dumps(config["views"][1], ensure_ascii=False)
    assert "mujcez_" not in text
    _assert_entities_exist(hass, text)
    # PV sections with real entity ids of both supply points.
    assert (
        "Přetoky do sítě" in text
        and "Výkup přetoků" in text
        and "Spotová cena dnes a zítra" in text
    )
    payout = er.async_get(hass).async_get_entity_id("sensor", DOMAIN, f"{SV_UID}_last_payout")
    assert payout and payout in text
    assert "Odběr ze sítě po letech" in text  # smart meter year over year instead of HA based
    # 15 min section loads the data of the place through the smart meter date sensor.
    grid_date = er.async_get(hass).async_get_entity_id("sensor", DOMAIN, f"{PV_UID}_grid_data_date")
    assert "Průběh po 15 minutách" in text and f"const PE='{grid_date}'" in text


async def test_strategy_dashboard_refused(
    hass: HomeAssistant, mock_client: AsyncMock, freezer: FrozenDateTimeFactory
) -> None:
    assert await async_setup_component(hass, "lovelace", {})
    collection = dashboard._dashboards_collection(hass)
    await collection.async_create_item({"url_path": "auto-map", "title": "Map"})
    await hass.async_block_till_done()
    await hass.data[LOVELACE_DATA].dashboards["auto-map"].async_save({"strategy": {"type": "map"}})
    await _setup(hass, freezer, "auto-map")
    assert await _config(hass, "auto-map") == {"strategy": {"type": "map"}}
    assert ir.async_get(hass).async_get_issue(DOMAIN, dashboard.ISSUE_FAILED)
    # Not offered in the settings at all.
    choices = await dashboard.async_dashboard_choices(hass)
    assert "auto-map" not in {c["value"] for c in choices}


async def test_update_dashboard_service(
    hass: HomeAssistant, mock_client: AsyncMock, freezer: FrozenDateTimeFactory
) -> None:
    await _setup(hass, freezer, DASHBOARD_NEW)
    response = await hass.services.async_call(
        DOMAIN, "update_dashboard", {}, blocking=True, return_response=True
    )
    assert response == {"dashboards": ["muj-cez"]}


async def test_hdo_section(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    fake_dip: type[FakeDip],
    freezer: FrozenDateTimeFactory,
) -> None:
    fake_dip.signals_data = {"*": load("dip_signals.json")}
    freezer.move_to(datetime(2026, 11, 17, 9, 30, tzinfo=TZ))
    await _setup(hass, freezer, DASHBOARD_NEW, now=datetime(2026, 11, 17, 9, 30, tzinfo=TZ))
    view, _prices = (await _config(hass, "muj-cez"))["views"]
    text = json.dumps(view, ensure_ascii=False)
    assert "Tarif HDO a cena" in text
    ids = _assert_entities_exist(hass, text)
    registry = er.async_get(hass)
    uid = next(iter(mock_client.fetch_all.return_value.supply_points))
    for key in ("hdo_tariff", "hdo_next_switch", "current_price"):
        assert registry.async_get_entity_id("sensor", DOMAIN, f"{uid}_{key}") in ids


async def test_no_hdo_section_price_in_contract(
    hass: HomeAssistant, mock_client: AsyncMock, freezer: FrozenDateTimeFactory
) -> None:
    await _setup(hass, freezer, DASHBOARD_NEW)
    view, _prices = (await _config(hass, "muj-cez"))["views"]
    text = json.dumps(view, ensure_ascii=False)
    assert "Tarif HDO a cena" not in text
    uid = next(iter(mock_client.fetch_all.return_value.supply_points))
    price = er.async_get(hass).async_get_entity_id("sensor", DOMAIN, f"{uid}_current_price")
    assert price and price in text  # single tariff price row in the contract block


@pytest.mark.parametrize("dual", [True, False])
async def test_meter_reading_rows(
    hass: HomeAssistant, mock_client: AsyncMock, freezer: FrozenDateTimeFactory, dual: bool
) -> None:
    """Dual tariff: the NT row points at the NT sensor; single tariff has no NT entity."""
    data = mock_client.fetch_all.return_value
    spd = next(iter(data.supply_points.values()))
    assert spd.meter_reading
    spd.meter_reading.value_lt = 13160.0 if dual else None
    await _setup(hass, freezer, DASHBOARD_NEW)
    view, _prices = (await _config(hass, "muj-cez"))["views"]
    text = json.dumps(view, ensure_ascii=False)
    _assert_entities_exist(hass, text)
    registry = er.async_get(hass)
    vt = registry.async_get_entity_id("sensor", DOMAIN, f"{spd.supply_point.uid}_meter_reading")
    nt = registry.async_get_entity_id("sensor", DOMAIN, f"{spd.supply_point.uid}_meter_reading_low")
    assert vt and vt in text
    assert "Stav elektroměru NT" in text
    if dual:
        assert nt and nt in text
    else:
        assert nt is None and f"sensor.{dashboard.MISSING}" in text


def test_is_ours() -> None:
    assert all(dashboard._is_ours(p) for p in ("cez", "cez-2", "cez-ceny", "cez-ceny-3"))
    assert not any(dashboard._is_ours(p) for p in ("home", "cez-x", "cezceny", None, "cez-ceny-"))


async def test_second_point_own_price_tab(
    hass: HomeAssistant, mock_client: AsyncMock, freezer: FrozenDateTimeFactory
) -> None:
    await _setup(hass, freezer, DASHBOARD_NEW)
    coordinator = hass.config_entries.async_entries(DOMAIN)[0].runtime_data
    spd = next(iter(coordinator.data.supply_points.values()))
    data = dataclasses.replace(coordinator.data, supply_points={"a": spd, "b": spd})
    views = dashboard.build_views(hass, coordinator.config_entry.entry_id, data)
    assert [v["path"] for v in views] == ["cez", "cez-ceny", "cez-2", "cez-ceny-2"]
    assert "muj_cez/prices" in json.dumps(views[3], ensure_ascii=False)
