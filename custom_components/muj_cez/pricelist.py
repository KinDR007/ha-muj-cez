"""Product price list ("Ceník elektřiny pro domácnosti", PDF from the portal).

Pure functions without Home Assistant imports. The PDF is a table: one column per
distribution tariff (D01d ... D61d), numbered rows (supplier part 1-3, distribution
4-20 incl. circuit breaker rows, other regulated charges 21-25). Each row has prices
with VAT and below them in parentheses without VAT. The text extraction of the table
loses the order, so the parser works with positioned fragments (y, x, text) as pypdf's
visitor reports them.

Used for months without an invoice at the new prices (a new price year), so the
simulation of the current period can be split as well.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from .invoice import DISTRIBUTION, SUPPLIER, TAX, UNIT_MONTH, UNIT_MWH

Fragment = tuple[int, float, float, str]  # page, y (up), x, text

_NUM = r"\d{1,3}(?: \d{3})*,\d{2}"
_TOKEN = re.compile(rf"–|{_NUM}")
_TARIFF = re.compile(r"\bD\d{2}[a-z]\b")
_FROM = {
    "supplier_from": re.compile(r"Účinnost obchodních cen: od (\d{1,2}\. ?\d{1,2}\. ?\d{4})"),
    "distribution_from": re.compile(
        r"Účinnost distribučních cen: od (\d{1,2}\. ?\d{1,2}\. ?\d{4})"
    ),
}
# Circuit breaker rows of three phase supply: upper limit (A) -> row number.
_BREAKER_3F = [(10, 6), (16, 7), (20, 8), (25, 9), (32, 10), (40, 11), (50, 12), (63, 13)]
_BREAKER_3F_BIG = [(80, 14), (100, 15), (125, 16), (160, 17)]


@dataclass
class PriceList:
    product: str
    supplier_from: date | None
    distribution_from: date | None
    # tariff (lower case, e.g. "d57d") -> row number -> price without VAT (None = "–")
    prices: dict[str, dict[int, float | None]] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "product": self.product,
            "supplier_from": self.supplier_from.isoformat() if self.supplier_from else None,
            "distribution_from": self.distribution_from.isoformat()
            if self.distribution_from
            else None,
            "prices": {t: {str(r): p for r, p in rows.items()} for t, rows in self.prices.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PriceList:
        return cls(
            product=data.get("product") or "",
            supplier_from=date.fromisoformat(data["supplier_from"])
            if data.get("supplier_from")
            else None,
            distribution_from=date.fromisoformat(data["distribution_from"])
            if data.get("distribution_from")
            else None,
            prices={
                t: {int(r): p for r, p in rows.items()}
                for t, rows in (data.get("prices") or {}).items()
            },
        )


def _num(text: str) -> float:
    return float(text.replace(" ", "").replace(",", "."))


def _date(text: str) -> date:
    d, m, y = (int(x) for x in re.split(r"\.\s*", text.strip()) if x)
    return date(y, m, d)


def _clean(text: str) -> str:
    return re.sub(r"[\xa0 ]", " ", text).strip()


def parse(fragments: list[Fragment]) -> PriceList | None:
    """Price list from positioned text fragments; None when it is not a price list table."""
    frags = [(p, y, x, _clean(t)) for p, y, x, t in fragments if _clean(t)]
    text = "\n".join(t for *_, t in frags)
    if "Ceník" not in text or "Distribuční sazba" not in text:
        return None
    dates = {k: (_date(m[1]) if (m := r.search(text)) else None) for k, r in _FROM.items()}
    header = next((f for f in frags if f[3].startswith("Distribuční sazba")), None)
    if header is None:
        return None
    tariffs = [t.lower() for t in _TARIFF.findall(header[3])]
    page = header[0]
    # Product: the fragments of the line under the title on the table page.
    title = next((f for f in frags if f[0] == page and f[3].startswith("Ceník elektřiny")), None)
    product = ""
    if title:
        line = sorted(
            (f for f in frags if f[0] == page and 3 < title[1] - f[1] < 25 and f[2] < 300),
            key=lambda f: f[2],
        )
        top = max((f[1] for f in line), default=None)
        product = " ".join(f[3] for f in line if f[1] == top).replace(" - ", " - ")
        product = re.sub(r"\s+", " ", product).strip()
    # Row label: the row number starts a fragment in the left column (alone or followed by
    # the label text, sometimes by the values too).
    labels = []
    for f in frags:
        m = re.match(r"(\d{1,2})(?:\s|$)", f[3])
        if f[0] == page and f[2] < 36 and m and 1 <= int(m[1]) <= 30:
            labels.append((f, int(m[1])))
    prices: dict[str, dict[int, float | None]] = {t: {} for t in tariffs}
    for label, row in labels:
        y = label[1]
        near = [(f[2], f[3]) for f in frags if f[0] == page and f[2] > 120 and abs(f[1] - y) <= 5.5]
        near.append((label[2], re.sub(r"^\d{1,2}", " ", label[3])))
        bold: list[str] = []
        paren: list[str] = []
        for _x, t in sorted(near):
            paren += [m for g in re.findall(r"\(([^)]*)\)", t) for m in _TOKEN.findall(g)]
            bold += _TOKEN.findall(re.sub(r"\([^)]*\)", " ", t))
        if len(bold) != len(tariffs):
            continue
        values = [b for b in bold if b != "–"]
        net = [_num(v) for v in paren] if len(paren) == len(values) else None
        it = iter(net) if net is not None else None
        for tariff, b in zip(tariffs, bold, strict=True):
            if b == "–":
                prices[tariff][row] = None
            else:
                prices[tariff][row] = next(it) if it else round(_num(b) / 1.21, 2)
    if not any(prices.values()):
        return None
    return PriceList(product, dates["supplier_from"], dates["distribution_from"], prices)


def breaker_row(rows: dict[int, float | None], amps: float, phases: int) -> float | None:
    """Monthly circuit breaker price for the breaker value and number of phases."""
    if phases == 1:
        base = rows.get(6)
        if base is None:
            return None
        return round(base + max(0.0, amps - 25) * (rows.get(20) or 0.0), 2) if amps > 25 else base
    for limit, row in _BREAKER_3F:
        if amps <= limit:
            return rows.get(row)
    for limit, row in _BREAKER_3F_BIG:
        if amps <= limit and rows.get(row) is not None:
            return rows.get(row)
    top = rows.get(13)
    return round(top + (amps - 63) * (rows.get(19) or 0.0), 2) if top is not None else None


@dataclass
class Price:
    """Unit price of one item kind (same shape as the invoice items used for splitting)."""

    kind: str
    group: str
    name: str
    unit: str
    unit_price: float


def item_prices(
    pl: PriceList, tariff: str | None, amps: float | None, phases: int | None, poze_by: str
) -> dict[str, Price]:
    """Unit prices by item kind for the supply point's tariff and breaker.

    POZE is charged by the breaker or by consumption, whichever is lower over the
    billing period; `poze_by` ("breaker" / "consumption") selects the variant.
    """
    rows = pl.prices.get((tariff or "").lower())
    if not rows:
        return {}
    out: dict[str, Price] = {}

    def put(kind: str, group: str, name: str, unit: str, value: float | None) -> None:
        if value:  # zero / missing prices are not charged
            out[kind] = Price(kind, group, name, unit, value)

    put("energy_vt", SUPPLIER, "Spotřeba / vysoký tarif (VT/T1)", UNIT_MWH, rows.get(1))
    put("energy_nt", SUPPLIER, "Spotřeba / nízký tarif (NT/T2)", UNIT_MWH, rows.get(2))
    put("supplier_fixed", SUPPLIER, "Stálá platba", UNIT_MONTH, rows.get(3))
    put("distribution_vt", DISTRIBUTION, "Distribuce / vysoký tarif (VT/T1)", UNIT_MWH, rows.get(4))
    put("distribution_nt", DISTRIBUTION, "Distribuce / nízký tarif (NT/T2)", UNIT_MWH, rows.get(5))
    if amps and phases:
        put(
            "breaker", DISTRIBUTION, "Platba za jistič", UNIT_MONTH, breaker_row(rows, amps, phases)
        )
    put("electricity_tax", TAX, "Daň z elektřiny", UNIT_MWH, rows.get(21))
    put("system_services", DISTRIBUTION, "Systémové služby", UNIT_MWH, rows.get(22))
    put("infrastructure", DISTRIBUTION, "Provoz nesíťové infrastruktury", UNIT_MONTH, rows.get(23))
    if poze_by == "breaker" and amps and phases and rows.get(24):
        put("poze", DISTRIBUTION, "Platba POZE", UNIT_MONTH, round(rows[24] * amps * phases, 2))
    elif poze_by == "consumption":
        put("poze", DISTRIBUTION, "Platba POZE", UNIT_MWH, rows.get(25))
    return out


def poze_free(pl: PriceList, tariff: str | None) -> bool:
    """POZE by breaker costs nothing (state pays it, e.g. 2026): it is always the lower one."""
    rows = pl.prices.get((tariff or "").lower()) or {}
    return 24 in rows and not rows[24]


def price_sources(
    pricelists: list[PriceList], tariff: str | None, amps: float | None, phases: int | None
) -> Any:
    """Candidate unit prices for a day (for invoice.build_report), best first.

    Supplier part from the price list whose supplier prices apply on that day, regulated
    part (distribution, fees, taxes) from the one whose distribution prices apply; also
    mixed with the last invoice prices (new distribution prices with the old product or
    the other way round). Both POZE variants are offered, the simulation decides.
    """

    def latest(attr: str, day: date) -> PriceList | None:
        valid = [p for p in pricelists if getattr(p, attr) and getattr(p, attr) <= day]
        return max(valid, key=lambda p: getattr(p, attr), default=None)

    def sources(day: date, invoice_prices: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
        sup_pl, reg_pl = latest("supplier_from", day), latest("distribution_from", day)
        inv_sup = {k: v for k, v in invoice_prices.items() if v.group == SUPPLIER}
        inv_reg = {k: v for k, v in invoice_prices.items() if v.group != SUPPLIER}
        out: list[tuple[str, dict[str, Any]]] = []
        for poze in ("breaker", "consumption"):
            sup = (
                {
                    k: v
                    for k, v in item_prices(sup_pl, tariff, amps, phases, poze).items()
                    if v.group == SUPPLIER
                }
                if sup_pl
                else {}
            )
            reg = (
                {
                    k: v
                    for k, v in item_prices(reg_pl, tariff, amps, phases, poze).items()
                    if v.group != SUPPLIER
                }
                if reg_pl
                else {}
            )
            if sup and reg:
                out.append(("pricelist", {**sup, **reg}))
            if reg and inv_sup:
                out.append(("mixed", {**inv_sup, **reg}))
            if sup and inv_reg:
                out.append(("mixed", {**sup, **inv_reg}))
        return out

    return sources
