"""Pseudonymize raw portal responses for diagnostics shared in issue reports.

Values of personal keys (names, addresses, contacts, ids and numbers of partners,
contracts, supply points, documents, accounts) and every run of 6+ digits anywhere
are replaced by stable placeholders: the same original value gets the same
placeholder in all responses, so relations between them (which supply point belongs
to which account) stay visible. Dates, amounts, kWh and codebook values are kept.
"""

from __future__ import annotations

import re
from typing import Any

# Key fragments (lower case) whose values are personal.
SENSITIVE = (
    "ean",
    "uid",
    "partner",
    "name",
    "address",
    "street",
    "city",
    "town",
    "municipal",
    "district",
    "zip",
    "postal",
    "house",
    "email",
    "mail",
    "phone",
    "birth",
    "iban",
    "account",
    "agreement",
    "contract",
    "variable",
    "document",
    "number",
    "device",
    "idisu",
    "idcrm",
    "idcol",
    "ppjm",
    "hash",
    "token",
    "user",
)
# Keys matching a fragment above that are not personal.
ALLOWED = {"rolename", "productname"}
_DIGITS = re.compile(r"\d{6,}")


class Anonymizer:
    def __init__(self) -> None:
        self._values: dict[str, str] = {}
        self._digits: dict[str, str] = {}

    def _value(self, value: str) -> str:
        if value not in self._values:
            self._values[value] = f"anon_{len(self._values) + 1}"
        return self._values[value]

    def _number(self, match: re.Match[str]) -> str:
        """Same length, starts with 9 (does not look like a real EAN / account)."""
        found = match.group(0)
        if found not in self._digits:
            n = str(len(self._digits) + 1)
            self._digits[found] = ("9" + n.rjust(len(found) - 1, "0"))[-len(found) :]
        return self._digits[found]

    def _text(self, text: str) -> str:
        return _DIGITS.sub(self._number, text)

    def __call__(self, data: Any, key: str = "", inherited: bool = False) -> Any:
        """inherited: under a personal key (e.g. addressCity: {"value": ...})."""
        lower = key.lower()
        sensitive = inherited or (lower not in ALLOWED and any(part in lower for part in SENSITIVE))
        if isinstance(data, dict):
            return {
                self._text(str(k)): self(v, str(k), sensitive and k != "@class")
                for k, v in data.items()
            }
        if isinstance(data, list):
            return [self(v, key, inherited) for v in data]
        if isinstance(data, bool) or data is None:
            return data
        if sensitive and isinstance(data, str | int | float):
            return (
                self._value(str(data))
                if not _DIGITS.fullmatch(str(data))
                else self._text(str(data))
            )
        if isinstance(data, str):
            return self._text(data)
        return data
