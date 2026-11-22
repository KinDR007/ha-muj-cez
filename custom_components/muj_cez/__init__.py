"""The Muj CEZ integration."""

from __future__ import annotations

import asyncio

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration

from .api import CezClient
from .const import (
    CONF_DASHBOARD,
    CONF_PARTNER,
    DASHBOARD_OFF,
    DOMAIN,
    price_breakdown_enabled,
)
from .coordinator import MujCezConfigEntry, MujCezCoordinator
from .dashboard import async_update_dashboard
from .frontend import async_register_frontend
from .pricing import InvoiceStore
from .profile import ProfileStore
from .services import async_setup_services
from .websocket import async_setup_websocket

DASHBOARD_WAIT_SECONDS = 30
# Pause after the entities appear so all platforms finish adding theirs.
DASHBOARD_SETTLE = 1.0
PLATFORMS = [Platform.BUTTON, Platform.CALENDAR, Platform.SELECT, Platform.SENSOR]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    async_setup_services(hass)
    async_setup_websocket(hass)
    integration = await async_get_integration(hass, DOMAIN)
    await async_register_frontend(hass, str(integration.version))
    return True


async def async_setup_entry(hass: HomeAssistant, entry: MujCezConfigEntry) -> bool:
    client = CezClient(
        async_get_clientsession(hass),
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
        entry.data.get(CONF_PARTNER),
    )
    coordinator = MujCezCoordinator(hass, entry, client)
    if not price_breakdown_enabled(entry.options):
        # Turned off: drop the downloaded invoices and price lists.
        await coordinator.invoices.async_remove()
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    entry.async_on_unload(coordinator.async_setup_schedule())
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    if entry.options.get(CONF_DASHBOARD) not in (None, "", DASHBOARD_OFF):
        entry.async_create_background_task(
            hass, _async_dashboard_after_setup(hass, entry), f"{DOMAIN}_dashboard"
        )
    return True


async def _async_dashboard_after_setup(hass: HomeAssistant, entry: MujCezConfigEntry) -> None:
    """Write the dashboard once the entities are registered (they are added async)."""
    registry = er.async_get(hass)
    for _ in range(DASHBOARD_WAIT_SECONDS):
        if any(e.config_entry_id == entry.entry_id for e in registry.entities.values()):
            break
        await asyncio.sleep(1)
    await asyncio.sleep(DASHBOARD_SETTLE)
    await async_update_dashboard(hass, entry)


async def async_unload_entry(hass: HomeAssistant, entry: MujCezConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: MujCezConfigEntry) -> None:
    """Delete the stored 15 min data, invoices and price lists of the entry."""
    await ProfileStore(hass, entry.entry_id).async_remove()
    await InvoiceStore(hass, entry.entry_id).async_remove()
