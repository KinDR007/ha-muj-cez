"""Config and options flow tests."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.muj_cez import api
from custom_components.muj_cez.api import CezAuthError, CezConnectionError
from custom_components.muj_cez.const import (
    CONF_DASHBOARD,
    CONF_HDO,
    CONF_INVOICE_PERIODS,
    CONF_PRICE_BREAKDOWN,
    CONF_REFERENCE_EXPORT_SENSOR,
    CONF_REFERENCE_SENSOR,
    CONF_UPDATE_PERIOD,
    CONF_UPDATE_TIME,
    DASHBOARD_NEW,
    DASHBOARD_OFF,
    DOMAIN,
)
from custom_components.muj_cez.dashboard import grid_sensors_from_energy

from .conftest import PASSWORD, USERNAME, load


async def test_user_flow(hass: HomeAssistant, mock_client: AsyncMock) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    assert result["description_placeholders"]["docs_url"].endswith("/docs/guide/instalace.md")
    with patch(
        "custom_components.muj_cez.config_flow.async_energy_grid_sensors",
        AsyncMock(return_value=("sensor.import_energy", "sensor.export_energy")),
    ):
        result = await hass.config_entries.flow.async_configure(
            # Upper case e-mail (phone keyboards): stored and used in lower case.
            result["flow_id"],
            {CONF_USERNAME: f" {USERNAME.capitalize()} ", CONF_PASSWORD: PASSWORD},
        )
    # Settings prefilled from the Energy dashboard, new dashboard suggested.
    assert result["step_id"] == "settings"
    suggested = {
        str(k): (k.description or {}).get("suggested_value") for k in result["data_schema"].schema
    }
    assert suggested[CONF_REFERENCE_SENSOR] == "sensor.import_energy"
    assert suggested[CONF_REFERENCE_EXPORT_SENSOR] == "sensor.export_energy"
    assert suggested[CONF_DASHBOARD] == DASHBOARD_NEW
    assert suggested[CONF_PRICE_BREAKDOWN] is None  # new entry: schema default off
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_UPDATE_PERIOD: "daily",
            CONF_UPDATE_TIME: "00:00:00",
            CONF_REFERENCE_SENSOR: "sensor.import_energy",
            CONF_DASHBOARD: DASHBOARD_OFF,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == USERNAME
    assert result["options"][CONF_REFERENCE_SENSOR] == "sensor.import_energy"
    assert result["options"][CONF_PRICE_BREAKDOWN] is False
    assert result["data"] == {CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD}
    assert result["result"].unique_id == USERNAME
    assert result["description"] is None  # no dashboard: nothing to reload


async def test_user_flow_with_dashboard_asks_for_reload(
    hass: HomeAssistant, mock_client: AsyncMock
) -> None:
    """The cards of a new dashboard load with the next page load: the success says so."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD}
    )
    with patch("custom_components.muj_cez.async_update_dashboard", AsyncMock()):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_UPDATE_PERIOD: "daily",
                CONF_UPDATE_TIME: "00:00:00",
                CONF_DASHBOARD: DASHBOARD_NEW,
            },
        )
        await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["description"] == "dashboard"


@pytest.mark.parametrize(
    ("side_effect", "supply_points", "error"),
    [
        (CezAuthError("x"), None, "invalid_auth"),
        (CezConnectionError("x"), None, "cannot_connect"),
        (RuntimeError("x"), None, "unknown"),
        (None, [], "no_supply_points"),
    ],
)
async def test_user_flow_errors(
    hass: HomeAssistant, mock_client: AsyncMock, side_effect, supply_points, error
) -> None:
    good_points = mock_client.get_supply_points.return_value
    mock_client.authenticate.side_effect = side_effect
    if supply_points is not None:
        mock_client.get_supply_points.return_value = supply_points
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}

    # Recovers after the problem is fixed.
    mock_client.authenticate.side_effect = None
    mock_client.get_supply_points.return_value = good_points
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD}
    )
    assert result["step_id"] == "settings"


async def test_already_configured(hass: HomeAssistant, mock_client: AsyncMock) -> None:
    MockConfigEntry(domain=DOMAIN, unique_id=USERNAME, data={}).add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_USERNAME: USERNAME.upper(), CONF_PASSWORD: PASSWORD}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reauth(hass: HomeAssistant, mock_client: AsyncMock) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=USERNAME, data={CONF_USERNAME: USERNAME, CONF_PASSWORD: "old"}
    )
    entry.add_to_hass(hass)
    result = await entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"

    mock_client.authenticate.side_effect = CezAuthError("x")
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PASSWORD: "bad"}
    )
    assert result["errors"] == {"base": "invalid_auth"}

    mock_client.authenticate.side_effect = None
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PASSWORD: "new"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_PASSWORD] == "new"
    await hass.async_block_till_done()


