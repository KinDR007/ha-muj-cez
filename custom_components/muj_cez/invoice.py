"""Invoice price breakdown: parse portal invoice data files and split costs.

Pure functions without Home Assistant imports. Sources, in order of preference:

* CSV data file of a settlement ("Datový soubor.csv" in billing detail), records
  PS (supply), R2 (distribution), OP (other regulated items), DR (tax summary).
* Invoice PDF text (page text joined by newlines), for invoices without the CSV.
  Item lines look like "<name> <quantity> <MWh|měs.> <unit price> Kč <amount> Kč"
  under a "<d. m. yyyy> - <d. m. yyyy>" period line.
* Payout self-billing PDF (production point): quantity and amount only.

Amounts are without VAT as the provider states them; VAT is applied per invoice rate.
"""

from __future__ import annotations

import calendar
import re
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from typing import Any

# Item kinds and their groups. Names follow the provider's invoice.
SUPPLIER = "supplier"
DISTRIBUTION = "distribution"
TAX = "tax"
PAYOUT = "payout"

_KINDS: list[tuple[str, str, str]] = [
    # (name prefix, kind, group)
    ("Spotřeba / vysoký tarif", "energy_vt", SUPPLIER),
    ("Spotřeba / nízký tarif", "energy_nt", SUPPLIER),
    ("Spotřeba", "energy", SUPPLIER),
    ("Stálá platba", "supplier_fixed", SUPPLIER),
    ("Sleva", "discount", SUPPLIER),
    ("Daň z elektřiny", "electricity_tax", TAX),
    ("Distribuce / vysoký tarif", "distribution_vt", DISTRIBUTION),
    ("Distribuce / nízký tarif", "distribution_nt", DISTRIBUTION),
    ("Platba za jistič", "breaker", DISTRIBUTION),
    ("Systémové služby", "system_services", DISTRIBUTION),
    ("Platba POZE", "poze", DISTRIBUTION),
    ("Provoz nesíťové infrastruktury", "infrastructure", DISTRIBUTION),
    ("Činnost OTE", "market_operator", DISTRIBUTION),
    ("Platba za činnost operátora", "market_operator", DISTRIBUTION),
]

UNIT_MWH = "MWh"
UNIT_MONTH = "month"


@dataclass
class InvoiceItem:
    name: str
    kind: str
    group: str
    date_from: date
    date_to: date
    quantity: float
    unit: str  # UNIT_MWH or UNIT_MONTH
    unit_price: float | None  # CZK per unit without VAT
    amount: float  # CZK without VAT
    # Part of a provider item cut here (overlap with a later invoice): amounts estimated.
    estimated: bool = False

    @property
    def fixed(self) -> bool:
        """Charged per month (independent of consumption)."""
        return self.unit == UNIT_MONTH


@dataclass
class Invoice:
    number: str  # receivables document number (portal "billingReceivablesAndPayables...")
    source: str  # "csv", "pdf" or "payout"
    period_from: date | None
    period_to: date | None
    vat_rate: float  # percent
    base: float | None  # tax base of the consumption part as stated by the invoice
    items: list[InvoiceItem] = field(default_factory=list)
    issued: date | None = None  # document date (later documents win on overlapping days)
    corrective: bool = False  # corrective settlement ("opravná faktura")

    @property
    def items_total(self) -> float:
        return round(sum(i.amount for i in self.items), 2)

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        for key in ("period_from", "period_to", "issued"):
            data[key] = data[key].isoformat() if data[key] else None
        for item in data["items"]:
            item["date_from"] = item["date_from"].isoformat()
            item["date_to"] = item["date_to"].isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Invoice:
        items = [
            InvoiceItem(
                **{
                    **i,
                    "date_from": date.fromisoformat(i["date_from"]),
                    "date_to": date.fromisoformat(i["date_to"]),
                }
            )
            for i in data.get("items", [])
        ]
        return cls(
            number=data["number"],
            source=data["source"],
            period_from=date.fromisoformat(data["period_from"])
            if data.get("period_from")
            else None,
            period_to=date.fromisoformat(data["period_to"]) if data.get("period_to") else None,
            vat_rate=data["vat_rate"],
            base=data.get("base"),
            items=items,
            issued=date.fromisoformat(data["issued"]) if data.get("issued") else None,
            corrective=bool(data.get("corrective")),
        )


