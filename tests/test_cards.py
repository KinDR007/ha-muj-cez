"""Installing the dashboard cards (Marketplace / HACS commands, GitHub fallback, repair flow)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from homeassistant.components import websocket_api
from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.muj_cez import cards, dashboard, repairs
from custom_components.muj_cez.const import DOMAIN

MODULE = b"class X extends HTMLElement{};customElements.define('x-card', X);"


@pytest.fixture
async def lovelace(hass: HomeAssistant) -> Any:
    assert await async_setup_component(hass, "lovelace", {})
    resources = hass.data[LOVELACE_DATA].resources
    if not resources.loaded:
        await resources.async_load()
    return resources


def _register_store(hass: HomeAssistant, store: str, installed: list[str], resources: Any) -> None:
    """Fake Marketplace/HACS websocket commands (list + download adding the resource)."""
    repos = [
        {"id": str(i), "full_name": card.repo, "installed": False}
        for i, card in enumerate(cards.CARDS)
    ]

    @websocket_api.websocket_command({"type": f"{store}/repositories/list"})
    @websocket_api.require_admin
    @websocket_api.async_response
    async def list_repos(hass: HomeAssistant, connection: Any, msg: dict) -> None:
        connection.send_message(websocket_api.result_message(msg["id"], repos))

    @websocket_api.websocket_command({"type": f"{store}/repository/download", "repository": str})
    @websocket_api.require_admin
    @websocket_api.async_response
    async def download(hass: HomeAssistant, connection: Any, msg: dict) -> None:
        card = cards.CARDS[int(msg["repository"])]
        installed.append(card.name)
        await resources.async_create_item(
            {"res_type": "module", "url": f"/{store}files/{card.name}/{card.asset}"}
        )
        connection.send_message(websocket_api.result_message(msg["id"], {}))

    websocket_api.async_register_command(hass, list_repos)
    websocket_api.async_register_command(hass, download)


async def test_install_via_marketplace(hass: HomeAssistant, lovelace: Any) -> None:
    installed: list[str] = []
    _register_store(hass, "marketplace", installed, lovelace)
    assert await cards.async_missing_cards(hass) == [c.name for c in cards.CARDS]
    result = await cards.async_install_cards(hass, ["button-card", "mini-graph-card"])
    assert result == {"button-card": "marketplace", "mini-graph-card": "marketplace"}
    assert installed == ["button-card", "mini-graph-card"]
    assert await cards.async_missing_cards(hass) == ["stack-in-card"]


async def test_install_via_hacs_when_no_marketplace(hass: HomeAssistant, lovelace: Any) -> None:
    installed: list[str] = []
    _register_store(hass, "hacs", installed, lovelace)
    result = await cards.async_install_cards(hass, ["stack-in-card"])
    assert result == {"stack-in-card": "hacs"}


async def test_install_from_github(
    hass: HomeAssistant, lovelace: Any, aioclient_mock: AiohttpClientMocker
) -> None:
    card = cards.CARDS[0]
    asset_url = f"https://github.com/{card.repo}/releases/download/v7.0.1/{card.asset}"
    aioclient_mock.get(
        cards.GITHUB_API.format(repo=card.repo),
        json={
            "tag_name": "v7.0.1",
            "assets": [{"name": card.asset, "browser_download_url": asset_url}],
        },
    )
    aioclient_mock.get(asset_url, content=MODULE)
    result = await cards.async_install_cards(hass, [card.name])
    assert result == {card.name: "github"}
    path = hass.config.path(*cards.LOCAL_DIR, card.asset)
    content = await hass.async_add_executor_job(Path(path).read_bytes)
    assert content == MODULE
    urls = [item["url"] for item in lovelace.async_items()]
    assert urls == [f"/local/muj_cez/cards/{card.asset}?v=v7.0.1"]
    assert card.name not in await cards.async_missing_cards(hass)


async def test_github_rejects_unexpected_content(
    hass: HomeAssistant, lovelace: Any, aioclient_mock: AiohttpClientMocker
) -> None:
    card = cards.CARDS[1]
    asset_url = f"https://example.invalid/{card.asset}"
    aioclient_mock.get(
        cards.GITHUB_API.format(repo=card.repo),
        json={
            "tag_name": "0.2.0",
            "assets": [{"name": card.asset, "browser_download_url": asset_url}],
        },
    )
    aioclient_mock.get(asset_url, content=b"<html>not a module</html>")
    result = await cards.async_install_cards(hass, [card.name])
    assert "unexpected content" in result[card.name]
    assert list(lovelace.async_items()) == []


async def test_repair_flow_installs_cards(hass: HomeAssistant, lovelace: Any) -> None:
    installed: list[str] = []
    _register_store(hass, "marketplace", installed, lovelace)
    ir.async_create_issue(
        hass,
        DOMAIN,
        dashboard.ISSUE_CARDS,
        is_fixable=True,
        severity=ir.IssueSeverity.WARNING,
        translation_key=dashboard.ISSUE_CARDS,
        translation_placeholders={"cards": "x"},
    )
    flow = await repairs.async_create_fix_flow(hass, dashboard.ISSUE_CARDS, None)
    flow.hass = hass
    flow.issue_id = dashboard.ISSUE_CARDS
    flow.handler = DOMAIN
    flow.flow_id = "1"
    result = await flow.async_step_init()
    assert result["step_id"] == "confirm"
    assert "button-card" in result["description_placeholders"]["cards"]
    result = await flow.async_step_confirm({})
    assert result["type"] == "create_entry"
    assert sorted(installed) == sorted(c.name for c in cards.CARDS)
    assert ir.async_get(hass).async_get_issue(DOMAIN, dashboard.ISSUE_CARDS) is None
