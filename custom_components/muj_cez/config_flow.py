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

from .api import CezAuthError, CezClient, CezError, InvoiceSimulation, SupplyPoint
from .const import (
    CONF_DASHBOARD,
    CONF_HDO,
    CONF_INSTALL_CARDS,
    CONF_INVOICE_PERIODS,
    CONF_PARTNER,
    CONF_PRICE_BREAKDOWN,
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
    INVOICE_PERIOD_DAYS,
    UPDATE_PERIODS,
    docs_url,
    price_breakdown_enabled,
)
from .coordinator import MujCezConfigEntry
from .dashboard import async_dashboard_choices, async_energy_grid_sensors, suggested_options
from .pricing import suggested_period

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
            vol.Optional(CONF_PRICE_BREAKDOWN, default=False): BooleanSelector(),
        }
    )
    if current is None:
        suggested = suggested_options(hass, await async_energy_grid_sensors(hass))
        suggested[CONF_DASHBOARD] = DASHBOARD_NEW
    else:
        suggested = dict(current)
        suggested[CONF_PRICE_BREAKDOWN] = price_breakdown_enabled(current)
    valid = {d["value"] for d in dashboards}
    if suggested.get(CONF_DASHBOARD) not in valid:
        suggested[CONF_DASHBOARD] = DASHBOARD_OFF
    return schema, suggested


type InvoicePoint = tuple[SupplyPoint, InvoiceSimulation | None]


def invoice_form(
    points: list[InvoicePoint], current: Mapping[str, str] | None
) -> tuple[vol.Schema, dict[str, Any], dict[str, tuple[str, str]]]:
    """Invoice check period per consumption point: schema, suggested values and
    {field: (uid, period suggested by the billing period)}. A period the user chose
    (current) is shown instead of the suggested one."""
    fields: dict[str, tuple[str, str]] = {}
    schema: dict[Any, Any] = {}
    values: dict[str, Any] = {}
    selector = SelectSelector(
        SelectSelectorConfig(
            options=list(INVOICE_PERIOD_DAYS),
            mode=SelectSelectorMode.DROPDOWN,
            translation_key="invoice_period",
        )
    )
    for sp, simulation in points:
        label = f"{sp.name} · {sp.ean[-7:]}" if sp.name else sp.ean
        auto = suggested_period(simulation)
        fields[label] = (sp.uid, auto)
        schema[vol.Required(label, default=auto)] = selector
        values[label] = (current or {}).get(sp.uid) or auto
    return vol.Schema(schema), values, fields


def invoice_periods(
    user_input: Mapping[str, Any], fields: Mapping[str, tuple[str, str]]
) -> dict[str, str]:
    """Periods the user changed from the suggested ones (others follow the billing)."""
    return {
        uid: user_input[label]
        for label, (uid, auto) in fields.items()
        if user_input.get(label) and user_input[label] != auto
    }


async def _validate(
    hass: HomeAssistant, username: str, password: str, partner: str | None = None
) -> tuple[dict[str, str], CezClient]:
    client = CezClient(async_get_clientsession(hass), username, password, partner)
    try:
        await client.authenticate()
        if not await client.get_supply_points():
            return {"base": "no_supply_points"}, client
    except CezAuthError:
        return {"base": "invalid_auth"}, client
    except CezError:
        return {"base": "cannot_connect"}, client
    except Exception:
        _LOGGER.exception("Unexpected error during validation")
        return {"base": "unknown"}, client
    return {}, client


async def _invoice_points(client: CezClient) -> list[InvoicePoint]:
    """Consumption points with their billing simulation (one request per point)."""
    points: list[InvoicePoint] = []
    try:
        supply_points = await client.get_supply_points()
    except CezError as err:
        _LOGGER.debug("Supply points for the invoice step: %s", err)
        return points
    for sp in supply_points:
        if not sp.invoiced:
            continue
        try:
            simulation = (await client.get_simulation(sp))[0]
        except CezError as err:
            _LOGGER.debug("Simulation of %s: %s", sp.ean, err)
            simulation = None
        points.append((sp, simulation))
    return points


async def _accounts(client: CezClient) -> tuple[dict[str, str], str | None]:
    """Selectable customer accounts {partner: label} when the ČEZ ID has several.

    Labels show the addresses of the account's supply points; the default account first.
    """
    try:
        partners, default = await client.get_accounts()
    except CezError as err:
        _LOGGER.debug("Customer accounts not available: %s", err)
        return {}, None
    if len(partners) < 2:
        return {}, default
    labels: dict[str, str] = {}
    for partner in sorted(partners, key=lambda p: p != default):
        client.partner = partner
        try:
            places = {sp.address or sp.name for sp in await client.get_supply_points()}
        except CezError:
            places = set()
        labels[partner] = f"{partner}: {', '.join(sorted(places))}" if places else partner
    client.partner = None
    return labels, default


class MujCezConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1
    _data: dict[str, Any]
    _accounts: dict[str, str]
    _default: str | None
    _client: CezClient
    _options: dict[str, Any]
    _fields: dict[str, tuple[str, str]]

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            username = user_input[CONF_USERNAME].strip()
            errors, client = await _validate(self.hass, username, user_input[CONF_PASSWORD])
            if not errors:
                self._client = client
                self._data = {CONF_USERNAME: username, CONF_PASSWORD: user_input[CONF_PASSWORD]}
                self._accounts, self._default = await _accounts(client)
                if self._accounts:
                    return await self.async_step_account()
                await self.async_set_unique_id(username.lower())
                self._abort_if_unique_id_configured()
                return await self.async_step_settings()
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                USER_SCHEMA, {CONF_USERNAME: (user_input or {}).get(CONF_USERNAME)}
            ),
            errors=errors,
            description_placeholders={"docs_url": docs_url("instalace")},
        )

    async def async_step_account(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Customer account when the ČEZ ID has several (e.g. shared access)."""
        errors: dict[str, str] = {}
        if user_input is not None:
            partner = user_input[CONF_PARTNER]
            username = self._data[CONF_USERNAME]
            # The default account keeps the plain unique id (entries before accounts existed).
            uid = username.lower() if partner == self._default else f"{username.lower()}_{partner}"
            await self.async_set_unique_id(uid)
            self._abort_if_unique_id_configured()
            errors, client = await _validate(
                self.hass, username, self._data[CONF_PASSWORD], partner
            )
            if not errors:
                self._client = client
                self._data[CONF_PARTNER] = partner
                return await self.async_step_settings()
        options = [{"value": p, "label": label} for p, label in self._accounts.items()]
        schema = vol.Schema(
            {
                vol.Required(CONF_PARTNER, default=options[0]["value"]): SelectSelector(
                    SelectSelectorConfig(options=options, mode=SelectSelectorMode.LIST)
                )
            }
        )
        return self.async_show_form(step_id="account", data_schema=schema, errors=errors)

    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Update schedule, reference sensors and dashboard (prefilled from Energy)."""
        if user_input is not None:
            self._options = user_input
            if price_breakdown_enabled(user_input):
                return await self.async_step_invoices()
            return self._create()
        schema, suggested = await settings_form(self.hass, None)
        return self.async_show_form(
            step_id="settings",
            data_schema=self.add_suggested_values_to_schema(schema, suggested),
            description_placeholders={"docs_url": docs_url("nastaveni")},
        )

    async def async_step_invoices(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Invoice check period per consumption point, prefilled from its billing period."""
        if user_input is not None:
            self._options[CONF_INVOICE_PERIODS] = invoice_periods(user_input, self._fields)
            return self._create()
        points = await _invoice_points(self._client)
        if not points:
            return self._create()
        schema, values, self._fields = invoice_form(points, None)
        return self.async_show_form(
            step_id="invoices",
            data_schema=self.add_suggested_values_to_schema(schema, values),
            description_placeholders={"docs_url": docs_url("nastaveni")},
        )

    def _create(self) -> ConfigFlowResult:
        title = self._data[CONF_USERNAME]
        if self._data.get(CONF_PARTNER):
            title = f"{title} ({self._data[CONF_PARTNER]})"
        # A new dashboard needs a page reload to load the integration's cards.
        dashboard = self._options.get(CONF_DASHBOARD) not in (None, "", DASHBOARD_OFF)
        return self.async_create_entry(
            title=title,
            data=self._data,
            options=self._options,
            description="dashboard" if dashboard else None,
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            errors, _client = await _validate(
                self.hass,
                entry.data[CONF_USERNAME],
                user_input[CONF_PASSWORD],
                entry.data.get(CONF_PARTNER),
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
    _options: dict[str, Any]
    _fields: dict[str, tuple[str, str]]

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            self._options = dict(user_input)
            current = self.config_entry.options.get(CONF_INVOICE_PERIODS)
            if current:
                self._options[CONF_INVOICE_PERIODS] = current
            if price_breakdown_enabled(user_input) and self._points():
                return await self.async_step_invoices()
            return self.async_create_entry(data=self._options)
        schema, suggested = await settings_form(self.hass, self.config_entry.options)
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(schema, suggested),
            description_placeholders={"docs_url": docs_url("nastaveni")},
        )

    def _points(self) -> list[InvoicePoint]:
        coordinator = getattr(self.config_entry, "runtime_data", None)
        data = coordinator.data if coordinator else None
        if data is None:
            return []
        return [
            (spd.supply_point, spd.simulation)
            for spd in data.supply_points.values()
            if spd.supply_point.invoiced
        ]

    async def async_step_invoices(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Invoice check period per consumption point; a changed one is kept."""
        if user_input is not None:
            self._options[CONF_INVOICE_PERIODS] = invoice_periods(user_input, self._fields)
            return self.async_create_entry(data=self._options)
        schema, values, self._fields = invoice_form(
            self._points(), self.config_entry.options.get(CONF_INVOICE_PERIODS)
        )
        return self.async_show_form(
            step_id="invoices",
            data_schema=self.add_suggested_values_to_schema(schema, values),
            description_placeholders={"docs_url": docs_url("nastaveni")},
        )
