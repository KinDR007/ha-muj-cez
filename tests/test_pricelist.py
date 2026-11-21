"""Product price list: table parsing from positioned PDF fragments, prices for a tariff."""

from __future__ import annotations

import json
from datetime import date

from custom_components.muj_cez import invoice, pricelist
from custom_components.muj_cez.api import SimulationItem

from .conftest import FIXTURES


def _pl() -> pricelist.PriceList:
    frags = [tuple(f) for f in json.loads((FIXTURES / "pricelist_fragments.json").read_text())]
    pl = pricelist.parse(frags)
    assert pl is not None
    return pl


def test_parse() -> None:
    pl = _pl()
    assert pl.product == "Elektřina - na 2 roky v akci"
    assert (pl.supplier_from, pl.distribution_from) == (date(2026, 1, 30), date(2026, 1, 1))
    assert list(pl.prices) == [
        "d01d", "d02d", "d25d", "d26d", "d27d", "d35d", "d45d", "d56d", "d57d", "d61d"
    ]  # fmt: skip
    d57 = pl.prices["d57d"]
    assert (d57[1], d57[2], d57[3]) == (2628.10, 2520.66, 135.0)
    assert (d57[4], d57[5], d57[9]) == (754.77, 116.5, 555.0)
    assert (d57[21], d57[22], d57[23], d57[24], d57[25]) == (28.3, 164.24, 12.87, 0.0, 495.0)
    assert d57[19] is None and d57[14] == 3093.0  # "–" and the extra rows of D57d
    d02 = pl.prices["d02d"]
    assert d02[2] is None and d02[5] is None  # single tariff: no NT
    assert (d02[1], d02[6], d02[20]) == (2388.43, 102.0, 3.41)
    assert pricelist.PriceList.from_dict(pl.as_dict()) == pl


def test_parse_rejects_other_documents() -> None:
    assert pricelist.parse([(0, 700.0, 30.0, "Všeobecné obchodní podmínky")]) is None
    assert pricelist.parse([]) is None


def test_breaker_row() -> None:
    rows = _pl().prices["d02d"]
    assert pricelist.breaker_row(rows, 25, 1) == 102.0
    assert pricelist.breaker_row(rows, 32, 1) == round(102.0 + 7 * 3.41, 2)
    assert pricelist.breaker_row(rows, 25, 3) == rows[9]
    assert pricelist.breaker_row(rows, 63, 3) == rows[13]
    assert pricelist.breaker_row(_pl().prices["d57d"], 100, 3) == 5335.0
    assert pricelist.breaker_row(rows, 80, 3) == round(rows[13] + 17 * rows[19], 2)


def test_item_prices() -> None:
    pl = _pl()
    prices = pricelist.item_prices(pl, "D57D", 25, 3, "breaker")
    assert {k: (p.unit, p.unit_price) for k, p in prices.items()} == {
        "energy_vt": ("MWh", 2628.10),
        "energy_nt": ("MWh", 2520.66),
        "supplier_fixed": ("month", 135.0),
        "distribution_vt": ("MWh", 754.77),
        "distribution_nt": ("MWh", 116.5),
        "breaker": ("month", 555.0),
        "electricity_tax": ("MWh", 28.3),
        "system_services": ("MWh", 164.24),
        "infrastructure": ("month", 12.87),
    }  # POZE by breaker is 0 in 2026: not charged
    assert prices["breaker"].group == invoice.DISTRIBUTION
    assert prices["electricity_tax"].group == invoice.TAX
    by_use = pricelist.item_prices(pl, "D57D", 25, 3, "consumption")
    assert (by_use["poze"].unit, by_use["poze"].unit_price) == ("MWh", 495.0)
    assert pricelist.poze_free(pl, "D57D")
    assert pricelist.item_prices(pl, "D99X", 25, 3, "breaker") == {}