def classify(name: str) -> tuple[str, str]:
    for prefix, kind, group in _KINDS:
        if name.startswith(prefix):
            return kind, group
    return "other", SUPPLIER


def _num(text: str) -> float:
    """Czech number: "1.234,56", "1 234,56", trailing minus "12,50-"."""
    text = text.strip().replace("\xa0", "").replace(" ", "").replace(" ", "")
    negative = text.endswith("-") or text.startswith("-")
    value = float(text.strip("-").replace(".", "").replace(",", "."))
    return -value if negative else value


def _date(text: str) -> date:
    """ "26.02.2025" or "1. 1. 2025"."""
    d, m, y = (int(x) for x in re.split(r"\.\s*", text.strip().rstrip(".")) if x)
    return date(y, m, d)


def _unit(text: str) -> str:
    return UNIT_MWH if text.lower() in ("mwh", "kwh") else UNIT_MONTH


def _item(
    name: str, start: date, end: date, qty: str, unit: str, price: str | None, amount: str
) -> InvoiceItem:
    kind, group = classify(name)
    quantity = _num(qty)
    if unit.lower() == "kwh":
        quantity /= 1000
    return InvoiceItem(
        name=name.strip(),
        kind=kind,
        group=group,
        date_from=start,
        date_to=end,
        quantity=round(quantity, 6),
        unit=_unit(unit),
        unit_price=_num(price) if price else None,
        amount=_num(amount),
    )


def parse_csv(number: str, text: str) -> Invoice:
    """Settlement data file (semicolon separated, Czech number format)."""
    items: list[InvoiceItem] = []
    vat_rate, base = 21.0, None
    for line in text.splitlines():
        c = [x.strip() for x in line.split(";")]
        if not c or not c[0]:
            continue
        if c[0] == "DR" and len(c) > 5 and c[2].startswith("Cena za"):
            vat_rate, base = float(c[4] or 0), _num(c[5])
        elif c[0] in ("PS", "R2") and len(c) > 11 and c[1] == "CD":
            # PS;CD;doc;place;from;to;name;qty;unit;price;price unit;amount;CZK;ean
            items.append(_item(c[6], _date(c[4]), _date(c[5]), c[7], c[8], c[9], c[11]))
        elif c[0] == "OP" and len(c) > 10:
            # OP;doc;place;from;to;name;qty;unit;price;price unit;amount;CZK;ean
            items.append(_item(c[5], _date(c[3]), _date(c[4]), c[6], c[7], c[8], c[10]))
    return _finish(Invoice(number, "csv", None, None, vat_rate, base, items))


_SPACE = re.compile(r"[\xa0 ]")
_NUM = r"-?\d{1,3}(?: \d{3})*,\d+"
_PERIOD = re.compile(r"^(\d{1,2}\. ?\d{1,2}\. ?\d{4}) ?[-–] ?(\d{1,2}\. ?\d{1,2}\. ?\d{4})\b")
_ITEM = re.compile(
    rf"^(?P<name>\D.*?) (?P<qty>{_NUM}) (?P<unit>MWh|kWh|měs\.) (?P<price>{_NUM}) Kč (?P<amount>{_NUM}) Kč$"
)
_BASE = re.compile(
    rf"^Cena za spotřebovanou elektřinu a služby (?P<base>{_NUM}) Kč (?P<rate>\d+) %"
)
_PAYOUT = re.compile(
    rf"^\S+ +(?P<name>.+?) +(?P<qty>{_NUM}) MWh +(?:(?P<price>{_NUM}) Kč +)?(?P<amount>{_NUM}) Kč$"
)
_PAYOUT_PERIOD = re.compile(r"Období: (\d{2}\.\d{2}\.\d{4}) - (\d{2}\.\d{2}\.\d{4})")


