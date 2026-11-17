"""Minimal HA websocket client. Send websocket messages to HA. Usage: HA_TOKEN=... [HA_WS=ws://host:8123/api/websocket] ha_ws.py messages.json"""

import asyncio
import json
import os
import sys

import aiohttp

URL = os.environ.get("HA_WS", "ws://homeassistant.local:8123/api/websocket")


async def main(msgs: list[dict]) -> None:
    async with aiohttp.ClientSession() as s, s.ws_connect(URL) as ws:
        await ws.receive_json()
        await ws.send_json({"type": "auth", "access_token": os.environ["HA_TOKEN"]})
        auth = await ws.receive_json()
        if auth.get("type") != "auth_ok":
            sys.exit(f"auth failed: {auth}")
        for i, msg in enumerate(msgs, start=1):
            await ws.send_json({"id": i, **msg})
            while True:
                r = await ws.receive_json()
                if r.get("id") == i:
                    break
            print(
                json.dumps(
                    {
                        "request": msg["type"],
                        "success": r.get("success"),
                        "result": r.get("result"),
                        "error": r.get("error"),
                    },
                    ensure_ascii=False,
                )
            )


with open(sys.argv[1]) as fh:
    asyncio.run(main(json.load(fh)))