async def test_options_flow(hass: HomeAssistant, mock_client: AsyncMock) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=USERNAME, data={CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD}
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    # Entry from before the option existed: price breakdown suggested on.
    key = next(k for k in result["data_schema"].schema if k == CONF_PRICE_BREAKDOWN)
    assert key.description == {"suggested_value": True}
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_UPDATE_PERIOD: "weekly", CONF_UPDATE_TIME: "03:15:00"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {
        CONF_UPDATE_PERIOD: "weekly",
        CONF_UPDATE_TIME: "03:15:00",
        CONF_DASHBOARD: DASHBOARD_OFF,
        CONF_HDO: True,
        CONF_PRICE_BREAKDOWN: False,
    }


def test_grid_sensors_from_energy() -> None:
    new = {
        "energy_sources": [
            {"type": "grid", "stat_energy_from": "sensor.a", "stat_energy_to": "sensor.b"}
        ]
    }
    legacy = {
        "energy_sources": [
            {"type": "solar", "stat_energy_from": "sensor.pv"},
            {
                "type": "grid",
                "flow_from": [{"stat_energy_from": "sensor.a"}],
                "flow_to": [{"stat_energy_to": "sensor.b"}],
            },
        ]
    }
    assert grid_sensors_from_energy(new) == ("sensor.a", "sensor.b")
    assert grid_sensors_from_energy(legacy) == ("sensor.a", "sensor.b")
    external = {"energy_sources": [{"type": "grid", "stat_energy_from": "muj_cez:grid_import_1"}]}
    assert grid_sensors_from_energy(external) == (None, None)
    assert grid_sensors_from_energy(None) == (None, None)


def _fields(result: dict) -> dict[str, object]:
    return {
        str(k): (k.description or {}).get("suggested_value") for k in result["data_schema"].schema
    }


async def test_user_flow_invoice_periods(hass: HomeAssistant, mock_client: AsyncMock) -> None:
    """Price breakdown on: period per point, prefilled from the billing period."""
    mock_client.get_simulation.return_value = (
        api.parse_simulation(load("simulation.json")),
        [],
        [],
    )
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_UPDATE_PERIOD: "daily",
            CONF_UPDATE_TIME: "00:00:00",
            CONF_DASHBOARD: DASHBOARD_OFF,
            CONF_PRICE_BREAKDOWN: True,
        },
    )
    assert result["step_id"] == "invoices"
    sp = mock_client.get_supply_points.return_value[0]
    label = f"{sp.name} · {sp.ean[-7:]}"
    assert _fields(result) == {label: "yearly"}  # yearly billing period
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {label: "monthly"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["options"][CONF_INVOICE_PERIODS] == {sp.uid: "monthly"}


async def test_options_flow_invoice_periods(hass: HomeAssistant, mock_client: AsyncMock) -> None:
    """The period the user chose is shown and kept; the suggested one is not stored."""
    uid = next(iter(mock_client.fetch_all.return_value.supply_points))
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=USERNAME,
        data={CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD},
        options={CONF_PRICE_BREAKDOWN: True, CONF_INVOICE_PERIODS: {uid: "weekly"}},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_UPDATE_PERIOD: "daily", CONF_PRICE_BREAKDOWN: True}
    )
    assert result["step_id"] == "invoices"
    ((label, value),) = _fields(result).items()
    assert value == "weekly"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {label: "quarterly"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_INVOICE_PERIODS] == {uid: "quarterly"}
    # Back to the suggested period: follows the billing again.
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_UPDATE_PERIOD: "daily", CONF_PRICE_BREAKDOWN: True}
    )
    result = await hass.config_entries.options.async_configure(result["flow_id"], {label: "yearly"})
    assert entry.options[CONF_INVOICE_PERIODS] == {}
    # Price breakdown off: no step, the periods stay for later.
    entry_options = dict(entry.options, **{CONF_INVOICE_PERIODS: {uid: "weekly"}})
    hass.config_entries.async_update_entry(entry, options=entry_options)
    await hass.async_block_till_done()
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_UPDATE_PERIOD: "daily", CONF_PRICE_BREAKDOWN: False}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_INVOICE_PERIODS] == {uid: "weekly"}
