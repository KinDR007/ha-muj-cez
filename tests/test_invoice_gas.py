"""Gas settlement PDF and the split of gas simulation items (invoice_gas)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from custom_components.muj_cez import invoice, invoice_gas
from custom_components.muj_cez.api import SimulationItem

TEXT = (Path(__file__).parent / "fixtures" / "invoice_gas_pdf.txt").read_text()


def _inv() -> invoice.Invoice:
    return invoice_gas.parse_pdf_text("G1", TEXT)


def test_parse_gas_pdf() -> None:
    inv = _inv()
    assert inv.base == 5839.31 and inv.items_total == inv.base
    assert inv.vat_rate == 21.0
    assert (inv.period_from, inv.period_to) == (date(2025, 10, 9), date(2026, 10, 7))
    by_kind: dict[str, list[invoice.InvoiceItem]] = {}
    for item in inv.items:
        by_kind.setdefault(item.kind, []).append(item)
    assert set(by_kind) == {
        "energy",
        "supplier_fixed",
        "gas_tax",
        "distribution",
        "distribution_fixed",
        "market_operator",
    }
    # Same names in both parts: the part decides.
    assert [i.unit_price for i in by_kind["supplier_fixed"]] == [89.0, 94.0]
    assert [i.unit_price for i in by_kind["distribution_fixed"]] == [104.47, 110.94]
    assert {i.group for i in by_kind["distribution"]} == {invoice.DISTRIBUTION}
    # Exempt households: the tax is listed with zero amounts.
    assert [(i.quantity, i.amount) for i in by_kind["gas_tax"]] == [(0.47052, 0.0), (1.19766, 0.0)]


def test_electricity_parser_does_not_classify_gas() -> None:
    """The electricity parser would put the distribution fixed fee to the supplier."""
    kinds = {i.kind for i in invoice.parse_pdf_text("G1", TEXT).items}
    assert "distribution_fixed" not in kinds


def test_gas_simulation_split_with_invoice_prices() -> None:
    inv = _inv()
    items = [
        SimulationItem(date(2026, 11, 1), date(2026, 11, 30), "gas", 0.153, 312.36, 377.96),
        SimulationItem(date(2026, 11, 1), date(2026, 11, 30), "fixed", 0.0, 204.94, 247.98),
        SimulationItem(date(2027, 1, 1), date(2027, 1, 31), "gas", 0.167, 366.05, 442.87),
    ]
    report = invoice.build_report(
        [inv], items, None, None, None, invoice_gas.SIM_PARTS, invoice_gas.SIM_NAMES
    )
    months = {m["month"]: m for m in report["months"]}
    nov = months["2026-11"]
    assert nov["matched"] is True
    kinds = {i["kind"]: i for i in nov["items"]}
    assert set(kinds) == {
        "energy",
        "distribution",
        "market_operator",
        "supplier_fixed",
        "distribution_fixed",
    }
    assert round(sum(i["amount"] for i in nov["items"]), 2) == round(312.36 + 204.94, 2)
    assert (
        kinds["supplier_fixed"]["amount"] == 94.0
        and kinds["distribution_fixed"]["amount"] == 110.94
    )
    # New price year without a price list: kept as the simulation summary.
    jan = months["2027-01"]
    assert jan["matched"] is False
    assert jan["items"][0]["name"] == "Spotřeba plynu (souhrn ze simulace)"
