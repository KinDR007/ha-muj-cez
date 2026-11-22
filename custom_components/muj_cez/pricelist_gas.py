"""Gas product price list ("Ceník plynu", PDF from the portal).

Pure functions without Home Assistant imports; electricity price lists are parsed by
pricelist.py. The PDF has a cover page with the validity ("Účinnost obchodních cen: od",
"Účinnost distribučních cen: od") followed by a table page, repeated for every price
period (e.g. the current year and the next one). The table has one row per band of the
yearly consumption ("Vařím do 1,89 MWh", "nad 7,56 do 15 MWh", ...): supply price
(Kč/MWh), supplier fixed fee (Kč/měsíc), distribution price incl. the OTE fee (Kč/MWh),
distribution fixed fee (Kč/měsíc) and the totals, with VAT and below in parentheses
without VAT. Households above 63 MWh pay a capacity price (Kč/m3), not supported here.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from .invoice import DISTRIBUTION, SUPPLIER, UNIT_MONTH, UNIT_MWH
from .pricelist import Fragment, Price, _clean, _date, _num

_NUM = r"\d{1,3}(?: \d{3})*,\d{2}"
# "Ú" may be a fragment of its own on the cover page.
_SUPPLIER_FROM = re.compile(r"činnost obchodních cen: od (\d{1,2}\. ?\d{1,2}\. ?\d{4})")
_DISTRIBUTION_FROM = re.compile(r"činnost distribučních cen: od (\d{1,2}\. ?\d{1,2}\. ?\d{4})")
_BAND = re.compile(r"do (\d+(?:,\d+)?) MWh")
_OTE = re.compile(rf"činnost OTE {_NUM} Kč \(({_NUM}) Kč\)/MWh")


@dataclass
class Band:
    upper_mwh: float  # yearly consumption up to (incl.)
    energy: float  # Kč/MWh without VAT
    supplier_fixed: float  # Kč/month
    distribution: float  # Kč/MWh, includes the OTE fee
    distribution_fixed: float  # Kč/month


@dataclass
class Section:
    supplier_from: date | None
    distribution_from: date | None
    ote: float | None  # OTE fee in the distribution price, Kč/MWh without VAT
    bands: list[Band] = field(default_factory=list)


@dataclass
class GasPriceList:
    sections: list[Section] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "commodity": "gas",
            "sections": [
                {
                    "supplier_from": s.supplier_from.isoformat() if s.supplier_from else None,
                    "distribution_from": s.distribution_from.isoformat()
                    if s.distribution_from
                    else None,
                    "ote": s.ote,
                    "bands": [vars(b) for b in s.bands],
                }
                for s in self.sections
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GasPriceList:
        def day(value: str | None) -> date | None:
            return date.fromisoformat(value) if value else None

        return cls(
            [
                Section(
                    day(s.get("supplier_from")),
                    day(s.get("distribution_from")),
                    s.get("ote"),
                    [Band(**b) for b in s.get("bands") or []],
                )
                for s in data.get("sections") or []
            ]
        )


def _bands(frags: list[Fragment], page: int) -> list[Band]:
    """Rows of the first table of a page (the capacity table has five values only)."""
    bands = []
    for p, y, x, text in frags:
        m = _BAND.search(text)
        if p != page or x > 200 or not m or "nad 63" in text:
            continue
        near = sorted(
            (f[2], f[3]) for f in frags if f[0] == page and f[2] > 200 and abs(f[1] - y) <= 5.5
        )
        net = [
            _num(v)
            for _x, t in near
            for g in re.findall(r"\(([^)]*)\)", t)
            for v in re.findall(_NUM, g)
        ]
        if len(net) != 6:
            continue
        energy, supplier_fixed, distribution, distribution_fixed, _total, _fixed = net
        bands.append(
            Band(
                float(m[1].replace(",", ".")),
                energy,
                supplier_fixed,
                distribution,
                distribution_fixed,
            )
        )
    return sorted(bands, key=lambda b: b.upper_mwh)


def parse(fragments: list[Fragment]) -> GasPriceList | None:
    """Gas price list from positioned text fragments; None when it is not one."""
    frags = [(p, y, x, _clean(t)) for p, y, x, t in fragments if _clean(t)]
    if not any("Ceník plynu" in f[3] for f in frags):
        return None
    sections: list[Section] = []
    dates: tuple[date | None, date | None] = (None, None)
    for page in sorted({f[0] for f in frags}):
        text = "\n".join(f[3] for f in frags if f[0] == page)
        sup, dist = _SUPPLIER_FROM.search(text), _DISTRIBUTION_FROM.search(text)
        if sup or dist:  # cover page of a price period
            dates = (_date(sup[1]) if sup else None, _date(dist[1]) if dist else None)
        bands = _bands(frags, page)
        if bands:
            ote = _OTE.search(text)
            sections.append(Section(dates[0], dates[1], _num(ote[1]) if ote else None, bands))
    return GasPriceList(sections) if sections else None


def item_prices(section: Section, yearly_mwh: float | None) -> dict[str, Price]:
    """Unit prices by item kind (as on the gas invoice) for the band of the consumption."""
    if yearly_mwh is None:
        return {}
    band = next((b for b in section.bands if yearly_mwh <= b.upper_mwh), None)
    if band is None:  # above the bands (capacity price)
        return {}
    ote = section.ote or 0.0
    out = {
        "energy": Price("energy", SUPPLIER, "Spotřeba", UNIT_MWH, band.energy),
        "supplier_fixed": Price(
            "supplier_fixed", SUPPLIER, "Stálá platba", UNIT_MONTH, band.supplier_fixed
        ),
        "distribution": Price(
            "distribution", DISTRIBUTION, "Distribuce", UNIT_MWH, round(band.distribution - ote, 2)
        ),
        "distribution_fixed": Price(
            "distribution_fixed", DISTRIBUTION, "Stálá platba", UNIT_MONTH, band.distribution_fixed
        ),
    }
    if ote:
        out["market_operator"] = Price(
            "market_operator", DISTRIBUTION, "Činnost OTE", UNIT_MWH, ote
        )
    return out


def price_sources(pricelists: list[GasPriceList], yearly_mwh: float | None) -> Any:
    """Candidate unit prices for a day (for invoice.build_report), best first: supplier
    part from the section valid that day, distribution part likewise, also mixed with the
    last invoice prices."""
    sections = [s for pl in pricelists for s in pl.sections]

    def latest(attr: str, day: date) -> Section | None:
        valid = [s for s in sections if getattr(s, attr) and getattr(s, attr) <= day]
        return max(valid, key=lambda s: getattr(s, attr), default=None)

    def sources(day: date, invoice_prices: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
        sup_s, reg_s = latest("supplier_from", day), latest("distribution_from", day)
        sup = {
            k: v
            for k, v in (item_prices(sup_s, yearly_mwh) if sup_s else {}).items()
            if v.group == SUPPLIER
        }
        reg = {
            k: v
            for k, v in (item_prices(reg_s, yearly_mwh) if reg_s else {}).items()
            if v.group != SUPPLIER
        }
        inv_sup = {k: v for k, v in invoice_prices.items() if v.group == SUPPLIER}
        inv_reg = {k: v for k, v in invoice_prices.items() if v.group != SUPPLIER}
        out: list[tuple[str, dict[str, Any]]] = []
        if sup and reg:
            out.append(("pricelist", {**sup, **reg}))
        if reg and inv_sup:
            out.append(("mixed", {**inv_sup, **reg}))
        if sup and inv_reg:
            out.append(("mixed", {**sup, **inv_reg}))
        return out

    return sources