def parse_pdf_text(number: str, text: str) -> Invoice:
    """Consumption settlement PDF (text extracted page by page)."""
    items: list[InvoiceItem] = []
    vat_rate, base = 21.0, None
    period: tuple[date, date] | None = None
    in_detail = False
    for raw in text.splitlines():
        line = _SPACE.sub(" ", raw).strip()
        if m := _BASE.match(line):
            base, vat_rate = _num(m["base"]), float(m["rate"])
            continue
        if line.startswith("Podrobné vyúčtování"):
            in_detail = True
        if not in_detail:
            continue
        if m := _PERIOD.match(line):
            period = (_date(m[1]), _date(m[2]))
            continue
        if period and (m := _ITEM.match(line)):
            items.append(_item(m["name"], *period, m["qty"], m["unit"], m["price"], m["amount"]))
    inv = Invoice(number, "pdf", None, None, vat_rate, base, items)
    inv.corrective = is_corrective_text(text)
    return _finish(inv)


def parse_payout_pdf_text(number: str, text: str) -> Invoice:
    """Production point self-billing ("Vyúčtování ... vystaveno zákazníkem")."""
    text = _SPACE.sub(" ", text)
    period = _PAYOUT_PERIOD.search(text)
    items: list[InvoiceItem] = []
    if period:
        start, end = _date(period[1]), _date(period[2])
        for raw in text.splitlines():
            line = raw.strip()
            if line.startswith("Celkem"):
                break
            if m := _PAYOUT.match(line):
                item = _item(m["name"], start, end, m["qty"], "MWh", m["price"], m["amount"])
                item.kind, item.group = "payout", PAYOUT
                if item.unit_price is None and item.quantity:
                    item.unit_price = round(item.amount / item.quantity, 2)
                items.append(item)
    rate = re.search(r"Cena za dodávku elektřiny +" + _NUM + r" Kč +(\d+)%", text)
    inv = Invoice(number, "payout", None, None, float(rate[1]) if rate else 0.0, None, items)
    inv.base = inv.items_total
    return _finish(inv)


def _finish(inv: Invoice) -> Invoice:
    if inv.items:
        inv.period_from = min(i.date_from for i in inv.items)
        inv.period_to = max(i.date_to for i in inv.items)
    return inv


_CORRECTIVE = re.compile(r"\bOPRAVN(É|Á|Ý)\b|OPRAVNÝ DAŇOVÝ DOKLAD|Opravná faktura", re.IGNORECASE)


def is_corrective_text(text: str) -> bool:
    """Corrective settlement: the heading says "OPRAVNÉ" instead of "ŘÁDNÉ"."""
    return bool(_CORRECTIVE.search(_SPACE.sub(" ", text[:1500])))


def is_corrective_type(type_text: str | None) -> bool:
    """Portal document type text ("Opravná faktura - přeplatek", ...)."""
    return "oprav" in (type_text or "").lower()


def is_payout_text(text: str) -> bool:
    return "VYSTAVENO ZÁKAZNÍKEM" in text or "DETAILNÍ ROZPIS" in text


# --- corrective and overlapping settlements ------------------------------------------


def _is_difference(inv: Invoice) -> bool:
    """Corrective invoice billing only the difference: it reverses the original items
    (negative quantities), so it adds to the original instead of replacing it."""
    return any(i.quantity < 0 and i.amount <= 0 for i in inv.items if i.kind != "discount")


def _cut(item: InvoiceItem, start: date, end: date) -> list[InvoiceItem]:
    """Parts of an item outside start..end, amounts by the share of days (months for fees)."""
    if item.date_to < start or item.date_from > end:
        return [item]
    keep = []
    if item.date_from < start:
        keep.append((item.date_from, start - timedelta(days=1)))
    if item.date_to > end:
        keep.append((end + timedelta(days=1), item.date_to))

    def weight(a: date, b: date) -> float:
        if item.fixed:
            return sum(_month_share(x, y) for x, y in _month_parts(a, b))
        return float(_days(a, b))

    total = weight(item.date_from, item.date_to) or 1.0
    out = []
    for a, b in keep:
        share = weight(a, b) / total
        out.append(
            InvoiceItem(
                item.name,
                item.kind,
                item.group,
                a,
                b,
                round(item.quantity * share, 6),
                item.unit,
                item.unit_price,
                round(item.amount * share, 2),
                True,
            )
        )
    return out


