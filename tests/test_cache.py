"""Portal data kept between restarts (no new download until the next scheduled update)."""

from __future__ import annotations

import json
from datetime import datetime
from functools import partial
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import CoreState, HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.muj_cez import api
from custom_components.muj_cez.cache import decode, encode, last_scheduled_run
from custom_components.muj_cez.const import CONF_HDO, DOMAIN, PERIOD_MONTHLY, PERIOD_WEEKLY
from custom_components.muj_cez.coordinator import is_update_day

from .conftest import PASSWORD, UID, USERNAME, FakeDip, load, sample_data
from .test_gas import gas_data
from .test_grid_ha import pv_data

TZ = ZoneInfo("Europe/Prague")


@pytest.mark.parametrize("make", [sample_data, gas_data, pv_data])
def test_roundtrip(make) -> None:
    data = make()
    stored = json.loads(json.dumps(encode(data)))  # what the Store writes
    assert decode(api.CezData, stored) == data


def test_last_scheduled_run() -> None:
    now = datetime(2026, 11, 18, 6, 0, tzinfo=TZ)  # Wednesday
    daily = last_scheduled_run(now, (0, 0, 0), lambda _d: True)
    assert daily == datetime(2026, 11, 18, 0, 0, tzinfo=TZ)
    late = last_scheduled_run(now, (7, 30, 0), lambda _d: True)
    assert late == datetime(2026, 11, 17, 7, 30, tzinfo=TZ)
    weekly = last_scheduled_run(now, (0, 0, 0), partial(is_update_day, PERIOD_WEEKLY))
    assert weekly == datetime(2026, 11, 16, 0, 0, tzinfo=TZ)  # Monday
    monthly = last_scheduled_run(now, (0, 0, 0), partial(is_update_day, PERIOD_MONTHLY))
    assert monthly == datetime(2026, 11, 1, 0, 0, tzinfo=TZ)


@pytest.fixture
async def entry(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> MockConfigEntry:
    await hass.config.async_set_time_zone("Europe/Prague")
    freezer.move_to(datetime(2026, 11, 16, 12, 0, tzinfo=TZ))
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=USERNAME, data={CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD}
    )
    entry.add_to_hass(hass)
    return entry


async def _start(hass: HomeAssistant, entry: MockConfigEntry, booting: bool) -> None:
    """Set up the entry as at the HA start (booting) or as a reload of a running HA."""
    if entry.runtime_data if hasattr(entry, "runtime_data") else None:
        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
    hass.set_state(CoreState.not_running if booting else CoreState.running)
    await hass.config_entries.async_setup(entry.entry_id)
    hass.set_state(CoreState.running)
    await hass.async_block_till_done(wait_background_tasks=True)


def _state(hass: HomeAssistant, key: str) -> str:
    entity_id = er.async_get(hass).async_get_entity_id("sensor", DOMAIN, f"{UID}_{key}")
    return hass.states.get(entity_id).state


async def test_restart_uses_cached_data(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    mock_client: AsyncMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    await _start(hass, entry, booting=True)  # nothing cached yet: download
    assert mock_client.fetch_all.call_count == 1
    updated = _state(hass, "last_update")

    freezer.move_to(datetime(2026, 11, 16, 20, 0, tzinfo=TZ))  # before the next 00:00 run
    await _start(hass, entry, booting=True)
    assert mock_client.fetch_all.call_count == 1
    assert _state(hass, "invoice_balance") == "-1947.99"
    assert _state(hass, "last_update") == updated  # time of the download, not of the start


async def test_stale_cache_shown_then_refreshed(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    mock_client: AsyncMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    await _start(hass, entry, booting=True)
    freezer.move_to(datetime(2026, 11, 17, 8, 0, tzinfo=TZ))  # the 00:00 run was missed
    fresh = sample_data()
    fresh.supply_points[UID].simulation.total_amount = -100.0
    mock_client.fetch_all.return_value = fresh
    started = []

    async def first_refresh_done(*_args) -> None:
        started.append(mock_client.fetch_all.call_count)

    with patch(
        "custom_components.muj_cez.coordinator.MujCezCoordinator.async_scheduled_refresh",
        autospec=True,
        side_effect=first_refresh_done,
    ) as refresh:
        await _start(hass, entry, booting=True)
    # Set up from the cache without downloading, refresh requested in the background.
    assert started == [1] and refresh.call_count == 1
    assert _state(hass, "invoice_balance") == "-1947.99"
    await entry.runtime_data.async_scheduled_refresh()
    await hass.async_block_till_done()
    assert mock_client.fetch_all.call_count == 2
    assert _state(hass, "invoice_balance") == "-100.0"


async def test_reload_downloads(
    hass: HomeAssistant, entry: MockConfigEntry, mock_client: AsyncMock
) -> None:
    await _start(hass, entry, booting=True)
    await _start(hass, entry, booting=False)
    assert mock_client.fetch_all.call_count == 2


async def test_cache_of_other_version_ignored(
    hass: HomeAssistant, entry: MockConfigEntry, mock_client: AsyncMock
) -> None:
    await _start(hass, entry, booting=True)
    with patch(
        "custom_components.muj_cez.coordinator.DataCache.__init__",
        autospec=True,
        side_effect=lambda self, h, e, identity: _orig_init(
            self, h, e, {**identity, "version": "9.9.9"}
        ),
    ):
        await _start(hass, entry, booting=True)
    assert mock_client.fetch_all.call_count == 2


async def test_hdo_not_downloaded_again_after_restart(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    mock_client: AsyncMock,
    fake_dip: type[FakeDip],
    freezer: FrozenDateTimeFactory,
) -> None:
    hass.config_entries.async_update_entry(entry, options={CONF_HDO: True})
    fake_dip.signals_data = {"*": load("dip_signals.json")}
    await _start(hass, entry, booting=True)
    assert fake_dip.calls == 1
    schedule = entry.runtime_data.data.hdo
    assert schedule
    freezer.move_to(datetime(2026, 11, 16, 14, 0, tzinfo=TZ))  # within HDO_MAX_AGE
    await _start(hass, entry, booting=True)
    assert fake_dip.calls == 1
    assert entry.runtime_data.data.hdo == schedule  # from the stored schedule


from custom_components.muj_cez.cache import DataCache  # noqa: E402

_orig_init = DataCache.__init__
