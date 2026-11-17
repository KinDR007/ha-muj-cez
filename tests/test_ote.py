"""OTE day-ahead prices and ČNB rates."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from custom_components.muj_cez import ote

from .conftest import FIXTURES, load


def test_parse_hourly_day() -> None:
    prices = ote.parse_ote_day(load("ote_hourly.json"), date(2025, 9, 30))
    assert len(prices) == 24
    first = next(iter(prices))
    assert first == datetime(2025, 9, 29, 22, tzinfo=UTC)  # local midnight (CEST)


def test_parse_quarter_hour_day_uses_hourly_index() -> None:
    data = load("ote_15min.json")
    prices = ote.parse_ote_day(data, date(2026, 6, 1))
    assert len(prices) == 24
    index = next(line for line in data["data"]["dataLine"] if "60min" in line["title"])
    assert prices[datetime(2026, 5, 31, 22, tzinfo=UTC)] == pytest.approx(index["point"][0]["y"])


def test_parse_dst_day_and_quarter_averaging() -> None:
    # 25 hour day (end of DST), 100 quarter hours, only a 15 min price line.
    data = {
        "data": {
            "dataLine": [
                {
                    "title": "Množství (MWh)",
                    "point": [{"x": str(i), "y": 1} for i in range(1, 101)],
                },
                {
                    "title": "15min cena (EUR/MWh)",
                    "point": [{"x": str(i), "y": float(i % 4)} for i in range(1, 101)],
                },
            ]
        }
    }
    prices = ote.parse_ote_day(data, date(2026, 10, 25))
    assert len(prices) == 25
    assert set(prices.values()) == {1.5}
    assert ote.parse_ote_day({}, date(2026, 10, 25)) == {}
    assert ote.parse_ote_day(None, date(2026, 10, 25)) == {}


def test_cnb_rates() -> None:
    rates = ote.parse_cnb_year((FIXTURES / "cnb_2026.txt").read_text())
    assert date(2026, 6, 1) in rates
    assert 20 < rates[date(2026, 6, 1)] < 30
    # Saturday uses Friday's rate.
    assert ote.rate_for(rates, date(2026, 5, 30)) == rates[date(2026, 5, 29)]
    assert ote.rate_for({}, date(2026, 5, 30)) is None
    assert ote.parse_cnb_year("") == {}
    assert ote.parse_cnb_year("Datum|1 USD\n01.01.2026|20,0") == {}


class FakeResponse:
    def __init__(self, status: int, text: str) -> None:
        self.status = status
        self._text = text

    async def __aenter__(self) -> FakeResponse:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def text(self) -> str:
        return self._text


class FakeSession:
    def __init__(self, routes: dict[str, tuple[int, str]]) -> None:
        self.routes = routes
        self.calls: list[tuple[str, dict]] = []

    def get(self, url: str, params: dict, timeout: object) -> FakeResponse:
        self.calls.append((url, params))
        return FakeResponse(*self.routes[url])


OTE_15MIN = (FIXTURES / "ote_15min.json").read_text()
CNB_2026 = (FIXTURES / "cnb_2026.txt").read_text()


async def test_day_prices_in_czk() -> None:
    session = FakeSession({ote.OTE_URL: (200, OTE_15MIN), ote.CNB_URL: (200, CNB_2026)})
    source = ote.OteSource(session)  # type: ignore[arg-type]
    prices = await source.day_prices(date(2026, 6, 1))
    eur = ote.parse_ote_day(load("ote_15min.json"), date(2026, 6, 1))
    rate = ote.parse_cnb_year(CNB_2026)[date(2026, 6, 1)]
    hour = datetime(2026, 5, 31, 22, tzinfo=UTC)
    assert prices[hour] == pytest.approx(eur[hour] * rate / 1000, abs=1e-5)
    await source.day_prices(date(2026, 6, 2))
    # The yearly rate file is loaded once.
    assert sum(1 for url, _ in session.calls if url == ote.CNB_URL) == 1


async def test_day_prices_errors() -> None:
    source = ote.OteSource(FakeSession({ote.OTE_URL: (500, "")}))  # type: ignore[arg-type]
    with pytest.raises(ote.OteError):
        await source.day_prices(date(2026, 6, 1))
    source = ote.OteSource(FakeSession({ote.OTE_URL: (200, "not json")}))  # type: ignore[arg-type]
    with pytest.raises(ote.OteError):
        await source.day_prices(date(2026, 6, 1))
    empty = '{"data": {"dataLine": []}}'
    source = ote.OteSource(FakeSession({ote.OTE_URL: (200, empty)}))  # type: ignore[arg-type]
    assert await source.day_prices(date(2026, 6, 1)) == {}
