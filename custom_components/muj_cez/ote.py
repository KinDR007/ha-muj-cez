"""Day-ahead spot prices from OTE (public data) converted to CZK with ČNB rates.

The ČEZ portal stopped publishing spot prices in October 2025 (15 minute market).
OTE publishes the day-ahead market results for every delivery day in EUR/MWh:
hourly until 30 September 2025, then 15 minute prices plus a 60 minute index.
EUR is converted with the ČNB rate valid for the delivery day (latest rate on or
before it). No personal data are sent anywhere, only dates.
"""

from __future__ import annotations

import bisect
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from typing import Any

import aiohttp

from .grid import local_midnight

OTE_URL = "https://www.ote-cr.cz/pw-data/chart-data/01"
CNB_URL = (
    "https://www.cnb.cz/cs/financni-trhy/devizovy-trh/kurzy-devizoveho-trhu/"
    "kurzy-devizoveho-trhu/rok.txt"
)
TIMEOUT = aiohttp.ClientTimeout(total=30)


class OteError(Exception):
    """OTE or ČNB data could not be loaded."""


def _price_series(data: Any) -> list[dict[str, Any]] | None:
    """Points of the price line: 60 min index when present, else the only price line."""
    lines = ((data or {}).get("data") or {}).get("dataLine") or []
    prices = [line for line in lines if "cena" in str(line.get("title", "")).lower()]
    for line in prices:
        if "60min" in str(line.get("title", "")).lower():
            return line.get("point") or []
    plain = [line for line in prices if "15min" not in str(line.get("title", "")).lower()]
    chosen = plain or prices
    return (chosen[0].get("point") or []) if chosen else None


def parse_ote_day(data: Any, day: date) -> dict[datetime, float]:
    """Hourly price in EUR/MWh by UTC hour start for one delivery day.

    Points are slots of equal length covering the local day (24/23/25 hourly
    points or 96/92/100 quarter hours); several slots in one hour are averaged.
    """
    points = _price_series(data)
    if not points:
        return {}
    start = local_midnight(day).astimezone(UTC)
    length = (local_midnight(day + timedelta(days=1)).astimezone(UTC) - start) / len(points)
    hours: dict[datetime, list[float]] = defaultdict(list)
    for point in points:
        try:
            slot = int(point["x"]) - 1
            value = float(point["y"])
        except (KeyError, TypeError, ValueError):
            continue
        moment = start + slot * length
        hours[moment.replace(minute=0, second=0, microsecond=0)].append(value)
    return {h: sum(v) / len(v) for h, v in sorted(hours.items())}


def parse_cnb_year(text: str) -> dict[date, float]:
    """EUR rates (CZK per 1 EUR) from the ČNB yearly rate file."""
    lines = [line for line in (text or "").splitlines() if line.strip()]
    if not lines:
        return {}
    header = lines[0].split("|")
    try:
        col = header.index("1 EUR")
    except ValueError:
        return {}
    rates = {}
    for line in lines[1:]:
        parts = line.split("|")
        try:
            day = datetime.strptime(parts[0], "%d.%m.%Y").date()
            rates[day] = float(parts[col].replace(",", "."))
        except (IndexError, ValueError):
            continue
    return rates


def rate_for(rates: dict[date, float], day: date) -> float | None:
    """Latest rate on or before the day (weekends, holidays), else the first after it."""
    if not rates:
        return None
    days = sorted(rates)
    i = bisect.bisect_right(days, day)
    return rates[days[i - 1]] if i else rates[days[0]]


class OteSource:
    """Fetches OTE day prices and ČNB rates with the integration's HTTP session."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session
        self._rates: dict[int, dict[date, float]] = {}

    async def _text(self, url: str, params: dict[str, str]) -> str:
        try:
            async with self._session.get(url, params=params, timeout=TIMEOUT) as resp:
                if resp.status != 200:
                    raise OteError(f"{url}: HTTP {resp.status}")
                return await resp.text()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise OteError(f"{url}: {err}") from err

    async def eur_rate(self, day: date) -> float | None:
        for year in (day.year, day.year - 1):
            if year not in self._rates:
                self._rates[year] = parse_cnb_year(await self._text(CNB_URL, {"rok": str(year)}))
            rates = {d: r for d, r in self._rates[year].items() if d <= day}
            if rates:
                return rate_for(rates, day)
        return rate_for(self._rates.get(day.year, {}), day)

    async def day_prices(self, day: date) -> dict[datetime, float]:
        """Hourly spot prices in CZK/kWh for one delivery day ({} when unpublished)."""
        import json

        text = await self._text(OTE_URL, {"language": "cs", "report_date": day.isoformat()})
        try:
            data = json.loads(text)
        except ValueError as err:
            raise OteError(f"OTE {day}: invalid JSON") from err
        eur = parse_ote_day(data, day)
        if not eur:
            return {}
        rate = await self.eur_rate(day)
        if rate is None:
            raise OteError(f"No EUR rate for {day}")
        return {h: round(v * rate / 1000, 5) for h, v in eur.items()}
