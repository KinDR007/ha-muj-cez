"""Invoice price breakdown (pure functions)."""

from datetime import date

from custom_components.muj_cez import invoice
from custom_components.muj_cez.api import MeterReadingPoint, SimulationItem

from .conftest import FIXTURES


def _csv() -> invoice.Invoice:
    return invoice.parse_csv("111", (FIXTURES / "invoice_settlement.csv").read_text())


def _pdf() -> invoice.Invoice:
    return invoice.parse_pdf_text("222", (FIXTURES / "invoice_settlement_pdf.txt").read_text())


def test_parse_csv() -> None:
    inv = _csv()
    assert inv.source == "csv"
    assert inv.vat_rate == 21
    assert inv.base == 2367.55
    assert inv.items_total == inv.base
    assert [i.kind for i in inv.items] == [
        "electricity_tax",
        "energy_vt",
        "supplier_fixed",
        "breaker",
        "system_services",
        "poze",
        "market_operator",
    ]
    energy = inv.items[1]
    assert (energy.group, energy.unit, energy.unit_price) == (invoice.SUPPLIER, "MWh", 2490.0)
    assert energy.quantity == 0.62928
    assert (energy.date_from, energy.date_to) == (date(2025, 7, 16), date(2025, 12, 31))
    assert inv.items[2].fixed and inv.items[2].quantity == 5.516
    assert inv.items[3].group == invoice.DISTRIBUTION
    assert (inv.period_from, inv.period_to) == (date(2025, 7, 16), date(2026, 2, 17))


def test_parse_pdf() -> None:
    inv = _pdf()
    assert inv.base == 1470.8
    assert inv.items_total == inv.base
    kinds = {i.kind: i for i in inv.items}
    assert set(kinds) == {
        "energy_nt",
        "discount",
        "supplier_fixed",
        "breaker",
        "distribution_vt",
        "infrastructure",
    }
    assert kinds["discount"].amount == -17.81 and kinds["discount"].unit_price == -2690.0
    assert kinds["supplier_fixed"].date_to == date(2025, 2, 28)
    assert kinds["breaker"].date_to == date(2025, 1, 31)  # period line with "Sazba D57D"


def test_parse_payout() -> None:
    text = (FIXTURES / "invoice_payout_pdf.txt").read_text()
    assert invoice.is_payout_text(text)
    assert not invoice.is_payout_text((FIXTURES / "invoice_settlement_pdf.txt").read_text())
    inv = invoice.parse_payout_pdf_text("333", text)
    assert inv.vat_rate == 0
    assert inv.base == 73.13
    (item,) = inv.items
    assert (item.kind, item.group, item.quantity) == ("payout", invoice.PAYOUT, 0.02184)
    assert item.unit_price == 3348.44
    assert (inv.period_from, inv.period_to) == (date(2026, 10, 1), date(2026, 10, 31))


def test_dict_roundtrip() -> None:
    inv = _csv()
    assert invoice.Invoice.from_dict(inv.as_dict()) == inv


def test_split_fixed_by_month_days() -> None:
    item = _csv().items[2]  # Stálá platba 16. 7. - 31. 12. 2025, 5.516 months
    parts = invoice.split_item(item)
    assert [p["month"] for p in parts] == [date(2025, m, 1) for m in range(7, 13)]
    assert parts[0]["quantity"] == round(5.516 * (16 / 31) / (16 / 31 + 5), 6)
    assert parts[1]["amount"] == round(706.05 / (16 / 31 + 5), 2)
    assert round(sum(p["amount"] for p in parts), 2) == 706.05
    assert all(p["estimated"] for p in parts)


def test_split_energy_by_weights() -> None:
    item = _csv().items[1]  # VT 16. 7. - 31. 12. 2025
    weights = {date(2025, m, 1): 100.0 for m in range(7, 13)}
    weights[date(2025, 12, 1)] = 300.0
    parts = invoice.split_item(item, weights)
    total = 100 * 16 / 31 + 4 * 100 + 300
    assert parts[-1]["amount"] == round(1566.91 - sum(p["amount"] for p in parts[:-1]), 2)
    assert parts[1]["amount"] == round(1566.91 * 100 / total, 2)
    # missing weight for a month: fall back to days
    del weights[date(2025, 9, 1)]
    parts = invoice.split_item(item, weights)
    assert parts[1]["amount"] == round(1566.91 * 31 / 169, 2)


