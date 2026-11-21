"""Meter reading: validation, register history and the card's websocket commands."""

from __future__ import annotations

from datetime import date
from typing import Any
from unittest.mock import AsyncMock

import pytest
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.typing import WebSocketGenerator

from custom_components.muj_cez import api, reading
from custom_components.muj_cez.const import DOMAIN

from .conftest import PASSWORD, USERNAME, load

TODAY = date(2026, 11, 21)
PREV = {"vt": reading.Previous(date(2026, 11, 16), 12882)}


def _codes(result: reading.Check) -> tuple[list[str], list[str]]:
    return [i.code for i in result.errors], [i.code for i in result.warnings]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("12 950", 12950), (12950, 12950), ("12950.0", 12950), (12950.0, 12950), ("12,5", None),
     ("abc", None), (True, None), ("-3", -3)],
)  # fmt: skip
def test_parse_value(raw: Any, expected: int | None) -> None:
    assert reading.parse_value(raw) == expected


def test_lower_is_error() -> None:
    """The portal: "Hodnota je nižší než předchozí stav ze dne 16. 11. 2026 (12882 kWh)"."""
    result = reading.check({"vt": "12345"}, ["vt"], PREV, {"vt": 5.0}, TODAY, TODAY)
    assert _codes(result) == (["lower"], [])
    assert result.errors[0].params == {"date": "2026-11-16", "value": 12882}
    assert not result.ok


def test_high_is_warning() -> None:
    """The portal: "Hodnota je nezvykle vysoká", saving is still possible."""
    result = reading.check({"vt": "123458"}, ["vt"], PREV, {"vt": 5.0}, TODAY, TODAY)
    assert _codes(result) == ([], ["high"])
    assert result.ok
    # like the portal: no warning without the usual consumption or on the same day
    assert _codes(reading.check({"vt": "123458"}, ["vt"], PREV, {}, TODAY, TODAY)) == ([], [])
    same_day = reading.check({"vt": "123458"}, ["vt"], PREV, {"vt": 5.0}, PREV["vt"].day, TODAY)
    assert _codes(same_day) == ([], [])


def test_plausible_value_and_delta() -> None:
    result = reading.check(
        {"vt": "12950"}, ["vt"], PREV, {"vt": 10.0}, TODAY, TODAY, "deníček", "diary"
    )
    assert _codes(result) == ([], [])
    assert result.delta == {"vt": {"kwh": 68, "days": 5, "per_day": 13.6}}
    # portal rule: previous + 10 kWh/day x 5 days x 1.5 = 12957
    assert reading.check({"vt": "12957"}, ["vt"], PREV, {"vt": 10.0}, TODAY, TODAY).ok
    over = reading.check({"vt": "12958"}, ["vt"], PREV, {"vt": 10.0}, TODAY, TODAY)
    assert _codes(over) == ([], ["high"]) and over.warnings[0].params == {"limit": 12957}


def test_form_errors() -> None:
    prev = {**PREV, "nt": reading.Previous(date(2026, 11, 16), 100)}
    result = reading.check(
        {"vt": "", "nt": "1.5"}, ["vt", "nt"], prev, {}, date(2026, 11, 22), TODAY, "x" * 161, "x"
    )
    assert sorted(_codes(result)[0]) == sorted(
        ["type", "date_future", "note_long", "required", "integer"]
    )
    before = reading.check({"vt": "12900"}, ["vt"], PREV, {}, date(2026, 11, 10), TODAY)
    assert _codes(before) == (["date_before"], [])
    assert _codes(reading.check({"vt": "-1"}, ["vt"], {}, {}, TODAY, TODAY)) == (["negative"], [])
    assert _codes(reading.check({"vt": "5"}, ["vt"], {}, {}, None, TODAY)) == (["required"], [])
    # no previous reading: nothing to compare with
    assert reading.check({"vt": "5"}, ["vt"], {}, {}, TODAY, TODAY).ok


def test_daily_usage() -> None:
    points = [(date(2025, 11, 1), 10900.0), (date(2025, 11, 25), 11000.0),
              (date(2026, 7, 5), 12169.0), (date(2026, 11, 16), 12882)]  # fmt: skip
    # readings of the last 365 days only
    assert reading.daily_usage(points, TODAY) == pytest.approx(1882 / 356)
    assert reading.daily_usage(points[:1], TODAY) is None
    assert reading.daily_usage([(date(2026, 1, 1), 5.0), (date(2026, 2, 1), 4.0)], TODAY) is None


