"""Smoke test of the API client.

Live:    CEZ_USER=... CEZ_PASS=... .venv/bin/python tools/smoke.py
Offline: .venv/bin/python tools/smoke.py --offline   (replays .snapshot/cez, no network)
"""

import asyncio
import logging
import os
import sys
from dataclasses import asdict
from datetime import date

import aiohttp
from offline import OfflineCezClient, api


def _print(data: "api.CezData", grid: dict | None = None) -> None:
    for place, cache in (grid or {}).items():
        print(
            f"grid {place}: from import={cache.get('import_from')} export={cache.get('export_from')}"
        )
        for key in ("import", "export"):
            values = cache.get(key) or {}
            if values:
                print(
                    f"  {key}: {len(values)} days {min(values)}..{max(values)} sum={sum(values.values()):.1f}"
                )

    print("unread_messages:", data.unread_messages)
    print("documents:", len(data.documents))
    for uid, spd in data.supply_points.items():
        d = asdict(spd)
        if d.get("advance_plan"):
            d["advance_plan"]["items"] = f"<{len(d['advance_plan']['items'])} items>"
        print(uid)
        for k, v in d.items():
            print(f"  {k}: {v}")


async def main(offline: bool) -> int:
    if offline:
        try:
            client = OfflineCezClient()
        except FileNotFoundError as err:
            print(err, file=sys.stderr)
            return 2
        today = client.captured_on or date.today()
        grid: dict = {}
        data = await client.fetch_all(today, grid)
        _print(data, grid)
        return 0
    user, pwd = os.environ.get("CEZ_USER"), os.environ.get("CEZ_PASS")
    if not user or not pwd:
        print("Set CEZ_USER and CEZ_PASS (or use --offline)", file=sys.stderr)
        return 2
    async with aiohttp.ClientSession() as session:
        client = api.CezClient(session, user, pwd)
        try:
            await client.authenticate()
            data = await client.fetch_all(date.today())
        except api.CezAuthError as err:
            print(f"AUTH ERROR: {err}", file=sys.stderr)
            return 1
        except api.CezError as err:
            print(f"ERROR: {err}", file=sys.stderr)
            return 1
    _print(data)
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "WARNING"))
    sys.exit(asyncio.run(main("--offline" in sys.argv)))
