"""Manual invoice refresh of a consumption supply point (price breakdown)."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import price_breakdown_enabled
from .coordinator import MujCezConfigEntry, MujCezCoordinator
from .entity import supply_point_device_info

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MujCezConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    if not price_breakdown_enabled(entry.options):
        return
    coordinator = entry.runtime_data
    async_add_entities(
        MujCezInvoiceButton(coordinator, uid)
        for uid, spd in (coordinator.data.supply_points if coordinator.data else {}).items()
        if spd.supply_point.invoiced
    )


class MujCezInvoiceButton(ButtonEntity):
    """Downloads new invoices and price lists of the point now."""

    _attr_has_entity_name = True
    _attr_translation_key = "refresh_invoices"

    def __init__(self, coordinator: MujCezCoordinator, uid: str) -> None:
        self._coordinator = coordinator
        self._uid = uid
        self._attr_unique_id = f"{uid}_refresh_invoices"
        sp = coordinator.data.supply_points[uid].supply_point
        self._attr_device_info = supply_point_device_info(sp)

    async def async_press(self) -> None:
        await self._coordinator.async_refresh_invoices(self._uid)