def test_split_single_month_is_exact() -> None:
    item = _pdf().items[3]  # jistič January
    assert invoice.split_item(item) == [
        {"month": date(2025, 1, 1), "quantity": 1.0, "amount": 469.0, "estimated": False}
    ]


def test_monthly_breakdown() -> None:
    months = invoice.monthly_breakdown([_pdf()])
    assert list(months) == ["2025-01", "2025-02"]
    jan = months["2025-01"]
    assert jan["breaker"]["amount"] == 469.0 and not jan["breaker"]["estimated"]
    assert jan["breaker"]["vat"] == 98.49
    assert jan["supplier_fixed"]["quantity"] == 1.0 and jan["supplier_fixed"]["estimated"]
    assert jan["breaker"]["invoices"] == ["222"]
    total = sum(r["amount"] for m in months.values() for r in m.values())
    assert round(total, 2) == 1470.8


def test_unit_prices_at() -> None:
    prices = invoice.unit_prices_at([_csv(), _pdf()], date(2026, 3, 1))
    # only the last price period (ending 17. 2. 2026); energy ended 31. 12. 2025
    assert set(prices) == {"breaker", "system_services", "poze", "market_operator"}
    assert prices["breaker"].unit_price == 102.0
    prices = invoice.unit_prices_at([_csv(), _pdf()], date(2025, 12, 1))
    assert prices["energy_vt"].unit_price == 2490.0 and "breaker" not in prices
    assert invoice.unit_prices_at([_csv()], date(2025, 1, 1)) == {}


def _sim(start: date, end: date, kind: str, mwh: float, amount: float) -> SimulationItem:
    return SimulationItem(start, end, kind, mwh, amount, round(amount * 1.21, 2))


def _priced() -> invoice.Invoice:
    """Invoice whose last price period has all components of a single tariff point."""
    return invoice.parse_csv(
        "444",
        "DR;1;Cena za spotřebovanou elektřinu a služby;PS;21;0;CZK;0;CZK;0;CZK\n"
        + "\n".join(
            f"PS;CD;1;2;01.01.2026;17.02.2026;{n};{q};{u};{p};x;{a};CZK;3;"
            for n, q, u, p, a in [
                ("Daň z elektřiny", "0,1", "MWh", "28,30", "2,83"),
                ("Spotřeba / vysoký tarif (VT/T1)", "0,1", "MWh", "2.490,00", "249,00"),
                ("Stálá platba", "1", "měs.", "128,00", "128,00"),
            ]
        )
        + "\n"
        + "\n".join(
            f"OP;1;2;01.01.2026;17.02.2026;{n};{q};{u};{p};x;{a};CZK;3;"
            for n, q, u, p, a in [
                ("Distribuce / vysoký tarif (VT/T1)", "0,1", "MWh", "2.078,58", "207,86"),
                ("Systémové služby", "0,1", "MWh", "164,24", "16,42"),
                ("Platba za jistič", "1", "měs.", "102,00", "102,00"),
                ("Provoz nesíťové infrastruktury", "1", "měs.", "12,87", "12,87"),
            ]
        ),
    )


def test_simulation_parts_matched() -> None:
    prices = invoice.unit_prices_at([_priced()], date(2026, 3, 1))
    # 4761.12 CZK/MWh = 2490 + 28.30 + 2078.58 + 164.24 (real 2026 values)
    parts, matched = invoice.simulation_parts(
        _sim(date(2026, 3, 1), date(2026, 3, 31), "vt", 0.144, 685.6), prices
    )
    assert matched
    assert [p["kind"] for p in parts] == [
        "energy_vt",
        "electricity_tax",
        "distribution_vt",
        "system_services",
    ]
    assert round(sum(p["amount"] for p in parts), 2) == 685.6
    assert parts[0]["amount"] == round(685.6 * 2490 / 4761.12, 2)
    parts, matched = invoice.simulation_parts(
        _sim(date(2026, 3, 1), date(2026, 3, 31), "fixed", 0, 242.87), prices
    )
    assert matched and [p["amount"] for p in parts] == [128.0, 102.0, 12.87]
    # half a month
    parts, matched = invoice.simulation_parts(
        _sim(date(2026, 2, 18), date(2026, 2, 28), "fixed", 0, 95.45), prices
    )
    assert matched and parts[0]["quantity"] == round(11 / 28, 6)
    # changed prices
    _, matched = invoice.simulation_parts(
        _sim(date(2026, 3, 1), date(2026, 3, 31), "vt", 0.144, 800.0), prices
    )
    assert not matched
    assert invoice.simulation_parts(
        _sim(date(2026, 3, 1), date(2026, 3, 31), "nt", 0.1, 10.0), {}
    ) == ([], False)


