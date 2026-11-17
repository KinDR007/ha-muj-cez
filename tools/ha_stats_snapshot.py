"""Capture Home Assistant long-term statistics once for offline development.

Usage: HA_TOKEN=... [HA_WS=ws://host:8123/api/websocket] ha_stats_snapshot.py <statistic_id> [start]
Writes .snapshot/ha/<statistic_id>_<period>.json for periods day and month.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import aiohttp

URL = os.environ.get("HA_WS", "ws://homeassistant.local:8123/api/websocket")
OUT = Path(__file__).resolve().parent.parent / ".snapshot" / "ha"


async def main(statistic_id: str, start: str) -> int:
    token = os.environ.get("HA_TOKEN")
    if not token:
        print("Set HA_TOKEN", file=sys.stderr)
        return 2
    OUT.mkdir(parents=True, exist_ok=True)
    timeout = aiohttp.ClientTimeout(total=900)
    async with (
        aiohttp.ClientSession(timeout=timeout) as s,
        s.ws_connect(URL, max_msg_size=0) as ws,
    ):
        await ws.receive_json()
        await ws.send_json({"type": "auth", "access_token": token})
        if (await ws.receive_json()).get("type") != "auth_ok":
            print("auth failed", file=sys.stderr)
            return 1
        for i, period in enumerate(("month", "day"), start=1):
            await ws.send_json(
                {
                    "id": i,
                    "type": "recorder/statistics_during_period",
                    "start_time": start,
                    "end_time": datetime.now(UTC).isoformat(),
                    "statistic_ids": [statistic_id],
                    "period": period,
                    "types": ["change", "sum", "state"],
                }
            )
            while True:
                r = await ws.receive_json()
                if r.get("id") == i:
                    break
            if not r.get("success"):
                print(f"{period}: {r.get('error')}", file=sys.stderr)
                return 1
            rows = r["result"].get(statistic_id, [])
            path = OUT / f"{statistic_id}_{period}.json"
            path.write_text(
                json.dumps(
                    {
                        "statistic_id": statistic_id,
                        "period": period,
                        "captured_at": datetime.now(UTC).isoformat(timespec="seconds"),
                        "rows": rows,
                    },
                    indent=1,
                )
            )
            print(f"{period}: {len(rows)} rows -> {path}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    sys.exit(
        asyncio.run(main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "2024-11-01T00:00:00Z"))
    )