def test_register_readings() -> None:
    single, device = api.parse_register_readings(load("meter_readings.json"), date(2026, 3, 1))
    assert device == "1000000001" and list(single) == ["vt"]  # NT reads 0: single tariff
    assert single["vt"][-1] == (date(2026, 2, 17), 11598.0)
    dual, device = api.parse_register_readings(load("pv_meter_readings.json"), date(2026, 3, 1))
    assert device == "70000002" and sorted(dual) == ["nt", "vt"]
    assert api.parse_register_readings(None, TODAY) == ({}, None)  # type: ignore[arg-type]


def test_replaced_meter_is_ignored() -> None:
    def row(day: str, value: float, device: str) -> dict[str, Any]:
        return {
            "meterReadingRegisterDate": day,
            "meterReadingDeviceNumber": device,
            "meterReadingType": {"entryId": "DISTR", "value": "Odečet distributorem"},
            "meterReadingTariff": {"entryId": "VT", "value": "Registr - VT"},
            "meterReadingValue": value,
        }

    rows = [
        row("2022-01-01", 9000, "0001"),
        row("2023-08-31", 1, "0002"),
        row("2026-10-31", 1673, "0002"),
    ]
    regs, device = api.parse_register_readings(rows, TODAY)
    assert device == "2" and regs["vt"] == [(date(2023, 8, 31), 1.0), (date(2026, 10, 31), 1673.0)]


def test_build_request() -> None:
    body = reading.build_request("859100000000000001", "1000000001", "diary", TODAY, 12950,
                                 None, "pozn")  # fmt: skip
    assert body["selfMeterReadingHighTariff"]["meterReadingValue"] == 12950
    assert body["selfMeterReadingHighTariff"]["meterReadingTariff"] == {"entryId": "highTariff"}
    assert body["selfMeterReadingLowTariff"]["meterReadingValue"] == 0  # single tariff
    assert body["selfMeterReadingReason"] == {"entryId": "08"}
    assert body["meterReadingRegisterDate"] == "2026-11-21"
    assert body["meterReadingDeviceNumber"] == "1000000001"
    assert body["selfMeterReadingDescription"] == "pozn" and body["checkSnaps"] is True
    assert body["selfMeterReadingGuidIsu"] == ""
    dual = reading.build_request("859100000000000001", "1", "control", TODAY, 1, 2, "")
    assert dual["selfMeterReadingLowTariff"]["meterReadingValue"] == 2
    assert dual["selfMeterReadingReason"] == {"entryId": "02"}


def test_consumption_vals_and_limits() -> None:
    data = {
        "lastConsVT": 1825, "lastConsNT": 0, "LastBillPeriod": 365,
        "Limits": [{"smrType": "02", "period": "YEAR", "limitActual": 1, "limitMax": 3},
                   {"smrType": "02", "period": "DAY", "limitActual": 0, "limitMax": 1}],
    }  # fmt: skip
    usage, remaining = reading.parse_consumption_vals(data)
    assert usage == {"vt": 5.0, "nt": 0.0} and remaining == {"02": 2}
    assert reading.parse_consumption_vals(None) == ({}, {})
    assert reading.parse_consumption_vals({"lastConsVT": 5, "LastBillPeriod": 0}) == ({}, {})
    out = reading.check({"vt": "13000"}, ["vt"], PREV, {}, TODAY, TODAY, "", "control",
                        remaining={"02": 0})  # fmt: skip
    assert _codes(out) == (["no_remaining"], [])
    # the limit only applies to control readings
    assert reading.check({"vt": "13000"}, ["vt"], PREV, {}, TODAY, TODAY, "", "diary",
                         remaining={"02": 0}).ok  # fmt: skip


def test_one_reading_per_day() -> None:
    rows = [
        {"meterReadingRequestRegisterDate": "2026-11-21", "selfMeterReadingReasonId": "02",
         "selfMeterReadingStatusId": "1"},
        {"meterReadingRequestRegisterDate": "2026-11-20", "selfMeterReadingReasonId": "02",
         "selfMeterReadingStatusId": "4"},  # rejected
        {"meterReadingRequestRegisterDate": "2026-11-19", "selfMeterReadingReasonId": "08",
         "selfMeterReadingStatusId": "0"},  # diary readings are not limited
    ]  # fmt: skip
    taken = reading.taken_days(rows)
    assert taken == {TODAY}
    out = reading.check({"vt": "13000"}, ["vt"], PREV, {}, TODAY, TODAY, "", "info", taken)
    assert _codes(out) == (["duplicate_day"], [])
    assert reading.check({"vt": "13000"}, ["vt"], PREV, {}, TODAY, TODAY, "", "diary", taken).ok
    too_long = reading.check({"vt": "1234567890"}, ["vt"], {}, {}, TODAY, TODAY)
    assert _codes(too_long) == (["too_long"], [])


