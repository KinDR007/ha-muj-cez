"""Compare portal (ČEZ) consumption with a Home Assistant energy sensor.

Pure functions without Home Assistant imports, so they can be developed and tested
offline. `daily` maps a local calendar day to kWh imported that day (HA long-term
statistics "change" with period "day").

Day convention: a meter reading dated D is the meter state at the end of day D, so
the interval between readings D1 and D2 covers days D1+1 .. D2 (same as billing
periods, which start the day after the closing reading).
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from .api import BillingPeriod, MeterReadingPoint, MonthValue, SupplyPointData

DailyEnergy = dict[date, float]


def _days(start: date, end: date) -> list[date]:
    """Inclusive range of days."""
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


def energy_between(daily: DailyEnergy, start: date, end: date) -> tuple[float | None, bool]:
    """kWh over days start..end (inclusive) and whether every day has data.

    Returns (None, False) when no day of the range has data.
    """
    if end < start:
        return None, False
    days = _days(start, end)
    present = [daily[d] for d in days if d in daily]
    if not present:
        return None, False
    return round(sum(present), 2), len(present) == len(days)


def diff_pct(ha: float | None, cez: float | None) -> float | None:
    if ha is None or not cez:
        return None
    return round((ha - cez) / cez * 100, 1)


def _iso(day: date | None) -> str | None:
    return day.isoformat() if day else None


def period_label(start: date | None, end: date | None) -> str | None:
    if not start or not end:
        return None
    return f"{start.year}/{str(end.year)[-2:]}" if end.year != start.year else str(start.year)


def compare_readings(readings: list[MeterReadingPoint], daily: DailyEnergy) -> list[dict[str, Any]]:
    """Meter delta between consecutive readings vs HA energy over the same days.

    Only intervals fully covered by HA data, on the same meter and with a positive
    delta are returned.
    """
    result = []
    for prev, cur in zip(readings, readings[1:], strict=False):
        if prev.device and cur.device and prev.device != cur.device:
            continue
        meter = round(cur.value - prev.value, 2)
        if meter <= 0:
            continue
        ha, complete = energy_between(
            daily, prev.reading_date + timedelta(days=1), cur.reading_date
        )
        if ha is None or not complete:
            continue
        result.append(
            {
                "from": _iso(prev.reading_date),
                "to": _iso(cur.reading_date),
                "cez_kwh": meter,
                "ha_kwh": ha,
                "diff_kwh": round(ha - meter, 2),
                "diff_pct": diff_pct(ha, meter),
                "reading_type": cur.reading_type,
            }
        )
    return result


def _month_price(month: MonthValue) -> float | None:
    if month.cost is None or not month.consumption_kwh:
        return None
    return month.cost / month.consumption_kwh


def compare_months(
    months: list[MonthValue], daily: DailyEnergy, today: date
) -> list[dict[str, Any]]:
    """Current period by month: portal split vs HA measured (up to yesterday).

    ha_cost uses the portal price of the same month (cost incl. fixed fees / kWh).
    """
    yesterday = today - timedelta(days=1)
    result = []
    for m in months:
        ha = None
        complete = False
        if m.date_from <= yesterday:
            ha, complete = energy_between(daily, m.date_from, min(m.date_to, yesterday))
        price = _month_price(m)
        result.append(
            {
                "month": m.month,
                "from": _iso(m.date_from),
                "to": _iso(m.date_to),
                "cez_kwh": m.consumption_kwh,
                "cez_cost": m.cost,
                "estimated": m.estimated,
                "ha_kwh": ha,
                "ha_cost": round(ha * price, 2) if ha is not None and price else None,
                "ha_partial": ha is not None and (not complete or m.date_to > yesterday),
            }
        )
    return result


def compare_periods(
    periods: list[BillingPeriod],
    months: list[MonthValue],
    daily: DailyEnergy,
    today: date,
) -> list[dict[str, Any]]:
    """Billing periods: portal kWh/Kč vs HA.

    Closed periods: HA energy over the whole period when fully covered.
    Current (predicted) period: HA measured so far + portal estimate of remaining days,
    so the prediction is anchored to what HA actually measured.
    """
    yesterday = today - timedelta(days=1)
    result = []
    for p in periods:
        item: dict[str, Any] = {
            "label": period_label(p.date_from, p.date_to),
            "from": _iso(p.date_from),
            "to": _iso(p.date_to),
            "predicted": p.predicted,
            "cez_kwh": p.consumption_kwh,
            "cez_cost": p.cost,
            "ha_kwh": None,
            "ha_cost": None,
            "ha_coverage": "none",
            "diff_pct": None,
        }
        if p.date_from and p.date_to:
            end = min(p.date_to, yesterday) if p.predicted else p.date_to
            ha, complete = energy_between(daily, p.date_from, end)
            if ha is not None:
                item["ha_coverage"] = "full" if complete else "partial"
                if p.predicted:
                    remaining = _remaining_estimate(months, today)
                    item["ha_measured_kwh"] = ha
                    item["ha_kwh"] = round(ha + remaining, 2)
                else:
                    item["ha_kwh"] = ha
                if complete:
                    item["diff_pct"] = diff_pct(item["ha_kwh"], p.consumption_kwh)
                    price = p.cost / p.consumption_kwh if p.cost and p.consumption_kwh else None
                    if price:
                        item["ha_cost"] = round(item["ha_kwh"] * price, 2)
        result.append(item)
    return result


def _remaining_estimate(months: list[MonthValue], today: date) -> float:
    """Portal estimate for days from today to period end (pro rata within a month)."""
    total = 0.0
    for m in months:
        if m.date_to < today or m.consumption_kwh is None:
            continue
        days = (m.date_to - m.date_from).days + 1
        remaining = (m.date_to - max(m.date_from, today)).days + 1
        total += m.consumption_kwh * remaining / days
    return round(total, 2)


def billing_months(start: date, end: date) -> list[tuple[date, date]]:
    """Split a period into month slices like the portal does (first/last may be partial)."""
    slices = []
    cur = start
    while cur <= end:
        next_month = (cur.replace(day=1) + timedelta(days=32)).replace(day=1)
        slices.append((cur, min(end, next_month - timedelta(days=1))))
        cur = next_month
    return slices


def ha_period_months(
    daily: DailyEnergy, periods: list[BillingPeriod], today: date
) -> list[dict[str, Any]]:
    """HA energy per billing-period month slice, for year-over-year comparison.

    index = month number within the period (0 = first slice). Only slices with
    HA data are returned; `complete` tells whether every day of the slice has data.
    """
    yesterday = today - timedelta(days=1)
    result = []
    for p in periods:
        if not p.date_from or not p.date_to:
            continue
        for index, (start, end) in enumerate(billing_months(p.date_from, p.date_to)):
            if start > yesterday:
                break
            kwh, complete = energy_between(daily, start, min(end, yesterday))
            if kwh is None:
                continue
            result.append(
                {
                    "period": period_label(p.date_from, p.date_to),
                    "index": index,
                    "month": start.strftime("%Y-%m"),
                    "kwh": kwh,
                    "complete": complete and end <= yesterday,
                }
            )
    return result


def build_comparison(
    spd: SupplyPointData, daily: DailyEnergy | None, today: date
) -> dict[str, Any]:
    """All comparison data for one supply point. Without HA data only portal values."""
    daily = daily or {}
    sim = spd.simulation
    months = spd.months or []
    periods = spd.periods or []
    current: dict[str, Any] = {}
    if sim and sim.period_from and sim.measured_until:
        ha, complete = energy_between(daily, sim.period_from, sim.measured_until)
        current = {
            "from": _iso(sim.period_from),
            "to": _iso(sim.period_to),
            "measured_until": _iso(sim.measured_until),
            "cez_measured_kwh": sim.consumption_measured_kwh,
            "ha_measured_kwh": ha if complete else None,
            "diff_pct": diff_pct(ha, sim.consumption_measured_kwh) if complete else None,
        }
    return {
        "current": current,
        "months": compare_months(months, daily, today),
        "periods": compare_periods(periods, months, daily, today),
        "readings": compare_readings(spd.readings or [], daily),
        "ha_months": ha_period_months(daily, periods, today),
        "ha_first_day": _iso(min(daily)) if daily else None,
    }
