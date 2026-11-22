"""Gas price list (pricelist_gas): bands from positioned PDF fragments, prices for a day."""

from __future__ import annotations

import json
from datetime import date

from custom_components.muj_cez import invoice, invoice_gas, pricelist, pricelist_gas
from custom_components.muj_cez.api import SimulationItem

from .conftest import FIXTURES

FRAGS = [tuple(f) for f in json.loads((FIXTURES / "pricelist_gas_fragments.json").read_text())]
INVOICE = (FIXTURES / "invoice_gas_pdf.txt").read_text()


def _pl() -> pricelist_gas.GasPriceList:
    pl = pricelist_gas.parse(FRAGS)
    assert pl is not None
    return pl


def test_parse_sections_and_bands() -> None:
    pl = _pl()
    assert [(s.supplier_from, s.distribution_from, s.ote) for s in pl.sections] == [
        (date(2026, 1, 1), date(2026, 1, 1), 4.06),
        (date(2027, 1, 1), date(2026, 1, 1), 4.06),
    ]
    first = pl.sections[0].bands
    assert [b.upper_mwh for b in first] == [1.89, 7.56, 15.0, 25.0, 45.0, 63.0]
    assert (first[0].energy, first[0].supplier_fixed) == (1289.26, 94.0)
    assert (first[0].distribution, first[0].distribution_fixed) == (755.87, 110.94)
    assert pl.sections[1].bands[0].energy == 1438.02
    assert pricelist_gas.GasPriceList.from_dict(pl.as_dict()) == pl


def test_parsers_do_not_mix() -> None:
    assert pricelist.parse(FRAGS) is None


def test_item_prices_by_band() -> None:
    section = _pl().sections[0]
    low = pricelist_gas.item_prices(section, 1.67)
    # The distribution price includes the OTE fee, the invoice lists them apart.
    assert (low["distribution"].unit_price, low["market_operator"].unit_price) == (751.81, 4.06)
    assert low["supplier_fixed"].unit_price == 94.0
    assert pricelist_gas.item_prices(section, 10)["distribution_fixed"].unit_price == 188.65
    assert pricelist_gas.item_prices(section, 100) == {}  # capacity price
    assert pricelist_gas.item_prices(section, None) == {}


def test_new_price_year_split_with_price_list() -> None:
    """January 2027: new supply price only in the price list, the simulation matches it."""
    items = [
        SimulationItem(date(2027, 1, 1), date(2027, 1, 31), "gas", 0.167, 366.05, 442.87),
        SimulationItem(date(2027, 1, 1), date(2027, 1, 31), "fixed", 0.0, 204.94, 247.98),
    ]
    report = invoice.build_report(
        [invoice_gas.parse_pdf_text("G1", INVOICE)],
        items,
        None,
        None,
        pricelist_gas.price_sources([_pl()], 1.67),
        invoice_gas.SIM_PARTS,
        invoice_gas.SIM_NAMES,
    )
    (jan,) = [m for m in report["months"] if m["month"] == "2027-01"]
    assert jan["matched"] is True
    kinds = {i["kind"]: i for i in jan["items"]}
    assert kinds["energy"]["prices"] == [1438.02]
    assert round(sum(i["amount"] for i in jan["items"]), 2) == round(366.05 + 204.94, 2)
