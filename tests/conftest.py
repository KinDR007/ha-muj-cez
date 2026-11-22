"""Shared test fixtures."""

from __future__ import annotations

import json
from collections.abc import Generator
from datetime import date
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from custom_components.muj_cez import api

FIXTURES = Path(__file__).parent / "fixtures"
TODAY = date(2026, 11, 16)
UID = "0000111111110002222222859100000000000001"
USERNAME = "user@example.com"
PASSWORD = "secret"


def load(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text())


def sample_data(today: date = TODAY) -> api.CezData:
    sp = api.parse_supply_points(load("supply_points.json"))[0]
    names = api.contract_names([sp], load("historical_supply_points.json"))
    documents = api.parse_documents(load("billings.json"), names)
    history = api.parse_consumption_periods(load("consumption_history.json"))
    simulation = api.parse_simulation(load("simulation.json"))
    spd = api.SupplyPointData(
        supply_point=sp,
        simulation=simulation,
        advance_plan=api.parse_advance_plan(load("advance_plan.json"), today),
        last_period=history[-1],
        meter_reading=api.parse_meter_readings(load("meter_readings.json"), today),
        contract=api.parse_contract_info(
            load("contract_detail.json"), load("distribution_rate.json")
        ),
        advance_settings=api.parse_advance_settings(
            load("advance_settings.json"), load("advance_events.json")
        ),
        billing=api.summarize_billing(documents, sp.agreement_id, today),
        periods=api.build_billing_periods(
            history,
            documents,
            sp.agreement_id,
            simulation,
            api.parse_advance_plan(load("advance_plan.json"), today),
        ),
        months=api.parse_simulation_months(load("simulation.json")),
        sim_items=api.parse_simulation_items(load("simulation.json")),
        readings=api.parse_meter_reading_history(load("meter_readings.json"), today),
        outages=api.parse_outages(load("outages.json"), sp.ean),
    )
    return api.CezData(
        supply_points={sp.uid: spd},
        unread_messages=api.parse_unread_messages(load("messages_summary.json")),
        documents=documents,
    )


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable custom integrations in all tests."""


@pytest.fixture
def mock_client() -> Generator[AsyncMock]:
    """Patch CezClient in both the integration and the config flow."""
    client = AsyncMock(spec=api.CezClient)
    client.fetch_all.return_value = sample_data()
    client.get_supply_points.return_value = api.parse_supply_points(load("supply_points.json"))
    client.get_profile_quarters.return_value = {}
    client.get_accounts.return_value = (["0011111111"], "0011111111")
    with (
        patch("custom_components.muj_cez.CezClient", return_value=client),
        patch("custom_components.muj_cez.config_flow.CezClient", return_value=client),
    ):
        yield client


class FakeDip:
    """ČEZ Distribuce client stub: `signals` per EAN (default: no HDO), or `error`."""

    signals_data: dict[str, Any] = {}
    error: Exception | None = None
    calls = 0

    def __init__(
        self, username: str, password: str, factory: Any = None, detach: bool = False
    ) -> None:
        self.username = username

    async def __aenter__(self) -> FakeDip:
        type(self).calls += 1
        if self.error:
            raise self.error
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    async def signals(self, ean: str) -> Any:
        return self.signals_data.get(ean, self.signals_data.get("*"))


@pytest.fixture(autouse=True)
def fake_dip() -> Generator[type[FakeDip]]:
    """Never contact the distribution portal in tests."""
    FakeDip.signals_data, FakeDip.error, FakeDip.calls = {}, None, 0
    with patch("custom_components.muj_cez.coordinator.DipClient", FakeDip):
        yield FakeDip


@pytest.fixture(autouse=True)
def no_profile_pause() -> Generator[None]:
    """No pause between the 15 min data requests (the backfill would wait in frozen time)."""
    with patch("custom_components.muj_cez.profile.REQUEST_PAUSE", 0):
        yield
