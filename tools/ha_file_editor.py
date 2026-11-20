"""Read / write files on a Home Assistant OS host through the File editor add-on.

For hosts without SSH: uses the add-on's ingress API with a long-lived access token.
The add-on cannot create directories, the target directory must exist.

Usage:
  HA_URL=http://host:8123 HA_TOKEN=... .venv/bin/python tools/ha_file_editor.py get <path>...
  HA_URL=... HA_TOKEN=... .venv/bin/python tools/ha_file_editor.py put <local> <remote> [...]
  HA_URL=... HA_TOKEN=... .venv/bin/python tools/ha_file_editor.py deploy [file ...]
      (integration files to /homeassistant/custom_components/muj_cez/, default: all)

Every written file is read back and compared.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import aiohttp

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "muj_cez"
REMOTE_COMPONENT = "/homeassistant/custom_components/muj_cez"


async def _ws(ws: aiohttp.ClientWebSocketResponse, i: int, **msg: object) -> dict:
    await ws.send_json({"id": i, **msg})
    while True:
        r = await ws.receive_json()
        if r.get("id") == i:
            if not r.get("success"):
                raise SystemExit(f"{msg.get('type')}: {r.get('error')}")
            return r["result"]


async def main(cmd: str, args: list[str]) -> int:
    base, token = os.environ["HA_URL"].rstrip("/"), os.environ["HA_TOKEN"]
    async with aiohttp.ClientSession() as s:
        async with s.ws_connect(base.replace("http", "ws", 1) + "/api/websocket") as ws:
            await ws.receive_json()
            await ws.send_json({"type": "auth", "access_token": token})
            if (await ws.receive_json()).get("type") != "auth_ok":
                raise SystemExit("HA auth failed")
            api = "supervisor/api"
            info = await _ws(
                ws, 1, type=api, endpoint="/addons/core_configurator/info", method="get"
            )
            sess = await _ws(ws, 2, type=api, endpoint="/ingress/session", method="post")
        root = base + info["ingress_url"].rstrip("/")
        cookies = {"ingress_session": sess["session"]}
        if cmd == "get":
            for path in args:
                async with s.get(
                    f"{root}/api/file", params={"filename": path}, cookies=cookies
                ) as r:
                    print(f"== {path} HTTP {r.status}")
                    print(await r.text())
            return 0
        if cmd == "deploy":
            names = args or sorted(
                str(p.relative_to(COMPONENT))
                for p in COMPONENT.rglob("*")
                if p.is_file()
                and "__pycache__" not in p.parts
                and p.suffix in (".py", ".json", ".yaml")
            )
            pairs = [(str(COMPONENT / n), f"{REMOTE_COMPONENT}/{n}") for n in names]
        elif cmd == "put" and args and len(args) % 2 == 0:
            pairs = list(zip(args[::2], args[1::2], strict=True))
        else:
            print(__doc__)
            return 2
        for local, remote in pairs:
            text = await asyncio.to_thread(Path(local).read_text, encoding="utf-8")
            async with s.post(
                f"{root}/api/save", data={"filename": remote, "text": text}, cookies=cookies
            ):
                pass
            async with s.get(f"{root}/api/file", params={"filename": remote}, cookies=cookies) as r:
                back = await r.text()
            print(f"{remote}: {'ok' if back == text else 'MISMATCH'}")
            if back != text:
                return 1
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(asyncio.run(main(sys.argv[1], sys.argv[2:])))
