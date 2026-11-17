"""Chart unit selector used by dashboards (kWh / CZK)."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .coordinator import MujCezConfigEntry
from .entity import account_device_info

PARALLEL_UPDATES = 0
UNIT_OPTIONS = ["kwh", "czk"]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MujCezConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([MujCezChartUnitSelect(entry)])


class MujCezChartUnitSelect(SelectEntity, RestoreEntity):
    """Local UI state only; does not talk to the portal."""

    _attr_has_entity_name = True
    _attr_translation_key = "chart_unit"
    _attr_options = UNIT_OPTIONS
    _attr_current_option = UNIT_OPTIONS[0]
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, entry: MujCezConfigEntry) -> None:
        self._attr_unique_id = f"{entry.entry_id}_chart_unit"
        self._attr_device_info = account_device_info(entry)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last and last.state in UNIT_OPTIONS:
            self._attr_current_option = last.state

    async def async_select_option(self, option: str) -> None:
        self._attr_current_option = option
        self.async_write_ha_state()