def test_build_report() -> None:
    sim = [
        _sim(date(2026, 2, 1), date(2026, 2, 17), "vt", 0.05, 99.0),  # already invoiced
        _sim(date(2026, 2, 18), date(2026, 2, 28), "fixed", 0, 95.45),
        _sim(date(2026, 3, 1), date(2026, 3, 31), "vt", 0.144, 685.6),
        _sim(date(2026, 4, 1), date(2026, 4, 30), "vt", 0.1, 900.0),  # prices do not fit
    ]
    payout = invoice.parse_payout_pdf_text("333", (FIXTURES / "invoice_payout_pdf.txt").read_text())
    rep = invoice.build_report([_priced(), payout], sim, measured_until=date(2026, 3, 31))
    months = {m["month"]: m for m in rep["months"]}
    assert months["2026-01"]["source"] == "invoice"
    assert months["2026-02"]["source"] == "mixed"
    assert months["2026-03"]["source"] == "simulation" and months["2026-03"]["matched"]
    assert not months["2026-03"]["predicted"]
    apr = months["2026-04"]
    assert apr["predicted"] and not apr["matched"]
    assert [(i["kind"], i["amount"]) for i in apr["items"]] == [("sim_vt", 900.0)]
    half = invoice.build_report([], [_sim(date(2026, 4, 1), date(2026, 4, 15), "fixed", 0, 120.0)])
    assert half["months"][0]["items"][0]["quantity"] == 0.5
    feb = {i["kind"]: i for i in months["2026-02"]["items"]}
    assert feb["supplier_fixed"]["estimated"]  # invoice part 1. 1. - 17. 2. split
    assert not any(i["estimated"] for i in months["2026-03"]["items"])  # split by ČEZ
    assert round(sum(i["amount"] for i in months["2026-03"]["items"]), 2) == 685.6
    assert rep["vat_rate"] == 21
    assert rep["payout"][0]["month"] == "2026-10"
    assert [i["number"] for i in rep["invoices"]] == ["333", "444"]


def test_weights_from_readings() -> None:
    pts = [
        MeterReadingPoint(date(2026, 1, 31), 100.0, None, "1"),
        MeterReadingPoint(date(2026, 3, 31), 690.0, None, "1"),  # 59 days
        MeterReadingPoint(date(2026, 4, 15), 600.0, None, "1"),  # decrease: ignored
    ]
    w = invoice.weights_from_readings(pts)
    assert w == {date(2026, 2, 1): 280.0, date(2026, 3, 1): 310.0}


def _fee_invoice(
    number: str, start: date, end: date, amount: float, issued: date, **kw
) -> invoice.Invoice:
    months = sum(invoice._month_share(a, b) for a, b in invoice._month_parts(start, end))
    item = invoice.InvoiceItem(
        "Stálá platba",
        "supplier_fixed",
        invoice.SUPPLIER,
        start,
        end,
        round(months, 6),
        "month",
        round(amount / months, 2),
        amount,
    )
    return invoice.Invoice(number, "pdf", start, end, 21.0, amount, [item], issued, **kw)


def test_corrective_replaces_original() -> None:
    a = _fee_invoice("A", date(2025, 1, 1), date(2025, 12, 31), 1200.0, date(2026, 1, 10))
    b = _fee_invoice(
        "B", date(2025, 1, 1), date(2025, 12, 31), 1320.0, date(2026, 3, 1), corrective=True
    )
    valid, replaced = invoice.resolve_overlaps([b, a])
    assert [i.number for i in valid] == ["B"] and replaced == {"A": "B"}
    rep = invoice.build_report([a, b])
    total = sum(i["amount"] for m in rep["months"] for i in m["items"])
    assert round(total, 2) == 1320.0
    docs = {d["number"]: d for d in rep["invoices"]}
    assert docs["A"]["replaced_by"] == "B" and not docs["A"]["partial"]
    assert docs["B"]["corrective"] and docs["B"]["replaced_by"] is None


