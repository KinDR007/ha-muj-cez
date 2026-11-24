"""Required dashboard cards: detection of missing Lovelace resources (no installs)."""

from __future__ import annotations

from typing import Any

import pytest
from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from custom_components.muj_cez import cards


@pytest.fixture
async def lovelace(hass: HomeAssistant) -> Any:
    assert await async_setup_component(hass, "lovelace", {})
    resources = hass.data[LOVELACE_DATA].resources
    if not resources.loaded:
        await resources.async_load()
    return resources


async def test_missing_cards(hass: HomeAssistant, lovelace: Any) -> None:
    assert await cards.async_missing_cards(hass) == [c.name for c in cards.CARDS]
    await lovelace.async_create_item(
        {"res_type": "module", "url": "/hacsfiles/button-card/button-card.js"}
    )
    await lovelace.async_create_item(
        {"res_type": "module", "url": "/hacsfiles/mini-graph-card/mini-graph-card-bundle.js"}
    )
    assert await cards.async_missing_cards(hass) == ["stack-in-card"]


async def test_missing_cards_without_lovelace(hass: HomeAssistant) -> None:
    assert await cards.async_missing_cards(hass) == [c.name for c in cards.CARDS]
