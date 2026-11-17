"""Comparison of portal values with HA daily energy (pure functions)."""

from datetime import date, timedelta

from custom_components.muj_cez import compare
from custom_components.muj_cez.api import MeterReadingPoint

from .conftest import TODAY, UID, sample_data


def _daily(start: date, end: date, kwh: float = 4.0) -> dict[date, float]:
    return {start + timedelta(days=i): kwh for i in range((end - start).days + 1)}


def test_energy_between() -> None:
    daily = _daily(date(2026, 1, 1), date(2026, 1, 10))
    assert compare.energy_between(daily, date(2026, 1, 1), date(2026, 1, 10)) == (40.0, True)
    assert compare.energy_between(daily, date(2025, 12, 30), date(2026, 1, 2)) == (8.0, False)
    assert compare.energy_between(daily, date(2027, 1, 1), date(2027, 1, 2)) == (None, False)
    assert compare.energy_between(daily, date(2026, 1, 5), date(2026, 1, 4)) == (None, False)


def test_readings_interval_days() -> None:
    """Reading on D = state at end of D: interval covers D1+1 .. D2."""
    daily = _daily(date(2026, 1, 1), date(2026, 1, 31), kwh=1.0)
    daily[date(2026, 1, 10)] = 100.0  # day of first reading: excluded
    readings = [
        MeterReadingPoint(date(2026, 1, 10), 1000.0, "Odečet distributorem", "1"),
        MeterReadingPoint(date(2026, 1, 20), 1011.0, "Samoodečet", "1"),
        MeterReadingPoint(date(2026, 1, 25), 5.0, "Odečet distributorem", "2"),  # new meter
        MeterReadingPoint(date(2026, 1, 30), 10.0, "Odečet distributorem", "2"),
        MeterReadingPoint(date(2026, 2, 28), 20.0, "Odečet distributorem", "2"),  # no HA data
    ]
    result = compare.compare_readings(readings, daily)
    assert [(r["from"], r["to"]) for r in result] == [
        ("2026-01-10", "2026-01-20"),
        ("2026-01-25", "2026-01-30"),
    ]
    assert result[0]["cez_kwh"] == 11
    assert result[0]["ha_kwh"] == 10
    assert result[0]["diff_pct"] == -9.1
    assert result[1]["ha_kwh"] == 5


def test_build_comparison_with_ha() -> None:
    spd = sample_data().supply_points[UID]
    daily = _daily(date(2025, 1, 1), TODAY - timedelta(days=1))
    c = compare.build_comparison(spd, daily, TODAY)

    closed = next(p for p in c["periods"] if p["label"] == "2025/26")
    days = (date(2026, 2, 17) - date(2025, 2, 26)).days + 1
    assert closed["ha_coverage"] == "full"
    assert closed["ha_kwh"] == 4 * days
    assert closed["diff_pct"] == round((4 * days - 1163) / 1163 * 100, 1)
    assert closed["ha_cost"] == round(4 * days * 10764.77 / 1163, 2)

    partial = next(p for p in c["periods"] if p["label"] == "2024/25")
    assert partial["ha_coverage"] == "partial"
    assert partial["diff_pct"] is None
    assert next(p for p in c["periods"] if p["label"] == "2023/24")["ha_coverage"] == "none"

    current = c["periods"][-1]
    assert current["predicted"]
    measured = 4 * ((TODAY - date(2026, 2, 18)).days)
    assert current["ha_measured_kwh"] == measured
    assert current["ha_kwh"] > measured  # plus portal estimate for remaining days

    march = next(m for m in c["months"] if m["month"] == "2026-03")
    assert march == {
        "month": "2026-03",
        "from": "2026-03-01",
        "to": "2026-03-31",
        "cez_kwh": 144.0,
        "cez_cost": 1120.58,
        "estimated": False,
        "ha_kwh": 124.0,
        "ha_cost": round(124 * 1120.58 / 144, 2),
        "ha_partial": False,
    }
    november = next(m for m in c["months"] if m["month"] == "2026-11")
    assert november["estimated"] and november["ha_partial"]
    assert november["ha_kwh"] == 4 * 15
    assert next(m for m in c["months"] if m["month"] == "2026-12")["ha_kwh"] is None

    assert c["current"]["measured_until"] == "2026-11-16"
    assert c["current"]["ha_measured_kwh"] is None  # today (16th) not in daily data
    assert c["readings"]
    first = c["ha_months"][0]
    assert first == {
        "period": "2024/25",
        "index": 11,
        "month": "2025-01",
        "kwh": 124.0,
        "complete": True,
    }
    feb_split = [m for m in c["ha_months"] if m["month"] == "2026-02"]
    # February 2026 belongs to two periods: 1.-17. (2025/26) and 18.-28. (2026/27)
    assert [(m["period"], m["kwh"]) for m in feb_split] == [("2025/26", 68.0), ("2026/27", 44.0)]
    assert c["ha_months"][-1]["complete"] is False  # current month
    assert c["ha_first_day"] == "2025-01-01"


def test_build_comparison_without_ha() -> None:
    spd = sample_data().supply_points[UID]
    c = compare.build_comparison(spd, None, TODAY)
    assert c["current"]["diff_pct"] is None
    assert all(p["ha_kwh"] is None for p in c["periods"])
    assert len(c["months"]) == 13
    assert c["months"][0]["cez_kwh"] == 54.0
    assert c["readings"] == []
    assert c["ha_months"] == []


def test_period_label() -> None:
    assert compare.period_label(date(2025, 2, 26), date(2026, 2, 17)) == "2025/26"
    assert compare.period_label(date(2025, 1, 1), date(2025, 12, 31)) == "2025"
    assert compare.period_label(None, None) is None


def test_billing_months() -> None:
    slices = compare.billing_months(date(2026, 2, 18), date(2027, 2, 15))
    assert slices[0] == (date(2026, 2, 18), date(2026, 2, 28))
    assert slices[1] == (date(2026, 3, 1), date(2026, 3, 31))
    assert slices[-1] == (date(2027, 2, 1), date(2027, 2, 15))
    assert len(slices) == 13
