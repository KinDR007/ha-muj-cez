"""Capture raw Muj CEZ API responses once for offline development.

Usage: CEZ_USER=... CEZ_PASS=... [CEZ_SNAPSHOT_DIR=.snapshot/<name>] .venv/bin/python tools/snapshot.py
Writes .snapshot/cez/<n>.json and manifest.json (git-ignored, contains personal data).

The live client is wrapped so every `_get` call made by `fetch_all` is recorded,
plus invoice details of the active contracts (used for paid amounts per period).
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import UTC, date, datetime
from typing import Any

import aiohttp
from offline import SNAPSHOT_DIR, api, request_key


class RecordingClient(api.CezClient):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.records: dict[str, tuple[int, Any]] = {}

    async def _get(self, path: str, params: dict[str, str] | None = None) -> Any:
        key = request_key(path, params)
        try:
            data = await super()._get(path, params)
        except api.CezConnectionError as err:
            status = int(str(err).split("HTTP ")[1].split()[0]) if "HTTP " in str(err) else 0
            self.records[key] = (status, None)
            raise
        self.records[key] = (200, data)
        return data


async def main() -> int:
    user, pwd = os.environ.get("CEZ_USER"), os.environ.get("CEZ_PASS")
    if not user or not pwd:
        print("Set CEZ_USER and CEZ_PASS", file=sys.stderr)
        return 2
    async with aiohttp.ClientSession() as session:
        client = RecordingClient(session, user, pwd)
        try:
            await client.authenticate()
            data = await client.fetch_all(date.today(), {})
            active = {spd.supply_point.agreement_id for spd in data.supply_points.values()}
            billings = client.records.get(request_key("/billings", {"includeNotPayed": "true"}))
            for row in (billings[1] if billings else None) or []:
                number = row.get("billingReceivablesAndPayablesAccountDocumentNumber")
                if (
                    row.get("agreementIdIsu") in active
                    and str(row.get("billingAccountingDocumentTypeText", "")).startswith("Faktura")
                    and number
                ):
                    try:
                        await client._get(
                            "/interactive-invoicing/invoice-detail",
                            {
                                "agreementIdIsu": row["agreementIdIsu"],
                                "billingReceivablesAndPayablesAccountDocumentNumber": number,
                            },
                        )
                    except api.CezError as err:
                        print(f"invoice detail {number}: {err}", file=sys.stderr)
        except api.CezError as err:
            print(f"ERROR: {err}", file=sys.stderr)
            return 1

    # Replace only files of a previous capture; keep other content (e.g. subdirectories).
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    for old in SNAPSHOT_DIR.glob("*.json"):
        old.unlink()
    manifest: dict[str, Any] = {
        "captured_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "requests": {},
    }
    for i, (key, (status, payload)) in enumerate(sorted(client.records.items())):
        file = None
        if payload is not None:
            file = f"{i:03d}.json"
            (SNAPSHOT_DIR / file).write_text(json.dumps(payload, ensure_ascii=False, indent=1))
        manifest["requests"][key] = {"status": status, "file": file}
    (SNAPSHOT_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1))
    print(f"Saved {len(client.records)} responses to {SNAPSHOT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
