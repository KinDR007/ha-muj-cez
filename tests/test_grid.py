"""Production supply points, dual tariff readings and smart meter data (PV accounts)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from custom_components.muj_cez import api, grid

from .conftest import TODAY, load

PV_UID = "0000333333330004444444859100000000000003"
SV_UID = "0000555555550004444444859100000000000005  SV"


def test_production_supply_point() -> None:
    cons, prod = api.parse_supply_points(load("pv_supply_points.json"))
    assert not cons.production
    assert cons.ean == "859100000000000003"
    assert cons.name == "Testovací 123, Praha"
    assert prod.production
    assert prod.uid == SV_UID
    assert prod.ean == "859100000000000005"
    assert prod.code == "859100000000000005  SV"
    assert prod.name == "Testovací 123, Praha výroba"
    assert cons.place_id == prod.place_id == "0004444444"


def test_production_detected_by_code_suffix() -> None:
    [sp] = api.parse_supply_points(
        [{"supplyPointUniqueId": "x", "supplyPointCode": "859100000000000009  SV"}]
    )
    assert sp.production
    assert sp.ean == "859100000000000009"


def test_payouts() -> None:
    payouts = api.parse_payouts(load("pv_payouts.json"))
    assert [p.month for p in payouts] == ["2026-07", "2026-08", "2026-09", "2026-10"]
    assert payouts[-1].amount == 73.13
    assert api.parse_payouts(None) == []


def test_dual_tariff_reading_history() -> None:
    """VT + NT summed; simulated readings and incomplete days ignored."""
    readings = api.parse_meter_reading_history(load("pv_meter_readings.json"), TODAY)
    by_day = {r.reading_date: r for r in readings}
    assert by_day[date(2026, 9, 30)].value == 1643 + 12904
    assert by_day[date(2026, 10, 31)].value == 1673 + 13160
    assert by_day[date(2026, 10, 31)].device == "70000001"
    assert date(2026, 12, 31) not in by_day
    # Self reading of another meter with both registers.
    assert by_day[date(2022, 3, 29)].value == 269 + 336


def test_reading_history_skips_day_without_all_registers() -> None:
    def row(day: str, tariff: str, value: float) -> dict[str, Any]:
        return {
            "meterReadingRegisterDate": day,
            "meterReadingDeviceNumber": "1",
            "meterReadingType": {"value": "Odečet distributorem"},
            "meterReadingTariff": {"value": f"Registr - {tariff}"},
            "meterReadingValue": value,
        }

    rows = [row("2026-01-01", "VT", 10), row("2026-01-01", "NT", 20), row("2026-02-01", "VT", 15)]
    readings = api.parse_meter_reading_history(rows, TODAY)
    assert [(r.reading_date, r.value) for r in readings] == [(date(2026, 1, 1), 30)]


def test_parse_daily_prefers_distribution_copy() -> None:
    imp = grid.parse_daily(load("pv_grid_import.json"))
    exp = grid.parse_daily(load("pv_grid_export.json"))
    assert min(imp) == date(2026, 10, 29)
    assert max(imp) == date(2026, 11, 3)
    assert len(imp) == 6
    assert set(exp) == set(imp)
    assert all(v >= 0 for v in exp.values())
    assert grid.parse_daily(None) == {}
    assert grid.parse_daily({"gridDataAggregate": [{"gridData": [{"x": 1}]}]}) == {}


def test_availability() -> None:
    assert grid.parse_availability(load("pv_time_intervals.json")) is not None
    assert grid.parse_availability([]) is None
    assert grid.parse_availability(None) is None


def test_profile_hourly() -> None:
    hourly = grid.parse_profile(load("pv_profile_export.json"))
    # 15 min values summed into UTC hours (11:00 and 12:00 local = 10:00 and 11:00 UTC).
    assert list(hourly) == [
        datetime(2026, 11, 1, 10, tzinfo=UTC),
        datetime(2026, 11, 1, 11, tzinfo=UTC),
    ]
    assert grid.parse_profile(None) == {}


def test_spot_prices() -> None:
    prices = grid.parse_spot_prices(load("spot_prices.json"))
    assert len(prices) == 24
    first = next(iter(prices))
    assert first == datetime(2024, 12, 31, 23, tzinfo=UTC)
    assert 0.1 < prices[first] < 10  # CZK/kWh
    quarter = {
        "pricelistConfigurationUnit": {"entryId": "MWH"},
        "spotConfigurations": [
            {
                "pricelistSpotConfigurationDatetimeFrom": f"2026-11-10T10:{m:02d}:00Z",
                "pricelistSpotConfigurationPriceAverage": price,
            }
            for m, price in ((0, 1000), (15, 2000), (30, 3000), (45, 4000))
        ],
    }
    assert grid.parse_spot_prices(quarter) == {datetime(2026, 11, 10, 10, tzinfo=UTC): 2.5}
    assert grid.parse_spot_prices(None) == {}


def test_windows() -> None:
    ws = list(grid.windows(date(2026, 1, 1), date(2026, 3, 1), 31))
    assert ws == [(date(2026, 1, 1), date(2026, 2, 1)), (date(2026, 2, 1), date(2026, 3, 1))]
    assert list(grid.windows(date(2026, 1, 1), date(2026, 1, 1), 31)) == []


def test_monthly_summary_and_comparison() -> None:
    imp = {date(2026, 10, 31): 10.0, date(2026, 11, 1): 5.0, date(2026, 11, 2): 7.0}
    exp = {date(2026, 11, 1): 2.0}
    months = grid.monthly(imp, exp)
    assert [m.as_dict() for m in months] == [
        {"month": "2026-10", "import_kwh": 10.0, "export_kwh": None, "days": 1},
        {"month": "2026-11", "import_kwh": 12.0, "export_kwh": 2.0, "days": 2},
    ]
    s = grid.summary(imp, exp, date(2026, 11, 16))
    assert s["import"]["this_month"] == 12.0
    assert s["import"]["last_month"] == 10.0
    assert s["import"]["this_year"] == 22.0
    assert s["import"]["last_year"] is None
    assert s["import"]["last_day"] == "2026-11-02"
    assert s["export"]["last_day_kwh"] == 2.0
    assert grid.summary({}, {}, TODAY) == {}
    ha = {date(2026, 11, 1): 5.5, date(2026, 11, 2): 6.5, date(2026, 11, 3): 1.0}
    assert grid.compare_monthly(imp, ha) == [
        {"month": "2026-11", "cez_kwh": 12.0, "ha_kwh": 12.0, "days": 2, "diff_pct": 0.0}
    ]
    assert grid.compare_monthly(imp, None) == []


def test_payout_months() -> None:
    payouts = api.parse_payouts(load("pv_payouts.json"))
    export = {date(2026, 10, 1): 10.0, date(2026, 10, 2): 12.13}
    result = grid.payout_months(payouts, export)
    assert result[-1] == {
        "month": "2026-10",
        "amount": 73.13,
        "export_kwh": 22.13,
        "price_per_kwh": 3.3,
    }
    assert result[0]["export_kwh"] is None
    assert result[0]["price_per_kwh"] is None


def test_cache_roundtrip() -> None:
    cached = grid.merge_daily({"2026-11-01": 1.0}, {date(2026, 11, 1): 2.0, date(2026, 11, 2): 3.0})
    assert cached == {"2026-11-01": 2.0, "2026-11-02": 3.0}
    assert grid.from_cache({**cached, "bad": "x"}) == {
        date(2026, 11, 1): 2.0,
        date(2026, 11, 2): 3.0,
    }


class FakeClient(api.CezClient):
    """Serves _get from a callable and records requested paths."""

    def __init__(self, handler: Any) -> None:
        super().__init__(None, "u", "p")  # type: ignore[arg-type]
        self.handler = handler
        self.calls: list[tuple[str, dict[str, str] | None]] = []

    async def _get(self, path: str, params: dict[str, str] | None = None) -> Any:
        self.calls.append((path, params))
        return self.handler(path, params or {})


def _pv_handler(path: str, params: dict[str, str]) -> Any:
    if path.endswith("time-intervals"):
        return load("pv_time_intervals.json")
    if path.endswith("grid-data"):
        name = (
            "pv_grid_import.json"
            if params["profileReadingRoleId"] == "SPOTREBA"
            else "pv_grid_export.json"
        )
        return load(name)
    raise api.CezConnectionError(f"GET {path}: HTTP 404")


async def test_grid_cache_backfill_and_incremental() -> None:
    sp = api.parse_supply_points(load("pv_supply_points.json"))[0]
    client = FakeClient(_pv_handler)
    cache = await client.update_grid_cache(sp, {}, date(2026, 11, 3))
    assert cache["checked"] == "2026-11-03"
    assert cache["import_from"] and cache["export_from"]
    assert max(cache["import"]) == "2026-11-02"
    first_run = len(client.calls)
    assert first_run > 4  # availability + windows from the first day
    client.calls.clear()
    await client.update_grid_cache(sp, cache, date(2026, 11, 4))
    # Availability not re-checked, one window per direction from last day - 3 days.
    assert [p for p, _ in client.calls] == ["/tapp/metering/grid-data"] * 2
    assert client.calls[0][1]["profileReadingDatetimeFrom"].startswith("2026-10-29")


async def test_grid_cache_without_smart_meter() -> None:
    sp = api.parse_supply_points(load("supply_points.json"))[0]

    def handler(path: str, params: dict[str, str]) -> Any:
        if path.endswith("time-intervals"):
            return []
        raise AssertionError("no data requests expected")

    client = FakeClient(handler)
    cache = await client.update_grid_cache(sp, {}, TODAY)
    assert cache == {"checked": TODAY.isoformat(), "import_from": None, "export_from": None}
    # Errors (endpoint missing for the account) are tolerated as well.
    client = FakeClient(lambda p, q: (_ for _ in ()).throw(api.CezConnectionError("HTTP 404")))
    cache = await client.update_grid_cache(sp, {}, TODAY)
    assert cache["import_from"] is None


async def test_spot_prices_skip_missing_and_foreign_days() -> None:
    def handler(path: str, params: dict[str, str]) -> Any:
        if params["pricelistSpotConfigurationDatetimeFrom"].startswith("2024-12-31"):
            return load("spot_prices.json")
        raise api.CezConnectionError("HTTP 404")

    client = FakeClient(handler)
    prices = await client.get_spot_prices(date(2025, 1, 1), date(2025, 1, 10))
    assert len(prices) == 24
    # Answer outside the requested window is dropped.
    client = FakeClient(lambda p, q: load("spot_prices.json"))
    assert await client.get_spot_prices(date(2025, 3, 1), date(2025, 3, 2)) == {}


async def test_fetch_all_production_point() -> None:
    def handler(path: str, params: dict[str, str]) -> Any:
        if path == "/supply-points/RetrieveSupplyPoints":
            return load("pv_supply_points.json")
        if path.startswith(f"/supply-points/{SV_UID}/ReadConsumptionHistory"):
            return load("pv_payouts.json")
        raise api.CezConnectionError(f"GET {path}: HTTP 404")

    client = FakeClient(handler)
    data = await client.fetch_all(TODAY)
    prod = data.supply_points[SV_UID]
    assert prod.payouts and prod.payouts[-1].amount == 73.13
    assert prod.simulation is None and prod.periods is None
    requested = [p for p, _ in client.calls]
    assert not any(
        SV_UID in p and ("ReadAdvancePlan" in p or "advance-payments" in p) for p in requested
    )
    assert not any(p.startswith("/simulations/invoices/859100000000000005") for p in requested)
    assert PV_UID in data.supply_points