def resolve_overlaps(invoices: list[Invoice]) -> tuple[list[Invoice], dict[str, str]]:
    """Settlements valid for the breakdown and {replaced number: replacing number}.

    A later document (issue date, then period end) is authoritative for the days it
    covers: items of earlier documents on those days are dropped (cut by days at the
    edges). A difference-type corrective invoice (reversal lines with negative
    quantities) is added to the original instead. Consumption and payout documents
    are resolved separately.
    """
    order = sorted(
        invoices,
        key=lambda i: (i.issued or i.period_to or date.min, i.period_to or date.min, i.number),
    )
    result: list[Invoice] = []
    replaced: dict[str, str] = {}
    for inv in order:
        if inv.period_from and inv.period_to and not _is_difference(inv):
            kept = []
            for old in result:
                if (
                    (old.source == "payout") != (inv.source == "payout")
                    or not old.period_from
                    or not old.period_to
                    or old.period_to < inv.period_from
                    or old.period_from > inv.period_to
                ):
                    kept.append(old)
                    continue
                items = [p for i in old.items for p in _cut(i, inv.period_from, inv.period_to)]
                replaced[old.number] = inv.number
                if items:
                    kept.append(
                        Invoice(
                            old.number,
                            old.source,
                            min(i.date_from for i in items),
                            max(i.date_to for i in items),
                            old.vat_rate,
                            old.base,
                            items,
                            old.issued,
                            old.corrective,
                        )
                    )
            result = kept
        result.append(inv)
    return result, replaced


# --- splitting into calendar months -------------------------------------------------


def _month_start(day: date) -> date:
    return day.replace(day=1)


def _month_end(day: date) -> date:
    return day.replace(day=calendar.monthrange(day.year, day.month)[1])


def _month_parts(start: date, end: date) -> list[tuple[date, date]]:
    parts, cur = [], start
    while cur <= end:
        last = min(_month_end(cur), end)
        parts.append((cur, last))
        cur = last + timedelta(days=1)
    return parts


def _days(a: date, b: date) -> int:
    return (b - a).days + 1


def _month_share(start: date, end: date) -> float:
    """Months of a period within one month (days / days of the month)."""
    return round(_days(start, end) / _days(_month_start(start), _month_end(start)), 6)


def split_item(item: InvoiceItem, weights: dict[date, float] | None = None) -> list[dict[str, Any]]:
    """Split an item into calendar months.

    Monthly charges: by the share of each month's days (the provider counts months
    the same way, e.g. 26. 2. - 15. 7. = 4.591 months). Consumption charges: by
    `weights` (energy per month start) when available, else by days. Parts of a
    multi-month item are marked `estimated` (allocated here, not by the provider).
    """
    parts = _month_parts(item.date_from, item.date_to)
    if len(parts) == 1:
        return [
            {
                "month": _month_start(item.date_from),
                "quantity": item.quantity,
                "amount": item.amount,
                "estimated": item.estimated,
            }
        ]
    if item.fixed:
        shares = [_days(a, b) / _days(_month_start(a), _month_end(a)) for a, b in parts]
    else:
        shares = []
        for a, b in parts:
            w = (weights or {}).get(_month_start(a))
            month_days = _days(_month_start(a), _month_end(a))
            shares.append((w * _days(a, b) / month_days) if w is not None else float(_days(a, b)))
        if weights and any((weights or {}).get(_month_start(a)) is None for a, _ in parts):
            shares = [float(_days(a, b)) for a, b in parts]  # incomplete weights: by days
    total = sum(shares) or 1.0
    out, amount_left, qty_left = [], item.amount, item.quantity
    for idx, ((a, _b), share) in enumerate(zip(parts, shares, strict=True)):
        if idx == len(parts) - 1:
            amount, qty = round(amount_left, 2), round(qty_left, 6)
        else:
            amount = round(item.amount * share / total, 2)
            qty = round(item.quantity * share / total, 6)
            amount_left -= amount
            qty_left -= qty
        out.append({"month": _month_start(a), "quantity": qty, "amount": amount, "estimated": True})
    return out


