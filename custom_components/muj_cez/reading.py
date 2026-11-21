"""Customer meter reading (samoodečet): validation of the entered values.

Pure functions without Home Assistant imports. The same checks as the portal form
(col-fe, chunk with the self reading form): the value is a whole number of kWh (at most
9 digits), not lower than the previous reading (for ČEZ Distribuce an error that blocks
saving), not unusually high (warning only), one reading of a limited type per day and
control readings only while the yearly limit allows. See docs/api/self-meter-reading.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

NOTE_MAX = 160
VALUE_MAX = 999_999_999  # 9 digits
REGISTERS = ("vt", "nt")

# Reading types (selfMeterReadingReason.entryId), in the portal's order.
REASONS = {"control": "02", "diary": "08", "extraordinary": "01", "info": "14"}
TYPES = tuple(REASONS)
# Types passed to the distributor (the diary reading stays in the portal).
DISTRIBUTOR_TYPES = ("control", "extraordinary", "info")
# Only one reading of these reasons per day (01, 02, 13, 14, 15-18); not rejected (4) or
# cancelled (C) ones count.
LIMITED_REASONS = {"01", "02", "13", "14", "15", "16", "17", "18"}
INACTIVE_STATUSES = {"4", "C"}

# "Unusually high": value > previous + kWh per day x days x HIGH_FACTOR (portal rule; it
# uses the consumption of the last billing period, here also the readings as a fallback).
HIGH_FACTOR = 1.5


@dataclass
class Previous:
    """Last known reading of one register."""

    day: date
    value: float


@dataclass
class Issue:
    # required, integer, negative, too_long, lower, high, date_future, date_before,
    # note_long, type, duplicate_day, no_remaining, date_range
    code: str
    field: str  # vt, nt, date, note, type
    params: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code, "field": self.field, "params": self.params}


@dataclass
class Check:
    errors: list[Issue] = field(default_factory=list)
    warnings: list[Issue] = field(default_factory=list)
    # Consumption since the previous reading per register: {"vt": {"kwh": .., "days": ..}}
    delta: dict[str, dict[str, Any]] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "errors": [i.as_dict() for i in self.errors],
            "warnings": [i.as_dict() for i in self.warnings],
            "delta": self.delta,
        }


def parse_value(raw: Any) -> int | None:
    """Whole kWh from user input ("12 345", 12345, "12345.0"); None when not a whole number."""
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return raw
    if isinstance(raw, float):
        return int(raw) if raw.is_integer() else None
    text = str(raw).replace("\xa0", "").replace(" ", "").strip()
    if text.endswith((".0", ",0")):
        text = text[:-2]
    return int(text) if text.lstrip("-").isdigit() else None


def daily_usage(points: list[tuple[date, float]], until: date, days: int = 365) -> float | None:
    """Average kWh per day between the readings of the last `days` before `until`."""
    usable = sorted((d, v) for d, v in points if d <= until)
    if len(usable) < 2:
        return None
    recent = [(d, v) for d, v in usable if (until - d).days <= days]
    start = recent[0] if len(recent) >= 2 else usable[-2]
    end = usable[-1]
    span = (end[0] - start[0]).days
    if span <= 0 or end[1] < start[1]:
        return None
    return (end[1] - start[1]) / span


def check(
    values: dict[str, Any],
    registers: list[str],
    previous: dict[str, Previous],
    usage: dict[str, float | None],
    day: date | None,
    today: date,
    note: str = "",
    reading_type: str | None = None,
    taken_days: set[date] | None = None,
    remaining: dict[str, int] | None = None,
    date_range: tuple[date, date] | None = None,
) -> Check:
    """Validate a reading of the given registers ("vt", optionally "nt").

    `previous` holds the last reading per register, `usage` the usual kWh per day,
    `taken_days` the days with an active reading of a limited reason, `remaining`
    the readings left this year per reason code and `date_range` the dates the portal
    allows for the reading type.
    """
    result = Check()
    reason = REASONS.get(reading_type or "diary")
    if reason is None:
        result.errors.append(Issue("type", "type"))
    elif reason == REASONS["control"] and remaining and remaining.get(reason, 1) < 1:
        result.errors.append(Issue("no_remaining", "type"))
    if reason in LIMITED_REASONS and day is not None and day in (taken_days or set()):
        result.errors.append(Issue("duplicate_day", "date", {"date": day.isoformat()}))
    if day is None:
        result.errors.append(Issue("required", "date"))
    elif day > today:
        result.errors.append(Issue("date_future", "date"))
    elif date_range and not date_range[0] <= day <= date_range[1]:
        params = {"min": date_range[0].isoformat(), "max": date_range[1].isoformat()}
        result.errors.append(Issue("date_range", "date", params))
    else:
        last = max((p.day for p in previous.values()), default=None)
        if last and day < last:
            result.errors.append(Issue("date_before", "date", {"date": last.isoformat()}))
    if len(note or "") > NOTE_MAX:
        result.errors.append(Issue("note_long", "note", {"max": NOTE_MAX}))
    for reg in registers:
        raw = values.get(reg)
        if raw is None or str(raw).strip() == "":
            result.errors.append(Issue("required", reg))
            continue
        value = parse_value(raw)
        if value is None:
            result.errors.append(Issue("integer", reg))
            continue
        if value < 0:
            result.errors.append(Issue("negative", reg))
            continue
        if value > VALUE_MAX:
            result.errors.append(Issue("too_long", reg))
            continue
        prev = previous.get(reg)
        if prev is None:
            continue
        if value < prev.value:
            params = {"date": prev.day.isoformat(), "value": prev.value}
            result.errors.append(Issue("lower", reg, params))
            continue
        days = ((day or today) - prev.day).days
        kwh = value - prev.value
        result.delta[reg] = {"kwh": kwh, "days": days, "per_day": round(kwh / max(days, 1), 1)}
        limit = (usage.get(reg) or 0.0) * days * HIGH_FACTOR
        if limit and kwh > limit:  # portal: no warning without usage or on the same day
            result.warnings.append(Issue("high", reg, {"limit": round(prev.value + limit)}))
    return result


def build_request(
    ean: str,
    device: str | None,
    reading_type: str,
    day: date,
    vt: int,
    nt: int | None,
    note: str,
) -> dict[str, Any]:
    """JSON part `selfMeterReadingRequestBody` of POST /self-meter-reading, as the portal
    builds it (submitSelfMeterReadingData). NT is 0 on a single tariff meter."""
    return {
        "selfMeterReadingGuidIsu": "",
        "selfMeterReadingLowTariff": {
            "meterReadingUnit": {"entryId": ""},
            "meterReadingTariff": {
                "entrySystemSpecificId": "",
                "systemId": "",
                "entryId": "lowTariff",
            },
            "meterReadingValue": nt or 0,
            "meterReadingDocumentId": "",
        },
        "selfMeterReadingHighTariff": {
            "meterReadingUnit": {"entryId": ""},
            "meterReadingTariff": {"entryId": "highTariff"},
            "meterReadingValue": vt,
            "meterReadingDocumentId": "",
        },
        "selfMeterReadingReason": {"entryId": REASONS[reading_type]},
        "meterReadingRegisterDate": day.isoformat(),
        "meterReadingDeviceNumber": device or "",
        "supplyPointCode": ean,
        "selfMeterReadingDescription": note,
        "checkSnaps": True,
        "selfMeterReadingStatus": {"entryId": "", "systemId": "", "entrySystemSpecificId": ""},
    }


def parse_consumption_vals(data: Any) -> tuple[dict[str, float], dict[str, int]]:
    """kWh per day of the last billing period per register and the readings left this year
    per reason code, from GET /meter-reading-consumption-vals."""
    if not isinstance(data, dict):
        return {}, {}
    usage: dict[str, float] = {}
    period = data.get("LastBillPeriod") or data.get("lastBillPeriod")
    for reg, key in (("vt", "lastConsVT"), ("nt", "lastConsNT")):
        value = data.get(key)
        if isinstance(value, int | float) and isinstance(period, int | float) and period > 0:
            usage[reg] = value / period
    remaining: dict[str, int] = {}
    for item in data.get("Limits") or data.get("limits") or []:
        if not isinstance(item, dict) or item.get("period") != "YEAR":
            continue
        top, used = item.get("limitMax"), item.get("limitActual")
        if item.get("smrType") and isinstance(top, int | float) and isinstance(used, int | float):
            remaining[str(item["smrType"])] = int(top - used)
    return usage, remaining


def parse_types(rows: Any) -> list[str] | None:
    """Offered reading types (our keys, portal order) from /meter-reading-requests-advanced;
    None when unknown (then all are offered)."""
    if not isinstance(rows, list):
        return None
    codes = {
        str(r.get("meterReadingReasonId"))
        for r in rows
        if isinstance(r, dict) and r.get("meterReadingReasonEnabled")
    }
    return [key for key, code in REASONS.items() if code in codes]


def parse_date_range(data: Any) -> tuple[date, date] | None:
    """(min, max) reading date from /self-meter-reading/form-config."""
    if not isinstance(data, dict):
        return None
    try:
        return (
            date.fromisoformat(str(data["meterReadingMinDate"])[:10]),
            date.fromisoformat(str(data["meterReadingMaxDate"])[:10]),
        )
    except (KeyError, ValueError):
        return None


def taken_days(rows: Any) -> set[date]:
    """Days with an active reading of a limited reason, from GET /self-meter-reading."""
    out: set[date] = set()
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        reason = str(row.get("selfMeterReadingReasonId") or "")
        status = str(row.get("selfMeterReadingStatusId") or "")
        raw = str(row.get("meterReadingRequestRegisterDate") or "")[:10]
        if reason in LIMITED_REASONS and status not in INACTIVE_STATUSES and raw:
            try:
                out.add(date.fromisoformat(raw))
            except ValueError:
                continue
    return out
