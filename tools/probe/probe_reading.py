"""One-off capture of the self meter reading endpoints (read only, nothing is sent).

Usage: CEZ_USER=... CEZ_PASS=... CEZ_SNAPSHOT_DIR=.snapshot/<name> \
  .venv/bin/python tools/probe/probe_reading.py

For every consumption point (electricity and gas) saves to <CEZ_SNAPSHOT_DIR>/reading/ (git-ignored,
personal data): the readings with reason and status, consumption of the last billing
period with the yearly limits, the selectable reading types and the date range per type.
Used to verify meter_reading.py against real responses before turning sending on.
See docs/api/self-meter-reading.md.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

import aiohttp

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from offline import SNAPSHOT_DIR, api  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from custom_components.muj_cez import reading  # noqa: E402

OUT = SNAPSHOT_DIR / "reading"


async def get(client: api.CezClient, path: str, params: dict[str, str]) -> tuple[int, Any]:
    await client._ensure_token()
    async with client._session.get(
        f"{client._api_url}{path}",
        params=params,
        headers={
            "User-Agent": api.USER_AGENT,
            "Accept": "application/json",
            "Authorization": f"Bearer {client._access_token}",
            **({api.PARTNER_HEADER: client.partner} if client.partner else {}),
        },
        timeout=api.TIMEOUT,
    ) as resp:
        text = await resp.text()
        try:
            return resp.status, json.loads(text) if text else None
        except ValueError:
            return resp.status, text[:500]


async def main() -> int:
    user, pwd = os.environ.get("CEZ_USER"), os.environ.get("CEZ_PASS")
    if not user or not pwd:
        print("Set CEZ_USER and CEZ_PASS", file=sys.stderr)
        return 2
    OUT.mkdir(parents=True, exist_ok=True)
    async with aiohttp.ClientSession() as session:
        client = api.CezClient(session, user, pwd)
        await client.authenticate()
        points = [
            sp
            for sp in await client.get_supply_points()
            if not sp.production and sp.commodity.startswith(("E", "P"))
        ]
        for sp in points:
            print(f"{sp.name} ({sp.ean[-6:]})")
            calls = {
                "self_readings": ("/self-meter-reading", {"supplyPointCode": sp.ean}),
                "consumption_vals": (
                    "/meter-reading-consumption-vals",
                    {"supplyPointCode": sp.ean},
                ),
                "requests_advanced": (
                    "/meter-reading-requests-advanced",
                    {"supplyPointCode": sp.ean},
                ),
                **{
                    f"form_config_{code}": (
                        "/self-meter-reading/form-config",
                        {
                            "meterReadingReasonId": code,
                            "supplyPointCode": sp.ean,
                            "supplyPointUid": sp.uid,
                        },
                    )
                    for code in reading.REASONS.values()
                },
            }
            for name, (path, params) in calls.items():
                status, data = await get(client, path, params)
                file = OUT / f"{sp.ean}_{name}.json"
                file.write_text(json.dumps({"status": status, "data": data}, ensure_ascii=False))
                print(f"  {name}: HTTP {status}")
                await asyncio.sleep(0.5)
            _status, vals = await get(client, *calls["consumption_vals"])
            usage, remaining = reading.parse_consumption_vals(vals)
            print(f"  parsed: kWh/day {usage}, remaining {remaining}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