def monthly_breakdown(
    invoices: list[Invoice], weights: dict[date, float] | None = None
) -> dict[str, dict[str, dict[str, Any]]]:
    """{ "YYYY-MM": { kind: {group, name, unit, quantity, amount, vat, unit_price, estimated, sources} } }.

    `vat` is the VAT of the amount at the invoice rate. Overlapping invoices (a
    corrective one replacing another) are not deduplicated here; pass the valid ones.
    """
    months: dict[str, dict[str, dict[str, Any]]] = {}
    for inv in invoices:
        for item in inv.items:
            for part in split_item(item, weights):
                key = part["month"].strftime("%Y-%m")
                row = months.setdefault(key, {}).setdefault(
                    item.kind,
                    {
                        "group": item.group,
                        "name": item.name,
                        "unit": item.unit,
                        "quantity": 0.0,
                        "amount": 0.0,
                        "vat": 0.0,
                        "prices": [],
                        "estimated": False,
                        "invoices": [],
                    },
                )
                row["quantity"] = round(row["quantity"] + part["quantity"], 6)
                row["amount"] = round(row["amount"] + part["amount"], 2)
                row["vat"] = round(row["vat"] + part["amount"] * inv.vat_rate / 100, 2)
                row["estimated"] = row["estimated"] or part["estimated"]
                if item.unit_price is not None and item.unit_price not in row["prices"]:
                    row["prices"].append(item.unit_price)
                if inv.number not in row["invoices"]:
                    row["invoices"].append(inv.number)
    return dict(sorted(months.items()))


def unit_prices_at(invoices: list[Invoice], day: date) -> dict[str, InvoiceItem]:
    """Unit prices of the last price period invoiced on or before `day`.

    Only items ending on the last invoiced day count, so charges that were abolished
    earlier (e.g. "Činnost OTE") are not carried over.
    """
    items = [
        i for inv in invoices for i in inv.items if i.unit_price is not None and i.date_from <= day
    ]
    if not items:
        return {}
    last = max(i.date_to for i in items)
    return {i.kind: i for i in sorted(items, key=lambda i: i.date_from) if i.date_to == last}


# --- current period: simulation items split with the latest unit prices -------------

# Components of the simulation items by item kind (first present wins in a tuple).
_SIM_PARTS: dict[str, list[tuple[str, ...]]] = {
    "vt": [
        ("energy_vt", "energy"),
        ("electricity_tax",),
        ("distribution_vt",),
        ("system_services",),
        ("poze",),
        ("market_operator",),
    ],
    "nt": [
        ("energy_nt", "energy"),
        ("electricity_tax",),
        ("distribution_nt",),
        ("system_services",),
        ("poze",),
        ("market_operator",),
    ],
    "fixed": [
        ("supplier_fixed",),
        ("breaker",),
        ("infrastructure",),
        ("poze",),
        ("market_operator",),
    ],
}


