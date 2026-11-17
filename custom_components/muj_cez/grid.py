"""Smart meter (AMS) data from the portal: grid import/export and spot prices.

Pure functions without Home Assistant imports. Data come from the `/tapp/...`
endpoints which only work for supply points with interval metering; for other
accounts they return errors or empty lists and everything here yields empty results.

- grid-data (daily): import (role SPOTREBA) and export to the grid (role VYROBA).
  A request may cover at most ~45 days.
- profile-data (15 min values): import M12, export M11; at most ~31 days per request.
- spot-prices-simple (hourly, CZK/MWh): history up to yesterday; at most ~7 days.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Prague")

ROLE_IMPORT = "SPOTREBA"
ROLE_EXPORT = "VYROBA"
PROFILE_IMPORT = "M12"
PROFILE_EXPORT = "M11"

DAILY_WINDOW_DAYS = 40
PROFILE_WINDOW_DAYS = 31
SPOT_WINDOW_DAYS = 7

# Daily rows come in two copies (distribution and trade view); prefer the first known.
_DAILY_ROLE_PREFERENCE = ("ODBER-DODANE", "ODBER-OBCHOD", "DODAVKA-DODANE", "DODAVKA-OBCHOD")

DailyValues = dict[date, float]


def iso_utc(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def local_midnight(day: date) -> datetime:
    return datetime(day.year, day.month, day.day, tzinfo=TZ)


def windows(start: date, end: date, days: int) -> Iterator[tuple[date, date]]:
    """Split [start, end) into consecutive windows of at most `days` days."""
    cur = start
    while cur < end:
        nxt = min(cur + timedelta(days=days), end)
        yield cur, nxt
        cur = nxt


def _parse_dt(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _code(obj: Any) -> str | None:
    if isinstance(obj, dict):
        return obj.get("entryId") or obj.get("value")
    return obj if isinstance(obj, str) else None


def parse_availability(data: Any) -> date | None:
    """First local day with profile data (time-intervals endpoint), None when there is none."""
    starts = [
        _parse_dt(item.get("profileReadingDatetimeFrom"))
        for place in data or []
        if isinstance(place, dict)
        for item in place.get("data") or []
        if isinstance(item, dict)
    ]
    starts = [s for s in starts if s]
    return min(starts).astimezone(TZ).date() if starts else None


def parse_daily(data: Any) -> DailyValues:
    """Daily kWh by local date from a grid-data (DEN) response."""
    by_role: dict[str, DailyValues] = defaultdict(dict)
    if not isinstance(data, dict):
        return {}
    for aggregate in data.get("gridDataAggregate") or []:
        for row in (aggregate or {}).get("gridData") or []:
            start = _parse_dt(row.get("profileReadingDatetimeFrom"))
            value = row.get("profileReadingValue")
            if start is None or not isinstance(value, int | float):
                continue
            role = _code(row.get("profileReadingRole")) or ""
            by_role[role][start.astimezone(TZ).date()] = float(value)
    for role in _DAILY_ROLE_PREFERENCE:
        if role in by_role:
            return by_role[role]
    return next(iter(by_role.values()), {})


def parse_profile(data: Any) -> dict[datetime, float]:
    """Hourly kWh (UTC hour start) from a profile-data response (15 min values summed)."""
    hourly: dict[datetime, float] = defaultdict(float)
    for aggregate in data if isinstance(data, list) else []:
        for row in (aggregate or {}).get("data") or []:
            start = _parse_dt(row.get("profileReadingDatetimeFrom"))
            value = row.get("profileReadingValue")
            if start is None or not isinstance(value, int | float):
                continue
            hour = start.astimezone(UTC).replace(minute=0, second=0, microsecond=0)
            hourly[hour] += float(value)
        # Several aggregates may describe the same meter; the first one is enough.
        if hourly:
            break
    return {h: round(v, 4) for h, v in sorted(hourly.items())}


def parse_spot_prices(data: Any) -> dict[datetime, float]:
    """Hourly spot price in CZK/kWh by UTC hour start (sub-hour values are averaged)."""
    if not isinstance(data, dict):
        return {}
    unit = _code(data.get("pricelistConfigurationUnit")) or "MWH"
    divisor = 1000.0 if unit.upper() == "MWH" else 1.0
    hours: dict[datetime, list[float]] = defaultdict(list)
    for row in data.get("spotConfigurations") or []:
        start = _parse_dt(row.get("pricelistSpotConfigurationDatetimeFrom"))
        price = row.get("pricelistSpotConfigurationPriceAverage")
        if start is None or not isinstance(price, int | float):
            continue
        hours[start.astimezone(UTC).replace(minute=0, second=0, microsecond=0)].append(price)
    return {h: round(sum(v) / len(v) / divisor, 5) for h, v in sorted(hours.items())}


@dataclass
class GridMonth:
    month: str
    import_kwh: float | None
    export_kwh: float | None
    days: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "month": self.month,
            "import_kwh": self.import_kwh,
            "export_kwh": self.export_kwh,
            "days": self.days,
        }


def monthly(import_daily: DailyValues, export_daily: DailyValues) -> list[GridMonth]:
    """Monthly sums, oldest first; None when a direction has no data in the month."""
    months: dict[str, dict[str, Any]] = defaultdict(lambda: {"i": None, "e": None, "d": set()})
    for key, daily in (("i", import_daily), ("e", export_daily)):
        for day, value in daily.items():
            m = months[day.strftime("%Y-%m")]
            m[key] = (m[key] or 0.0) + value
            m["d"].add(day)
    return [
        GridMonth(
            month=k,
            import_kwh=None if v["i"] is None else round(v["i"], 2),
            export_kwh=None if v["e"] is None else round(v["e"], 2),
            days=len(v["d"]),
        )
        for k, v in sorted(months.items())
    ]


def period_sum(daily: DailyValues, start: date, end: date) -> float | None:
    values = [v for d, v in daily.items() if start <= d <= end]
    return round(sum(values), 2) if values else None


def summary(import_daily: DailyValues, export_daily: DailyValues, today: date) -> dict[str, Any]:
    """Totals for sensors: this/last month and year, last day with data."""
    month_start = today.replace(day=1)
    prev_month_end = month_start - timedelta(days=1)
    prev_month_start = prev_month_end.replace(day=1)
    year_start = today.replace(month=1, day=1)
    prev_year_start = year_start.replace(year=year_start.year - 1)
    prev_year_end = year_start - timedelta(days=1)
    result: dict[str, Any] = {}
    for key, daily in (("import", import_daily), ("export", export_daily)):
        if not daily:
            continue
        result[key] = {
            "this_month": period_sum(daily, month_start, today),
            "last_month": period_sum(daily, prev_month_start, prev_month_end),
            "this_year": period_sum(daily, year_start, today),
            "last_year": period_sum(daily, prev_year_start, prev_year_end),
            "last_day": max(daily).isoformat(),
            "last_day_kwh": daily[max(daily)],
        }
    return result


def merge_daily(cached: dict[str, float], fresh: DailyValues) -> dict[str, float]:
    """Merge fresh values into the cache (ISO date keys), fresh values win."""
    out = dict(cached)
    out.update({d.isoformat(): v for d, v in fresh.items()})
    return dict(sorted(out.items()))


def from_cache(cached: dict[str, float] | None) -> DailyValues:
    result: DailyValues = {}
    for key, value in (cached or {}).items():
        try:
            result[date.fromisoformat(key)] = float(value)
        except (TypeError, ValueError):
            continue
    return result


def compare_monthly(cez: DailyValues, ha: dict[date, float] | None) -> list[dict[str, Any]]:
    """Monthly ČEZ meter vs HA sensor over days present in both sources, oldest first."""
    if not cez or not ha:
        return []
    months: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0, 0])
    for day, value in cez.items():
        if day in ha:
            m = months[day.strftime("%Y-%m")]
            m[0] += value
            m[1] += ha[day]
            m[2] += 1
    return [
        {
            "month": k,
            "cez_kwh": round(c, 2),
            "ha_kwh": round(h, 2),
            "days": n,
            "diff_pct": round((h - c) / c * 100, 1) if c else None,
        }
        for k, (c, h, n) in sorted(months.items())
    ]


def payout_months(
    payouts: list[Any],
    export: DailyValues,
    valuation: dict[str, dict[str, float]] | None = None,
) -> list[dict[str, Any]]:
    """Payouts with exported kWh, effective price and the value at spot prices."""
    result = []
    for p in payouts:
        kwh = period_sum(export, p.date_from, p.date_to)
        spot = (valuation or {}).get(p.month) or {}
        item = {
            "month": p.month,
            "amount": p.amount,
            "export_kwh": kwh,
            "price_per_kwh": round(p.amount / kwh, 2) if p.amount is not None and kwh else None,
        }
        if spot.get("kwh"):
            item["spot_value"] = round(spot["value"], 2)
            item["spot_price_per_kwh"] = round(spot["value"] / spot["kwh"], 2)
        result.append(item)
    return result