def test_later_invoice_cuts_overlap() -> None:
    a = _fee_invoice("A", date(2025, 1, 1), date(2025, 12, 31), 1200.0, date(2026, 1, 10))
    b = _fee_invoice("B", date(2025, 7, 1), date(2025, 12, 31), 660.0, date(2026, 2, 1))
    valid, replaced = invoice.resolve_overlaps([a, b])
    assert replaced == {"A": "B"}
    cut = next(i for i in valid if i.number == "A")
    (item,) = cut.items
    assert (item.date_from, item.date_to, item.amount, item.quantity) == (
        date(2025, 1, 1),
        date(2025, 6, 30),
        600.0,
        6.0,
    )
    assert item.estimated and (cut.period_from, cut.period_to) == (
        date(2025, 1, 1),
        date(2025, 6, 30),
    )
    rep = invoice.build_report([a, b])
    months = {m["month"]: m for m in rep["months"]}
    assert (
        months["2025-03"]["items"][0]["amount"] == 100.0
        and months["2025-03"]["items"][0]["estimated"]
    )
    assert months["2025-09"]["items"][0]["amount"] == 110.0
    assert {d["number"]: d["partial"] for d in rep["invoices"]} == {"A": True, "B": False}
    # energy is cut by days
    e = invoice.InvoiceItem(
        "Spotřeba / vysoký tarif (VT/T1)",
        "energy_vt",
        invoice.SUPPLIER,
        date(2025, 1, 1),
        date(2025, 1, 10),
        1.0,
        "MWh",
        2000.0,
        2000.0,
    )
    (part,) = invoice._cut(e, date(2025, 1, 5), date(2025, 1, 31))
    assert (part.date_to, part.quantity, part.amount) == (date(2025, 1, 4), 0.4, 800.0)


def test_difference_corrective_adds_up() -> None:
    a = _fee_invoice("A", date(2025, 1, 1), date(2025, 12, 31), 1200.0, date(2026, 1, 10))
    rev = invoice.InvoiceItem(
        "Stálá platba",
        "supplier_fixed",
        invoice.SUPPLIER,
        date(2025, 1, 1),
        date(2025, 12, 31),
        -12.0,
        "month",
        100.0,
        -1200.0,
    )
    new = invoice.InvoiceItem(
        "Stálá platba",
        "supplier_fixed",
        invoice.SUPPLIER,
        date(2025, 1, 1),
        date(2025, 12, 31),
        12.0,
        "month",
        110.0,
        1320.0,
    )
    b = invoice.Invoice(
        "B",
        "pdf",
        date(2025, 1, 1),
        date(2025, 12, 31),
        21.0,
        120.0,
        [rev, new],
        date(2026, 3, 1),
        True,
    )
    valid, replaced = invoice.resolve_overlaps([a, b])
    assert [i.number for i in valid] == ["A", "B"] and replaced == {}
    rep = invoice.build_report([a, b])
    assert round(sum(i["amount"] for m in rep["months"] for i in m["items"]), 2) == 1320.0


def test_payout_and_consumption_do_not_overlap() -> None:
    a = _fee_invoice("A", date(2026, 1, 1), date(2026, 12, 31), 1200.0, date(2027, 1, 10))
    p = invoice.parse_payout_pdf_text("P", (FIXTURES / "invoice_payout_pdf.txt").read_text())
    p.issued = date(2026, 11, 9)
    valid, replaced = invoice.resolve_overlaps([a, p])
    assert len(valid) == 2 and replaced == {}


def test_corrective_detection() -> None:
    assert invoice.is_corrective_text("VYÚČTOVÁNÍ ZA ELEKTŘINU\nOPRAVNÉ\nDaňový doklad: 1")
    assert not invoice.is_corrective_text("VYÚČTOVÁNÍ ZA ELEKTŘINU\nŘÁDNÉ\nDaňový doklad: 1")
    assert invoice.is_corrective_type("Opravná faktura - přeplatek")
    assert not invoice.is_corrective_type("Vyúčtování") and not invoice.is_corrective_type(None)
    text = (FIXTURES / "invoice_settlement_pdf.txt").read_text()
    assert not invoice.parse_pdf_text("1", text).corrective
    assert invoice.parse_pdf_text(
        "1", text.replace("ZA ELEKTŘINU", "ZA ELEKTŘINU\nOPRAVNÉ")
    ).corrective
    inv = _fee_invoice(
        "A", date(2025, 1, 1), date(2025, 1, 31), 100.0, date(2025, 2, 1), corrective=True
    )
    assert invoice.Invoice.from_dict(inv.as_dict()) == inv
    old = inv.as_dict()
    del old["issued"], old["corrective"]  # stored by the first version
    assert invoice.Invoice.from_dict(old).issued is None
