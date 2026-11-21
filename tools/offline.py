"""Offline replay of Muj CEZ API responses captured by tools/snapshot.py.

Use OfflineCezClient instead of CezClient during development so the portal is not
queried repeatedly. Requests not present in the snapshot raise CezConnectionError,
which the integration handles like a failed endpoint.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = Path(os.environ.get("CEZ_SNAPSHOT_DIR") or ROOT / ".snapshot" / "cez")


def load_api() -> Any:
    """Import the integration's api module (needs the dev venv with Home Assistant)."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from custom_components.muj_cez import api as module

    return module


def load_ha_daily(statistic_id: str = "sensor.ac_main_power_import") -> dict:
    """Daily kWh from .snapshot/ha (captured by ha_stats_snapshot.py), local dates."""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    tz = ZoneInfo("Europe/Prague")
    path = ROOT / ".snapshot" / "ha" / f"{statistic_id}_day.json"
    rows = json.loads(path.read_text())["rows"]
    return {
        datetime.fromtimestamp(r["start"] / 1000, tz).date(): r["change"]
        for r in rows
        if r.get("change") is not None
    }


def request_key(path: str, params: dict[str, str] | None) -> str:
    query = "&".join(f"{k}={v}" for k, v in sorted((params or {}).items()))
    return f"{path}?{query}" if query else path


api = load_api()


class OfflineCezClient(api.CezClient):
    """CezClient serving `_get` from a snapshot directory."""

    def __init__(self, snapshot_dir: Path = SNAPSHOT_DIR) -> None:
        super().__init__(None, "offline", "offline")  # type: ignore[arg-type]
        manifest = snapshot_dir / "manifest.json"
        if not manifest.exists():
            raise FileNotFoundError(f"No snapshot at {snapshot_dir}; run tools/snapshot.py first")
        self._dir = snapshot_dir
        content = json.loads(manifest.read_text())
        self._manifest: dict[str, dict[str, Any]] = content["requests"]
        self.requests: list[str] = []
        # Local date of the capture: requests with date ranges only match for this day.
        self.captured_on = None
        if content.get("captured_at"):
            from datetime import datetime
            from zoneinfo import ZoneInfo

            captured = datetime.fromisoformat(content["captured_at"])
            self.captured_on = captured.astimezone(ZoneInfo("Europe/Prague")).date()

    async def authenticate(self) -> None:
        return None

    async def _get(self, path: str, params: dict[str, str] | None = None) -> Any:
        key = request_key(path, params)
        self.requests.append(key)
        entry = self._manifest.get(key)
        if entry is None:
            raise api.CezConnectionError(f"Not in snapshot: {key}")
        if entry["status"] != 200:
            raise api.CezConnectionError(f"GET {path}: HTTP {entry['status']} (snapshot)")
        if entry["file"] is None:
            return None
        return json.loads((self._dir / entry["file"]).read_text())

    # Invoices captured by tools/probe/probe_documents.py into <snapshot>/docs/.
    def _doc(self, row: dict[str, Any], suffix: str) -> Path | None:
        path = (
            self._dir
            / "docs"
            / (row["billingReceivablesAndPayablesAccountDocumentNumber"] + suffix)
        )
        return path if path.exists() else None

    async def get_invoice_rows(self, since: Any) -> list[dict[str, Any]]:
        path = self._dir / "docs" / "billings_extended.json"
        if not path.exists():
            raise api.CezConnectionError("Not in snapshot: billings/extended")
        rows = json.loads(path.read_text())
        return [r for r in rows if r.get("billingAccountingDocumentType2") in api.INVOICE_TYPES]

    async def get_invoice_csv(self, row: dict[str, Any]) -> str | None:
        path = self._doc(row, "_csv.bin")
        return path.read_text(encoding="utf-8-sig") if path else None

    async def get_invoice_pdf(self, row: dict[str, Any]) -> bytes | None:
        path = self._doc(row, "_pdf0.pdf")
        return path.read_bytes() if path else None

    async def get_price_lists(self, sp: Any) -> list[dict[str, Any]]:
        return [
            {"doc_id": path.stem, "guid": str(path), "name": path.stem, "valid_from": None}
            for path in sorted((self._dir / "docs").glob(f"cenik_{sp.ean}_*.pdf"))
        ]

    @staticmethod
    def _read(path: str) -> bytes | None:
        file = Path(path)
        return file.read_bytes() if file.exists() else None

    async def get_document_pdf(self, guid: str) -> bytes | None:
        return self._read(guid)  # offline: guid is the local file
