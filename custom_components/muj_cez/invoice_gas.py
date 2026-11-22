"""Gas settlement PDF ("Vyúčtování za plyn"): items and the split of simulation items.

Pure functions without Home Assistant imports; the electricity invoices are parsed by
invoice.py. The PDF lists the items per price period in two parts:

* "Spotřebovaný plyn (obchodní část)": Spotřeba (MWh), Stálá platba (měs.), Daň z plynu
* "Distribuce plynu (distribuční část)": Distribuce (MWh, includes the OTE fee in the
  price list), Stálá platba (měs.), Činnost OTE (MWh)

The same item names appear in both parts, so the part decides the kind. Item lines look
like "<name> <quantity> <MWh|měs.> <unit price> Kč <amount> Kč" under a
"<d. m. yyyy> - <d. m. yyyy>" period line, as in electricity invoices.
"""

from __future__ import annotations

import re
from datetime import date

from .invoice import (
    _ITEM,
    _NUM,
    _PERIOD,
    _SPACE,
    DISTRIBUTION,
    SUPPLIER,
    TAX,
    Invoice,
    InvoiceItem,
    _date,
    _finish,
    _item,
    _num,
    is_corrective_text,
)

COMMODITY_PREFIXES = ("P", "G")

# Kinds per part: (name prefix, kind, group).
_SUPPLIER_KINDS = [
    ("Spotřeba", "energy", SUPPLIER),
    ("Stálá platba", "supplier_fixed", SUPPLIER),
    ("Sleva", "discount", SUPPLIER),
    ("Daň z plynu", "gas_tax", TAX),
]
_DISTRIBUTION_KINDS = [
    ("Distribuce", "distribution", DISTRIBUTION),
    ("Stálá platba", "distribution_fixed", DISTRIBUTION),
    ("Činnost OTE", "market_operator", DISTRIBUTION),
    ("Platba za činnost operátora", "market_operator", DISTRIBUTION),
]

# Gas tax: the name, the meter and the amounts are on separate lines.
_TAX_NAME = "Daň z plynu"
_TAX_AMOUNTS = re.compile(
    rf"^(?P<qty>{_NUM}) (?P<unit>MWh) (?P<price>{_NUM}) Kč (?P<amount>{_NUM}) Kč$"
)
_BASE = re.compile(rf"^Cena za spotřebovaný plyn a služby (?P<base>{_NUM}) Kč (?P<rate>\d+) %")
_SUPPLIER_PART = "(obchodní část)"
_DISTRIBUTION_PART = "(distribuční část)"

# Components of the gas simulation items ("gas" = consumption, "fixed" = monthly fees),
# split in the ratio of the latest unit prices (see invoice.simulation_parts).
SIM_PARTS: dict[str, list[tuple[str, ...]]] = {
    "gas": [("energy",), ("gas_tax",), ("distribution",), ("market_operator",)],
    "fixed": [("supplier_fixed",), ("distribution_fixed",)],
}
SIM_NAMES = {
    "gas": "Spotřeba plynu (souhrn ze simulace)",
    "fixed": "Stálé platby (souhrn ze simulace)",
}


def is_gas(commodity: str | None) -> bool:
    return bool(commodity) and str(commodity).startswith(COMMODITY_PREFIXES)


def _classify(name: str, distribution: bool) -> tuple[str, str]:
    for prefix, kind, group in _DISTRIBUTION_KINDS if distribution else _SUPPLIER_KINDS:
        if name.startswith(prefix):
            return kind, group
    return "other", DISTRIBUTION if distribution else SUPPLIER


def parse_pdf_text(number: str, text: str) -> Invoice:
    """Gas settlement PDF (text extracted page by page)."""
    items: list[InvoiceItem] = []
    vat_rate, base = 21.0, None
    period: tuple[date, date] | None = None
    distribution: bool | None = None  # None before the first item part
    tax_pending = False
    for raw in text.splitlines():
        line = _SPACE.sub(" ", raw).strip()
        if m := _BASE.match(line):
            base, vat_rate = _num(m["base"]), float(m["rate"])
            continue
        if line.endswith(_SUPPLIER_PART):
            distribution, period = False, None
            continue
        if line.endswith(_DISTRIBUTION_PART):
            distribution, period = True, None
            continue
        if distribution is None:
            continue
        if m := _PERIOD.match(line):
            period = (_date(m[1]), _date(m[2]))
        # The period line of the distribution part carries the column headings.
        if line == _TAX_NAME:
            tax_pending = True
            continue
        if period and tax_pending and (m := _TAX_AMOUNTS.match(line)):
            tax_pending = False
            item = _item(_TAX_NAME, *period, m["qty"], m["unit"], m["price"], m["amount"])
            item.kind, item.group = _classify(item.name, distribution)
            items.append(item)
            continue
        if period and (m := _ITEM.match(line)):
            item = _item(m["name"], *period, m["qty"], m["unit"], m["price"], m["amount"])
            item.kind, item.group = _classify(item.name, distribution)
            items.append(item)
    inv = Invoice(number, "pdf", None, None, vat_rate, base, items)
    inv.corrective = is_corrective_text(text)
    return _finish(inv)
