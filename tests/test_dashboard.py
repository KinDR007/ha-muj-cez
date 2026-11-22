"""Dashboard generation from the shipped template (with and without PV)."""

from __future__ import annotations

import asyncio
import dataclasses
import json
import re
from datetime import datetime
from types import MappingProxyType
from typing import Any
from unittest.mock import AsyncMock, patch
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


def _tabs(view: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Inner tabs of a supply point view by title."""
    assert view["type"] == "panel"
    (card,) = view["cards"]
    assert card["type"] == dashboard.TABS_CARD and card["id"] == view["path"]
    return {tab["title"]: tab for tab in card["tabs"]}


def _overview(view: dict[str, Any]) -> str:
    return json.dumps(_tabs(view)["Přehled"], ensure_ascii=False)


async def test_new_dashboard_without_pv(
    hass: HomeAssistant, mock_client: AsyncMock, freezer: FrozenDateTimeFactory
) -> None:
    await _setup(hass, freezer, DASHBOARD_NEW)
    config = await _config(hass, "muj-cez")
    (view,) = config["views"]
    sp = next(iter(mock_client.fetch_all.return_value.supply_points.values())).supply_point
    assert view["path"] == f"cez-{sp.ean}"
    assert view["title"] == f"⚡ {sp.name} · {sp.ean[-7:]}"
    assert "icon" not in view  # HA shows the icon instead of the title
    entry_id = hass.config_entries.async_entries("muj_cez")[0].entry_id
    assert dashboard.view_owner(view) == entry_id
    tabs = _tabs(view)
    assert list(tabs) == ["Přehled", "Ceny", "Odečet"]
    reading = tabs["Odečet"]
    assert reading["icon"] == "mdi:counter" and reading["max_width"]
    assert reading["cards"] == [
        {"type": "custom:muj-cez-reading-card", "entry_id": entry_id, "ean": sp.ean}
    ]
    prices = tabs["Ceny"]
    assert prices["icon"] == "mdi:cash-multiple"
    # Refresh icon in the heading presses the invoice button after a confirmation.
    button = er.async_get(hass).async_get_entity_id("button", DOMAIN, f"{sp.uid}_refresh_invoices")
    (badge,) = prices["sections"][0]["cards"][0]["badges"]
    assert badge["entity"] == button and badge["icon"] == "mdi:refresh"
    assert badge["tap_action"]["perform_action"] == "button.press"
    assert badge["tap_action"]["confirmation"]["text"]
    prices_text = json.dumps(prices, ensure_ascii=False)
    assert "muj_cez/prices" in prices_text and "mujcez_" not in prices_text
    _assert_entities_exist(hass, prices_text)
    text = _overview(view)
    assert tabs["Přehled"]["max_columns"] == 3
    assert "mujcez_" not in text  # every marker resolved
    assert len(_assert_entities_exist(hass, text)) > 25
    assert "muj_cez_head" in text and "vrm_head" not in text
    assert {"muj_cez_head", "muj_cez_details"} <= set(config["button_card_templates"])
    template = dashboard.load_template()
    present = {"no_grid", "no_hdo", "electricity"}
    expected = [s for s in template["sections"] if set(s["requires"]) <= present]
    assert len(tabs["Přehled"]["sections"]) == len(expected)
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
    old = [{"path": p, "title": "old"} for p in ("cez", "cez-ceny", "cez-2", "cez-odecet")]
    await (
        hass.data[LOVELACE_DATA]
        .dashboards["my-home"]
        .async_save(
            {
                "views": [{"path": "home", "title": "Home"}, *old, {"path": "end"}],
                "button_card_templates": {"mine": {"color": "red"}},
            }
        )
    )
    await _setup(hass, freezer, "my-home")
    config = await _config(hass, "my-home")
    # Tabs of older versions are replaced in place, other views are kept.
    paths = [v["path"] for v in config["views"]]
    assert paths[0] == "home" and paths[-1] == "end" and len(paths) == 3
    assert paths[1].startswith("cez-") and not dashboard._is_legacy(paths[1])
    assert config["views"][0] == {"path": "home", "title": "Home"}
    assert "mine" in config["button_card_templates"]
    text = _overview(config["views"][1])
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
    (view,) = (await _config(hass, "muj-cez"))["views"]
    text = _overview(view)
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
    (view,) = (await _config(hass, "muj-cez"))["views"]
    text = _overview(view)
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
    (view,) = (await _config(hass, "muj-cez"))["views"]
    text = _overview(view)
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


def test_is_legacy() -> None:
    assert all(
        dashboard._is_legacy(p) for p in ("cez", "cez-2", "cez-ceny", "cez-ceny-3", "cez-odecet")
    )
    assert not any(
        dashboard._is_legacy(p)
        for p in ("home", "cez-x", "cezceny", None, "cez-ceny-", "cez-859182400500000007")
    )


async def test_second_point_own_tab(
    hass: HomeAssistant, mock_client: AsyncMock, freezer: FrozenDateTimeFactory
) -> None:
    await _setup(hass, freezer, DASHBOARD_NEW)
    coordinator = hass.config_entries.async_entries(DOMAIN)[0].runtime_data
    spd = next(iter(coordinator.data.supply_points.values()))
    other = dataclasses.replace(
        spd,
        supply_point=dataclasses.replace(
            spd.supply_point, ean="859182400500000007", name="Jiná 2, Valašské Meziříčí"
        ),
    )
    data = dataclasses.replace(coordinator.data, supply_points={"a": spd, "b": other})
    views = dashboard.build_views(hass, coordinator.config_entry.entry_id, data, prices=False)
    assert [v["path"] for v in views] == [f"cez-{spd.supply_point.ean}", "cez-859182400500000007"]
    assert views[1]["title"] == "⚡ Jiná 2 · 0000007"
    tabs = _tabs(views[1])
    assert list(tabs) == ["Přehled", "Odečet"]
    assert tabs["Odečet"]["cards"][0]["ean"] == "859182400500000007"


def _view(entry_id: str, path: str) -> dict[str, Any]:
    card = {"type": dashboard.TABS_CARD, "id": path, "entry_id": entry_id, "tabs": []}
    return {"path": path, "title": path, "type": "panel", "cards": [card]}


async def test_entries_share_dashboard(hass: HomeAssistant) -> None:
    """Accounts of one login write into one dashboard without removing each other's tabs."""
    assert await async_setup_component(hass, "lovelace", {})
    collection = dashboard._dashboards_collection(hass)
    await collection.async_create_item({"url_path": "cez-shared", "title": "ČEZ"})
    await hass.async_block_till_done()
    dash = hass.data[LOVELACE_DATA].dashboards["cez-shared"]
    await dash.async_save({"views": [{"path": "home"}]})
    load = dash.async_load

    async def slow_load(force: bool) -> dict[str, Any]:
        config = await load(force)
        await asyncio.sleep(0.01)  # the other entry runs meanwhile
        return config

    dash.async_load = slow_load
    # Both entries write at the same time (setup after a restart).
    await asyncio.gather(
        dashboard.async_write_dashboard(hass, "cez-shared", [_view("a", "cez-1111")], "a"),
        dashboard.async_write_dashboard(hass, "cez-shared", [_view("b", "cez-2222")], "b"),
    )
    paths = [v["path"] for v in (await load(False))["views"]]
    assert paths == ["home", "cez-1111", "cez-2222"]
    # Entry a: a point was removed and another added, b stays.
    await dashboard.async_write_dashboard(hass, "cez-shared", [_view("a", "cez-3333")], "a")
    paths = [v["path"] for v in (await load(False))["views"]]
    assert paths == ["home", "cez-3333", "cez-2222"]


async def test_reload_notification(
    hass: HomeAssistant, mock_client: AsyncMock, freezer: FrozenDateTimeFactory
) -> None:
    """New tabs (or newly installed cards) load only with the next page load: notify once."""
    from homeassistant.components import persistent_notification

    def notifications() -> dict[str, Any]:
        return persistent_notification._async_get_or_create_notifications(hass)

    with patch.object(dashboard, "async_missing_cards", AsyncMock(return_value=[])):
        entry = await _setup(hass, freezer, DASHBOARD_NEW)
        note = notifications()[dashboard.RELOAD_NOTIFICATION]
        assert "F5" in note["message"] and "(/muj-cez)" in note["message"]
        persistent_notification.async_dismiss(hass, dashboard.RELOAD_NOTIFICATION)
        await dashboard.async_update_dashboard(hass, entry)  # tabs exist already
        assert dashboard.RELOAD_NOTIFICATION not in notifications()
    # Cards installed now: a reload is needed again (without reloading the entry).
    object.__setattr__(
        entry, "options", MappingProxyType({**entry.options, CONF_INSTALL_CARDS: True})
    )
    missing = AsyncMock(side_effect=[["button-card"], []])
    with (
        patch.object(dashboard, "async_missing_cards", missing),
        patch.object(dashboard, "async_install_cards", AsyncMock()),
    ):
        await dashboard.async_update_dashboard(hass, entry)
    assert dashboard.RELOAD_NOTIFICATION in notifications()
