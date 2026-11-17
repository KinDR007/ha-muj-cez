"""Repair flow: install the custom cards the generated dashboard needs."""

from __future__ import annotations

from typing import Any

from homeassistant.components.repairs import RepairsFlow
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import issue_registry as ir

from .cards import async_install_cards, async_missing_cards
from .const import DOMAIN

INSTALLED = ("marketplace", "hacs", "github")


class InstallCardsFlow(RepairsFlow):
    """Confirm and install the missing cards (Marketplace / HACS, else GitHub release)."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        return await self.async_step_confirm()

    async def async_step_confirm(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        missing = await async_missing_cards(self.hass)
        if user_input is None:
            return self.async_show_form(
                step_id="confirm", description_placeholders={"cards": ", ".join(missing) or "–"}
            )
        result = await async_install_cards(self.hass, missing)
        failed = {name: msg for name, msg in result.items() if msg not in INSTALLED}
        if failed:
            return self.async_abort(
                reason="install_failed",
                description_placeholders={
                    "error": "; ".join(f"{name}: {msg}" for name, msg in failed.items())
                },
            )
        ir.async_delete_issue(self.hass, DOMAIN, self.issue_id)
        return self.async_create_entry(data={})


async def async_create_fix_flow(
    hass: HomeAssistant, issue_id: str, data: dict[str, Any] | None
) -> RepairsFlow:
    return InstallCardsFlow()
