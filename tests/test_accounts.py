"""Several customer accounts under one ČEZ ID (shared access)."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.muj_cez import api
from custom_components.muj_cez.const import CONF_PARTNER, DOMAIN

from .conftest import PASSWORD, USERNAME, load

OWN, SHARED = "0011111111", "0022222222"


def test_parse_accounts() -> None:
    data = {"partners": [SHARED, OWN], "defaultPartner": SHARED, "email": "x"}
    assert api.parse_accounts(data) == ([SHARED, OWN], SHARED)
    assert api.parse_accounts({"partners": []}) == ([], None)
    assert api.parse_accounts(None) == ([], None)


class _Resp:
    status = 200

    async def text(self) -> str:
        return "{}"

    async def json(self, content_type: Any = None) -> dict:
        return {}

    async def __aenter__(self) -> _Resp:
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None


class _Session:
    def __init__(self) -> None:
        self.headers: list[dict[str, str]] = []

    def get(self, url: str, params: Any = None, headers: Any = None, timeout: Any = None) -> _Resp:
        self.headers.append(headers)
        return _Resp()


@pytest.mark.parametrize(("partner", "expected"), [(None, None), (OWN, OWN)])
async def test_partner_header(partner: str | None, expected: str | None) -> None:
    session = _Session()
    client = api.CezClient(session, USERNAME, PASSWORD, partner)  # type: ignore[arg-type]
    client._access_token, client._expires_at = "token", float("inf")
    await client._get("/supply-points/RetrieveSupplyPoints")
    assert session.headers[0].get(api.PARTNER_HEADER) == expected


def _accounts(mock_client: AsyncMock) -> None:
    own, shared = api.parse_supply_points(load("supply_points.json"))[0], None
    mock_client.get_accounts.return_value = ([SHARED, OWN], SHARED)
    shared = api.SupplyPoint("0000999", "859999", "Jinde", "Cizí 2, Brno", "", "", None, None)

    async def supply_points() -> list[api.SupplyPoint]:
        return [shared] if mock_client.partner in (None, SHARED) else [own]

    mock_client.get_supply_points.side_effect = supply_points


async def _to_account_step(hass: HomeAssistant) -> dict:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    return await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD}
    )


async def test_choose_own_account(hass: HomeAssistant, mock_client: AsyncMock) -> None:
    mock_client.partner = None
    _accounts(mock_client)
    result = await _to_account_step(hass)
    assert result["type"] is FlowResultType.FORM and result["step_id"] == "account"
    options = result["data_schema"].schema[CONF_PARTNER].config["options"]
    assert [o["value"] for o in options] == [SHARED, OWN]  # default account first
    assert options[0]["label"] == f"{SHARED}: Cizí 2, Brno"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_PARTNER: OWN})
    assert result["step_id"] == "settings"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_PARTNER] == OWN
    assert result["title"] == f"{USERNAME} ({OWN})"
    assert result["result"].unique_id == f"{USERNAME}_{OWN}"


async def test_default_account_matches_existing_entry(
    hass: HomeAssistant, mock_client: AsyncMock
) -> None:
    """An entry made before accounts existed is the default account: no duplicate."""
    MockConfigEntry(domain=DOMAIN, unique_id=USERNAME, data={CONF_USERNAME: USERNAME}).add_to_hass(
        hass
    )
    mock_client.partner = None
    _accounts(mock_client)
    result = await _to_account_step(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PARTNER: SHARED}
    )
    assert result["type"] is FlowResultType.ABORT and result["reason"] == "already_configured"


async def test_single_account_no_step(hass: HomeAssistant, mock_client: AsyncMock) -> None:
    result = await _to_account_step(hass)
    assert result["step_id"] == "settings"


async def test_accounts_unavailable(hass: HomeAssistant, mock_client: AsyncMock) -> None:
    mock_client.get_accounts.side_effect = api.CezConnectionError("HTTP 500")
    result = await _to_account_step(hass)
    assert result["step_id"] == "settings"
