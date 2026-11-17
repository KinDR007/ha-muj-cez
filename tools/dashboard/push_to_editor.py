"""Put the ČEZ view into the Dashboard Editor model and publish it like the editor does.

Usage:
  HA_HOST=192.168.88.201 HA_SSH_PASS=... HA_TOKEN=... EDITOR_DIR=<dashboard_editor_app> \\
    .venv/bin/python tools/dashboard/push_to_editor.py view.json [--model prehled] [--after energie] [--dry-run]

view.json is the output of build_cez_view.py (an editor model view with path "cez").

Steps (same safety as the editor's Publish):
  1. download the model and the editor's "published" state, read the live dashboard,
  2. refuse when the live dashboard differs from the last publish (changed outside the editor)
     in any other view than the one being replaced,
  3. insert/replace the view, validate the schema and entities with the editor's own checks,
  4. back up the live config (editor backups/ and local .backup/), save the model + history,
     save the dashboard, update the published state.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import aiohttp
import yaml

ROOT = Path(__file__).resolve().parents[2]
REMOTE = "/addon_configs/local_dashboard_editor"


def ssh(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    env = dict(os.environ, SSHPASS=os.environ["HA_SSH_PASS"])
    return subprocess.run(["sshpass", "-e", *cmd], env=env, check=True, **kw)


def scp_get(remote: str, local: Path) -> None:
    ssh(["scp", "-q", f"root@{os.environ['HA_HOST']}:{remote}", str(local)])


def scp_put(local: Path, remote: str) -> None:
    ssh(["scp", "-q", str(local), f"root@{os.environ['HA_HOST']}:{remote}"])


async def ws(messages: list[dict]) -> list[dict]:
    url = f"ws://{os.environ['HA_HOST']}:8123/api/websocket"
    out = []
    async with (
        aiohttp.ClientSession() as s,
        s.ws_connect(url, max_msg_size=0) as w,
    ):
        await w.receive_json()
        await w.send_json({"type": "auth", "access_token": os.environ["HA_TOKEN"]})
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
    ap.add_argument("--model", default="prehled")
    ap.add_argument("--after", default="energie")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    for var in ("HA_HOST", "HA_SSH_PASS", "HA_TOKEN", "EDITOR_DIR"):
        if not os.environ.get(var):
            print(f"Set {var}", file=sys.stderr)
            return 2
    editor = Path(os.environ["EDITOR_DIR"])
    sys.path[:0] = [str(editor / "model"), str(editor / "app")]
    import dashmodel
    from checks import entity_report, published_model, schema_errors

    view = json.loads(Path(a.view).read_text())
    path = view.get("path")
    tmp = Path(tempfile.mkdtemp())
    scp_get(f"{REMOTE}/dashboards/{a.model}.yaml", tmp / "model.yaml")
    scp_get(f"{REMOTE}/published/{a.model}.json", tmp / "published.json")
    model = yaml.safe_load((tmp / "model.yaml").read_text())
    published = json.loads((tmp / "published.json").read_text())
    url = model["dashboard"]
    live, states = asyncio.run(
        ws(
            [
                {"type": "lovelace/config", "url_path": None if url == "lovelace" else url},
                {"type": "get_states"},
            ]
        )
    )

    lv = {v.get("path"): v for v in live["views"]}
    pv = {v.get("path"): v for v in published["views"]}
    outside = sorted(k for k in lv.keys() | pv.keys() if k != path and lv.get(k) != pv.get(k))
    tmpl_changed = live.get("button_card_templates") != published.get("button_card_templates")
    if outside or tmpl_changed:
        print(
            f"Live dashboard changed outside the editor: {outside} templates={tmpl_changed}",
            file=sys.stderr,
        )
        return 1

    paths = [v.get("path") for v in model["views"]]
    if path in paths:
        model["views"][paths.index(path)] = view
    else:
        model["views"].insert(paths.index(a.after) + 1 if a.after in paths else len(paths), view)
    errs = schema_errors(model)
    if errs:
        print("Schema errors:", errs, file=sys.stderr)
        return 1
    cfg = dashmodel.render(published_model(model))
    cfg = dict(
        {k: v for k, v in live.items() if k not in ("views", "button_card_templates")}, **cfg
    )
    rep = entity_report({"views": [v for v in cfg["views"] if v.get("path") == path]}, states)
    if rep["errors"]:
        print("Missing entities:", rep["errors"], file=sys.stderr)
        return 1
    cv = {v.get("path"): v for v in cfg["views"]}
    diff = sorted(k for k in lv.keys() | cv.keys() if lv.get(k) != cv.get(k))
    print(f"views changed: {diff}; warnings: {len(rep['warnings'])}")
    if diff not in ([], [path]):
        print("Unexpected changes in other views, aborting", file=sys.stderr)
        return 1
    if a.dry_run:
        return 0

    ts = time.strftime("%Y%m%d_%H%M%S")
    backup = tmp / f"{ts}_{url}.json"
    backup.write_text(json.dumps(live, ensure_ascii=False))
    (ROOT / ".backup").mkdir(exist_ok=True)
    (ROOT / ".backup" / backup.name).write_text(backup.read_text())
    scp_put(backup, f"{REMOTE}/backups/{backup.name}")
    text = yaml.safe_dump(model, allow_unicode=True, sort_keys=False, width=120)
    (tmp / "new.yaml").write_text(text)
    scp_put(tmp / "new.yaml", f"{REMOTE}/dashboards/{a.model}.tmp")
    ssh(
        [
            "ssh",
            f"root@{os.environ['HA_HOST']}",
            f"mv {REMOTE}/dashboards/{a.model}.tmp {REMOTE}/dashboards/{a.model}.yaml && "
            f"mkdir -p {REMOTE}/history/{a.model} && "
            f"cp {REMOTE}/dashboards/{a.model}.yaml {REMOTE}/history/{a.model}/{ts}.yaml",
        ]
    )
    asyncio.run(
        ws(
            [
                {
                    "type": "lovelace/config/save",
                    "url_path": None if url == "lovelace" else url,
                    "config": cfg,
                }
            ]
        )
    )
    (tmp / "published_new.json").write_text(json.dumps(cfg, ensure_ascii=False))
    scp_put(tmp / "published_new.json", f"{REMOTE}/published/{a.model}.json")
    (after,) = asyncio.run(
        ws([{"type": "lovelace/config", "url_path": None if url == "lovelace" else url}])
    )
    print("published; live == published:", after == cfg, "| backup:", backup.name)
    return 0 if after == cfg else 1


if __name__ == "__main__":
    sys.exit(main())