async def _setup(hass: HomeAssistant, **options: Any) -> str:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=USERNAME,
        data={CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD},
        options=options,
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry.entry_id


async def test_websocket_form_check_submit(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    mock_client: AsyncMock,
) -> None:
    mock_client.get_register_readings.return_value = api.parse_register_readings(
        load("meter_readings.json"), date(2026, 3, 1)
    )
    entry_id = await _setup(hass)
    ws = await hass_ws_client(hass)
    await ws.send_json({"id": 1, "type": f"{DOMAIN}/reading_form"})
    form = (await ws.receive_json())["result"]
    today = form["today"]
    assert today == dt_util.now().date().isoformat()
    assert form["types"] == ["control", "diary", "extraordinary", "info"]
    (point,) = form["points"]
    assert point["entry_id"] == entry_id and not point["dual_tariff"]
    assert point["previous"] == {"date": "2026-02-17", "vt": 11598.0}
    assert point["device"] == "1000000001"
    base = {"entry_id": entry_id, "ean": point["ean"], "reading_type": "diary", "date": today}

    await ws.send_json({"id": 2, "type": f"{DOMAIN}/reading_check", **base, "vt": "11000"})
    check = (await ws.receive_json())["result"]
    assert not check["ok"] and check["errors"][0]["code"] == "lower"

    await ws.send_json({"id": 3, "type": f"{DOMAIN}/reading_submit", **base, "vt": "11000"})
    assert (await ws.receive_json())["error"]["code"] == "invalid"

    await ws.send_json({"id": 5, "type": f"{DOMAIN}/reading_check", **base, "ean": "nope"})
    assert (await ws.receive_json())["error"]["code"] == "not_found"


async def test_websocket_submit(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    mock_client: AsyncMock,
) -> None:
    mock_client.get_register_readings.return_value = api.parse_register_readings(
        load("meter_readings.json"), date(2026, 3, 1)
    )
    mock_client.submit_meter_reading.return_value = {
        "activityId": "A1",
        "meterReadingImplausible": False,
        "isAttachmentNeeded": True,
    }
    entry_id = await _setup(hass)
    ws = await hass_ws_client(hass)
    await ws.send_json({"id": 1, "type": f"{DOMAIN}/reading_form"})
    point = (await ws.receive_json())["result"]["points"][0]
    await ws.send_json(
        {"id": 2, "type": f"{DOMAIN}/reading_submit", "entry_id": entry_id, "ean": point["ean"],
         "reading_type": "control", "date": dt_util.now().date().isoformat(), "vt": 11700, "note": ""}
    )  # fmt: skip
    result = (await ws.receive_json())["result"]
    assert result["sent"] is True and result["activity_id"] == "A1"
    assert result["attachment_needed"] is True and result["implausible"] is False
    body = mock_client.submit_meter_reading.await_args.args[0]
    assert body["selfMeterReadingReason"] == {"entryId": "02"}
    assert body["selfMeterReadingHighTariff"]["meterReadingValue"] == 11700
    assert body["meterReadingDeviceNumber"] == "1000000001"


def test_offered_types_and_date_range() -> None:
    rows = [
        {"meterReadingReasonId": "08", "meterReadingReasonEnabled": True},
        {"meterReadingReasonId": "02", "meterReadingReasonEnabled": True},
        {"meterReadingReasonId": "14", "meterReadingReasonEnabled": False},
    ]
    assert reading.parse_types(rows) == ["control", "diary"]  # portal order
    assert reading.parse_types(None) is None
    config = {"meterReadingMinDate": "2026-10-22", "meterReadingMaxDate": "2026-11-21"}
    span = reading.parse_date_range(config)
    assert span == (date(2026, 10, 22), TODAY)
    assert reading.parse_date_range({"meterReadingMinDate": "x"}) is None
    out = reading.check({"vt": "13000"}, ["vt"], {}, {}, date(2026, 10, 21), TODAY,
                        date_range=span)  # fmt: skip
    assert _codes(out) == (["date_range"], [])
    assert out.errors[0].params == {"min": "2026-10-22", "max": "2026-11-21"}
    assert reading.check({"vt": "13000"}, ["vt"], {}, {}, TODAY, TODAY, date_range=span).ok
