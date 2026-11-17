"""Render the ČEZ view and insert it into a plain Lovelace dashboard (no Dashboard Editor).

Usage:
  HA_URL=http://host:8123 HA_TOKEN=... EDITOR_DIR=<dashboard_editor_app> \\
    .venv/bin/python tools/dashboard/push_lovelace.py view.json --templates <model.yaml> \\
    [--dashboard lovelace] [--after spot] [--dry-run]

view.json is the output of build_cez_view.py (editor model view). It is rendered with the
editor's own renderer (viewlib) using the button-card templates of <model.yaml>. Existing
templates on the target dashboard are kept (the view uses the same vrm_head / vrm_details
fields); missing templates are added.

Safety: the live config is backed up to .backup/, the save is refused when the config
changed while running, and only the "cez" view may differ afterwards.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

import aiohttp
import yaml

ROOT = Path(__file__).resolve().parents[2]


async def ws(url: str, token: str, messages: list[dict]) -> list[dict]:
    out = []
    ws_url = url.replace("http", "ws", 1).rstrip("/") + "/api/websocket"
    async with aiohttp.ClientSession() as s, s.ws_connect(ws_url, max_msg_size=0) as w:
        await w.receive_json()
        await w.send_json({"type": "auth", "access_token": token})
        if (await w.receive_json()).get("type") != "auth_ok":
            raise SystemExit("HA auth failed")
        for i, m in enumerate(messages, 1):
            await w.send_json({"id": i, **m})
            while True:
                r = await w.receive_json()
                if r.get("id") == i:
                    break
            if not r.get("success"):
                raise SystemExit(f"{m['type']}: {r.get('error')}")
            out.append(r.get("result"))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("view")
    ap.add_argument("--templates", required=True, help="editor model yaml with the templates")
    ap.add_argument("--dashboard", default="lovelace")
    ap.add_argument("--after", default=None, help="insert after this view path")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    for var in ("HA_URL", "HA_TOKEN", "EDITOR_DIR"):
        if not os.environ.get(var):
            print(f"Set {var}", file=sys.stderr)
            return 2
    editor = Path(os.environ["EDITOR_DIR"])
    sys.path[:0] = [str(editor / "model"), str(editor / "app")]
    import dashmodel
    from checks import published_model, schema_errors

    view = json.loads(Path(a.view).read_text())
    model = yaml.safe_load(Path(a.templates).read_text())
    model["views"] = [view]
    errs = schema_errors(model)
    if errs:
        print("Schema errors:", errs, file=sys.stderr)
        return 1
    rendered = dashmodel.render(published_model(model))
    new_view = rendered["views"][0]
    url, token = os.environ["HA_URL"], os.environ["HA_TOKEN"]
    url_path = None if a.dashboard == "lovelace" else a.dashboard
    (live,) = asyncio.run(ws(url, token, [{"type": "lovelace/config", "url_path": url_path}]))

    views = [v for v in live["views"] if v.get("path") != new_view.get("path")]
    paths = [v.get("path") for v in views]
    old = next(
        (i for i, v in enumerate(live["views"]) if v.get("path") == new_view.get("path")), None
    )
    if old is not None:
        index = old
    elif a.after in paths:
        index = paths.index(a.after) + 1
    else:
        index = len(views)
    views.insert(index, new_view)
    templates = dict(rendered.get("button_card_templates") or {})
    templates.update(live.get("button_card_templates") or {})
    new = dict(live, views=views, button_card_templates=templates)
    added = sorted(set(templates) - set(live.get("button_card_templates") or {}))
    print(f"view at index {index}, templates added: {added}")
    if a.dry_run:
        return 0

    stamp = time.strftime("%Y%m%d_%H%M%S")
    (ROOT / ".backup").mkdir(exist_ok=True)
    backup = ROOT / ".backup" / f"lovelace_{a.dashboard}_{stamp}.json"
    backup.write_text(json.dumps(live, ensure_ascii=False))
    (current, _saved, after) = asyncio.run(
        ws(
            url,
            token,
            [
                {"type": "lovelace/config", "url_path": url_path},
                {"type": "lovelace/config/save", "url_path": url_path, "config": new},
                {"type": "lovelace/config", "url_path": url_path},
            ],
        )
    )
    if current != live:
        # Changed between reading and saving: restore what was there.
        asyncio.run(
            ws(
                url,
                token,
                [{"type": "lovelace/config/save", "url_path": url_path, "config": current}],
            )
        )
        print("Dashboard changed meanwhile, restored and aborted", file=sys.stderr)
        return 1
    others = [v for v in after["views"] if v.get("path") != new_view.get("path")]
    unchanged = others == [v for v in live["views"] if v.get("path") != new_view.get("path")]
    print("saved:", after == new, "| other views unchanged:", unchanged, "| backup:", backup.name)
    return 0 if after == new and unchanged else 1


if __name__ == "__main__":
    sys.exit(main())