def _sim(start: date, end: date, kind: str, mwh: float, amount: float) -> SimulationItem:
    return SimulationItem(start, end, kind, mwh, amount, round(amount * 1.21, 2))


def _old_invoice() -> invoice.Invoice:
    """2025 invoice of the same point (old product, old distribution prices)."""

    def item(name: str, qty: float, unit: str, price: float) -> invoice.InvoiceItem:
        kind, group = invoice.classify(name)
        a, b = date(2025, 12, 1), date(2025, 12, 31)
        return invoice.InvoiceItem(name, kind, group, a, b, qty, unit, price, round(qty * price, 2))

    items = [
        item("Spotřeba / vysoký tarif (VT/T1)", 0.1, "MWh", 2630.0),
        item("Spotřeba / nízký tarif (NT/T2)", 0.8, "MWh", 2630.0),
        item("Stálá platba", 1, "month", 128.0),
        item("Daň z elektřiny", 0.9, "MWh", 28.3),
        item("Distribuce / vysoký tarif (VT/T1)", 0.1, "MWh", 721.45),
        item("Distribuce / nízký tarif (NT/T2)", 0.8, "MWh", 206.0),
        item("Platba za jistič", 1, "month", 469.0),
        item("Systémové služby", 0.9, "MWh", 170.92),
        item("Platba POZE", 0.9, "MWh", 495.0),
        item("Provoz nesíťové infrastruktury", 1, "month", 10.84),
    ]
    total = round(sum(i.amount for i in items), 2)
    return invoice.Invoice(
        "OLD", "pdf", date(2025, 12, 1), date(2025, 12, 31), 21.0, total, items, date(2026, 1, 12)
    )


def test_new_price_year_split_with_price_list() -> None:
    sources = pricelist.price_sources([_pl()], "D57D", 25, 3)
    nt_new = 2520.66 + 116.5 + 28.3 + 164.24  # 2026 product + 2026 distribution
    nt_mixed = 2630.0 + 116.5 + 28.3 + 164.24  # old product, 2026 distribution
    sim = [
        _sim(date(2026, 1, 1), date(2026, 1, 31), "nt", 0.9, round(0.9 * nt_mixed, 2)),
        _sim(date(2026, 1, 1), date(2026, 1, 31), "fixed", 0, 128 + 555 + 12.87),
        _sim(date(2026, 3, 1), date(2026, 3, 31), "nt", 0.4, round(0.4 * nt_new, 2)),
        _sim(date(2026, 3, 1), date(2026, 3, 31), "fixed", 0, 135 + 555 + 12.87),
    ]
    rep = invoice.build_report([_old_invoice()], sim, None, None, sources)
    months = {m["month"]: m for m in rep["months"]}
    jan, mar = months["2026-01"], months["2026-03"]
    assert jan["matched"] and jan["prices"] == ["mixed"]
    assert mar["matched"] and mar["prices"] == ["pricelist"]
    items = {i["kind"]: i for i in mar["items"]}
    assert items["energy_nt"]["prices"] == [2520.66] and items["breaker"]["amount"] == 555.0
    assert "poze" not in items  # free in 2026
    assert round(sum(i["amount"] for i in mar["items"]), 2) == round(0.4 * nt_new + 702.87, 2)
    # without the price list the new year stays a simulation total
    rep = invoice.build_report([_old_invoice()], sim)
    assert not {m["month"]: m for m in rep["months"]}["2026-03"]["matched"]


def test_rounded_quantity_tolerance() -> None:
    """The simulation rounds MWh to 3 decimals: 0.02353 MWh is shown as 0.024."""
    prices = pricelist.item_prices(_pl(), "D57D", 25, 3, "breaker")
    vt = 2628.10 + 754.77 + 28.3 + 164.24
    item = _sim(date(2026, 12, 1), date(2026, 12, 31), "vt", 0.024, round(0.02353 * vt, 2))
    _parts, ok = invoice.simulation_parts(item, prices)
    assert ok