def simulation_parts(
    item: Any,
    prices: dict[str, InvoiceItem],
    table: dict[str, list[tuple[str, ...]]] | None = None,
) -> tuple[list[dict[str, Any]], bool]:
    """Split one simulation item (vt / nt / fixed) into invoice item kinds.

    The simulation gives one amount per item; it is divided in the ratio of the unit
    prices of the latest invoice (energy items: per MWh, fixed: per month). Returns
    (parts, matched): matched when the unit prices explain the simulated amount
    within 1 % (energy) / 1 CZK per month (fixed), i.e. the prices did not change.
    """
    want_unit = UNIT_MONTH if item.kind == "fixed" else UNIT_MWH
    chosen: list[InvoiceItem] = []
    for alternatives in (table or _SIM_PARTS).get(item.kind, []):
        for kind in alternatives:
            p = prices.get(kind)
            if p is not None and p.unit == want_unit and p.unit_price:
                chosen.append(p)
                break
    total_price = sum(p.unit_price or 0.0 for p in chosen)
    if not chosen or total_price <= 0:
        return [], False
    if item.kind == "fixed":
        start, end = item.date_from, item.date_to
        months = _month_share(start, end)
        matched = abs(total_price * months - item.amount) <= max(1.0, months)
        quantity = round(months, 6)
    else:
        # The simulation rounds quantities to 0.001 MWh: allow that error as well.
        allowed = max(0.01 * item.amount, total_price * 0.0005) + 0.5
        matched = item.mwh > 0 and abs(total_price * item.mwh - item.amount) <= allowed
        quantity = item.mwh
    parts, left = [], item.amount
    for idx, p in enumerate(chosen):
        amount = (
            round(left, 2)
            if idx == len(chosen) - 1
            else round(item.amount * (p.unit_price or 0) / total_price, 2)
        )
        left -= amount
        parts.append(
            {
                "kind": p.kind,
                "group": p.group,
                "name": p.name,
                "unit": p.unit,
                "quantity": quantity,
                "amount": amount,
                "unit_price": p.unit_price,
            }
        )
    return parts, matched


SIM_NAMES = {
    "vt": "Spotřeba VT (souhrn ze simulace)",
    "nt": "Spotřeba NT (souhrn ze simulace)",
    "fixed": "Stálé platby (souhrn ze simulace)",
}


