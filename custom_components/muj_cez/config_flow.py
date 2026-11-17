"""Config flow for the Muj CEZ integration."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlowWithReload
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    BooleanSelector,
    EntitySelector,
    EntitySelectorConfig,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
    TimeSelector,
)

from .api import CezAuthError, CezClient, CezError
from .const import (
    CONF_DASHBOARD,
    CONF_HDO,
    CONF_INSTALL_CARDS,
    CONF_REFERENCE_EXPORT_SENSOR,
    CONF_REFERENCE_SENSOR,
    CONF_SPOT_PRICE_SENSOR,
    CONF_UPDATE_PERIOD,
    CONF_UPDATE_TIME,
    DASHBOARD_NEW,
    DASHBOARD_OFF,
    DEFAULT_UPDATE_PERIOD,
    DEFAULT_UPDATE_TIME,
    DOMAIN,
    UPDATE_PERIODS,
)
from .coordinator import MujCezConfigEntry
from .dashboard import async_dashboard_choices, async_energy_grid_sensors, suggested_options

_LOGGER = logging.getLogger(__name__)

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): TextSelector(
            TextSelectorConfig(type=TextSelectorType.EMAIL, autocomplete="username")
        ),
        vol.Required(CONF_PASSWORD): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD, autocomplete="current-password")
        ),
    }
)
REAUTH_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PASSWORD): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD, autocomplete="current-password")
        ),
    }
)


_DASHBOARD_LABELS = {
    "cs": {"off": "Nevytvářet", "new": "Nový dashboard „ČEZ“"},
    "en": {"off": "Do not create", "new": 'New dashboard "ČEZ"'},
}


async def settings_form(
    hass: HomeAssistant, current: Mapping[str, Any] | None
) -> tuple[vol.Schema, dict[str, Any]]:
    """Settings schema and suggested values (current options, else detected defaults).

    Grid import/export reference sensors default to the Energy dashboard grid source,
    the spot price sensor to cz_energy_spot_prices when installed.
    """
    labels = _DASHBOARD_LABELS.get(hass.config.language, _DASHBOARD_LABELS["en"])
    dashboards = [
        {"value": DASHBOARD_OFF, "label": labels["off"]},
        {"value": DASHBOARD_NEW, "label": labels["new"]},
        *await async_dashboard_choices(hass),
    ]
    schema = vol.Schema(
        {
            vol.Required(CONF_UPDATE_PERIOD, default=DEFAULT_UPDATE_PERIOD): SelectSelector(
                SelectSelectorConfig(
                    options=UPDATE_PERIODS,
                    mode=SelectSelectorMode.DROPDOWN,
                    translation_key=CONF_UPDATE_PERIOD,
                )
            ),
            vol.Required(CONF_UPDATE_TIME, default=DEFAULT_UPDATE_TIME): TimeSelector(),
            vol.Optional(CONF_REFERENCE_SENSOR): EntitySelector(
                EntitySelectorConfig(domain="sensor", device_class="energy")
            ),
            vol.Optional(CONF_REFERENCE_EXPORT_SENSOR): EntitySelector(
                EntitySelectorConfig(domain="sensor", device_class="energy")
            ),
            vol.Optional(CONF_SPOT_PRICE_SENSOR): EntitySelector(
                EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(CONF_DASHBOARD, default=DASHBOARD_OFF): SelectSelector(
                SelectSelectorConfig(options=dashboards, mode=SelectSelectorMode.DROPDOWN)
            ),
            vol.Optional(CONF_INSTALL_CARDS, default=True): BooleanSelector(),
            vol.Optional(CONF_HDO, default=True): BooleanSelector(),
        }
    )
    if current is None:
        suggested = suggested_options(hass, await async_energy_grid_sensors(hass))
        suggested[CONF_DASHBOARD] = DASHBOARD_NEW
    else:
        suggested = dict(current)
    valid = {d["value"] for d in dashboards}
    if suggested.get(CONF_DASHBOARD) not in valid:
        suggested[CONF_DASHBOARD] = DASHBOARD_OFF
    return schema, suggested


async def _validate(hass: HomeAssistant, username: str, password: str) -> dict[str, str]:
    client = CezClient(async_get_clientsession(hass), username, password)
    try:
        await client.authenticate()
        if not await client.get_supply_points():
            return {"base": "no_supply_points"}
    except CezAuthError:
        return {"base": "invalid_auth"}
    except CezError:
        return {"base": "cannot_connect"}
    except Exception:
        _LOGGER.exception("Unexpected error during validation")
        return {"base": "unknown"}
    return {}


class MujCezConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1
    _data: dict[str, Any]

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            username = user_input[CONF_USERNAME].strip()
            await self.async_set_unique_id(username.lower())
            self._abort_if_unique_id_configured()
            errors = await _validate(self.hass, username, user_input[CONF_PASSWORD])
            if not errors:
                self._data = {CONF_USERNAME: username, CONF_PASSWORD: user_input[CONF_PASSWORD]}
                return await self.async_step_settings()
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                USER_SCHEMA, {CONF_USERNAME: (user_input or {}).get(CONF_USERNAME)}
            ),
            errors=errors,
        )

    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Update schedule, reference sensors and dashboard (prefilled from Energy)."""
        if user_input is not None:
            return self.async_create_entry(
                title=self._data[CONF_USERNAME], data=self._data, options=user_input
            )
        schema, suggested = await settings_form(self.hass, None)
        return self.async_show_form(
            step_id="settings", data_schema=self.add_suggested_values_to_schema(schema, suggested)
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = await _validate(
                self.hass, entry.data[CONF_USERNAME], user_input[CONF_PASSWORD]
            )
            if not errors:
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_PASSWORD: user_input[CONF_PASSWORD]}
                )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=REAUTH_SCHEMA,
            errors=errors,
            description_placeholders={"username": entry.data[CONF_USERNAME]},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: MujCezConfigEntry) -> MujCezOptionsFlow:
        return MujCezOptionsFlow()


class MujCezOptionsFlow(OptionsFlowWithReload):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        schema, suggested = await settings_form(self.hass, self.config_entry.options)
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(schema, suggested),
        )