def build_report(
    invoices: list[Invoice],
    sim_items: list[Any] | None = None,
    measured_until: date | None = None,
    weights: dict[date, float] | None = None,
    price_sources: Any = None,
    sim_parts: dict[str, list[tuple[str, ...]]] | None = None,
    sim_names: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Price breakdown per calendar month for the dashboard.

    History from invoices (provider's items, multi-month items split here), the current
    billing period from the simulation (after the last invoiced day), split with the
    latest invoice unit prices (components per simulation item kind from `sim_parts`,
    electricity by default; gas passes invoice_gas.SIM_PARTS). Month flags: source invoice / simulation / mixed,
    predicted (after the last meter reading of the simulation).
    """
    valid, replaced = resolve_overlaps(invoices)
    consumption = [i for i in valid if i.source != "payout"]
    months = monthly_breakdown(consumption, weights)
    meta = {m: {"source": "invoice", "predicted": False, "matched": True} for m in months}
    last = max((i.period_to for i in consumption if i.period_to), default=None)
    vat_rate = next(
        (
            i.vat_rate
            for i in sorted(consumption, key=lambda x: x.period_to or date.min, reverse=True)
        ),
        21.0,
    )
    pending = [i for i in sim_items or [] if not (last and i.date_to <= last)]
    by_month: dict[str, list[Any]] = {}
    for item in pending:
        by_month.setdefault(item.date_from.strftime("%Y-%m"), []).append(item)
    chosen_parts: dict[int, tuple[list[dict[str, Any]], bool, str | None]] = {}
    for items in by_month.values():
        day = min(i.date_from for i in items)
        prices = unit_prices_at(consumption, day)
        candidates = [("invoice", prices)]
        if price_sources is not None:  # e.g. product price lists for a new price year
            candidates += price_sources(day, prices)
        # One price source for the whole month when it explains every item.
        for name, cand in candidates:
            results = [simulation_parts(i, cand, sim_parts) for i in items]
            if all(ok for _, ok in results):
                for i, (parts, _ok) in zip(items, results, strict=True):
                    chosen_parts[id(i)] = (parts, True, name)
                break
        else:  # item by item: first source that explains it
            for i in items:
                chosen_parts[id(i)] = ([], False, None)
                for name, cand in candidates:
                    parts, ok = simulation_parts(i, cand, sim_parts)
                    if ok:
                        chosen_parts[id(i)] = (parts, True, name)
                        break
    for item in pending:
        parts, matched, source = chosen_parts[id(item)]
        key = item.date_from.strftime("%Y-%m")
        m = meta.setdefault(key, {"source": "simulation", "predicted": False, "matched": True})
        if m["source"] == "invoice":
            m["source"] = "mixed"
        m["matched"] = m["matched"] and matched
        if source:
            m.setdefault("prices", [])
            if source not in m["prices"]:
                m["prices"].append(source)
        if measured_until and item.date_to > measured_until:
            m["predicted"] = True
        rows = months.setdefault(key, {})
        if not parts:  # keep the simulation item as it is
            parts = [
                {
                    "kind": f"sim_{item.kind}",
                    "group": "simulation",
                    "name": (sim_names or SIM_NAMES).get(item.kind, item.kind),
                    "unit": UNIT_MONTH if item.kind == "fixed" else UNIT_MWH,
                    "quantity": _month_share(item.date_from, item.date_to)
                    if item.kind == "fixed"
                    else item.mwh,
                    "amount": item.amount,
                    "unit_price": None,
                }
            ]
        for part in parts:
            row = rows.setdefault(
                part["kind"],
                {
                    "group": part["group"],
                    "name": part["name"],
                    "unit": part["unit"],
                    "quantity": 0.0,
                    "amount": 0.0,
                    "vat": 0.0,
                    "prices": [],
                    "estimated": False,
                    "invoices": [],
                },
            )
            row["quantity"] = round(row["quantity"] + part["quantity"], 6)
            row["amount"] = round(row["amount"] + part["amount"], 2)
            row["vat"] = round(row["vat"] + part["amount"] * vat_rate / 100, 2)
            if part["unit_price"] is not None and part["unit_price"] not in row["prices"]:
                row["prices"].append(part["unit_price"])
    payout = monthly_breakdown([i for i in valid if i.source == "payout"])
    return {
        "vat_rate": vat_rate,
        "months": [
            {
                "month": key,
                **meta.get(key, {}),
                "items": [{"kind": k, **v} for k, v in rows.items()],
            }
            for key, rows in sorted(months.items())
        ],
        "payout": [
            {"month": key, "items": [{"kind": k, **v} for k, v in rows.items()]}
            for key, rows in sorted(payout.items())
        ],
        "invoices": [
            {
                "number": i.number,
                "source": i.source,
                "period_from": i.period_from.isoformat() if i.period_from else None,
                "period_to": i.period_to.isoformat() if i.period_to else None,
                "base": i.base,
                "vat_rate": i.vat_rate,
                "issued": i.issued.isoformat() if i.issued else None,
                "corrective": i.corrective,
                "replaced_by": replaced.get(i.number),
                "partial": replaced.get(i.number) is not None
                and any(v.number == i.number for v in valid),
            }
            for i in sorted(invoices, key=lambda x: x.period_to or date.min, reverse=True)
        ],
    }


def weights_from_readings(points: list[Any]) -> dict[date, float]:
    """kWh per month (month start) from meter readings, spread evenly between readings.

    Only months fully covered by reading intervals are returned. Points need
    `reading_date`, `value` and `device` (a meter change starts a new series).
    """
    daily: dict[date, float] = {}
    series: dict[Any, list[Any]] = {}
    for p in points:
        series.setdefault(getattr(p, "device", None), []).append(p)
    for pts in series.values():
        pts = sorted(pts, key=lambda p: p.reading_date)
        for a, b in zip(pts, pts[1:], strict=False):
            days = (b.reading_date - a.reading_date).days
            delta = b.value - a.value
            if days <= 0 or delta < 0:
                continue
            for i in range(1, days + 1):
                d = a.reading_date + timedelta(days=i)
                daily[d] = daily.get(d, 0.0) + delta / days
    out: dict[date, float] = {}
    for d, v in daily.items():
        out[_month_start(d)] = out.get(_month_start(d), 0.0) + v
    return {
        m: round(v, 3)
        for m, v in out.items()
        if all(m + timedelta(days=i) in daily for i in range(_days(m, _month_end(m))))
    }
