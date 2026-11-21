"""Export the ČEZ view as a template shipped with the integration.

Usage: EDITOR_DIR=<dashboard_editor_app> .venv/bin/python tools/dashboard/export_dashboard.py

Builds every section (build_cez_view.py in export mode) with marker entity ids,
renders it with the Dashboard Editor renderer (button-card templates, JS helpers) and
writes custom_components/muj_cez/dashboard_template.json:

  {"view": {...view without sections...}, "templates": {...},
   "sections": [{"requires": [...], "span_without_production": n, "config": {...}}],
   "subview": {"view": {...price breakdown view (own tab)...}, "sections": [...]},
   "keys": {"c:predikce_vyuctovani": "invoice_balance", ...}}

Markers: sensor.mujcez_c_<slug> (consumption point), sensor.mujcez_g_<slug> (smart meter
sensors of the same point), sensor.mujcez_v_<slug> (production point), account entities
select/calendar/sensor.mujcez_a_*, spot sensors sensor.mujcez_s_today / _tomorrow.
The integration replaces them with entity ids from the entity registry.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "custom_components" / "muj_cez" / "dashboard_template.json"
MARKER = re.compile(r"\b(sensor|select|calendar)\.mujcez_([cgvas])_([a-z0-9_]+)")
TEMPLATE_NAMES = {"vrm_head": "muj_cez_head", "vrm_details": "muj_cez_details"}
ACCOUNT_KEYS = {
    "select:jednotka_grafu": "chart_unit",
    "calendar:doklady": "documents",
    "sensor:neprectene_zpravy": "unread_messages",
}


def slug_keys() -> dict[str, str]:
    """Czech entity name slug -> sensor key (entity ids are created from cs names)."""
    sys.path.insert(0, str(ROOT / ".venv"))
    from homeassistant.util import slugify

    names = json.loads((ROOT / "custom_components/muj_cez/translations/cs.json").read_text())
    return {slugify(v["name"]): k for k, v in names["entity"]["sensor"].items()}


def main() -> int:
    editor = os.environ.get("EDITOR_DIR")
    if not editor:
        print("Set EDITOR_DIR", file=sys.stderr)
        return 2
    tmp = Path(tempfile.mkdtemp()) / "view.json"
    tmp_prices = tmp.with_name("prices.json")
    env = dict(
        os.environ,
        CEZ_EXPORT="1",
        CEZ_PREFIX="sensor.mujcez_c_",
        CEZ_GRID_PREFIX="sensor.mujcez_g_",
        CEZ_PROD_PREFIX="sensor.mujcez_v_",
        CEZ_SPOT_TODAY="sensor.mujcez_s_today",
        CEZ_SPOT_TOMORROW="sensor.mujcez_s_tomorrow",
        CEZ_SELECT="select.mujcez_a_jednotka_grafu",
        CEZ_CALENDAR="calendar.mujcez_a_doklady",
        CEZ_MESSAGES="sensor.mujcez_a_neprectene_zpravy",
    )
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools/dashboard/build_cez_view.py"),
            str(tmp),
            str(tmp_prices),
        ],
        env=env,
        check=True,
    )
    view = json.loads(tmp.read_text())
    prices = json.loads(tmp_prices.read_text())
    meta = [{k: sec.pop(k) for k in list(sec) if k.startswith("_")} for sec in view["sections"]]
    for sec in prices["sections"]:
        for k in [k for k in sec if k.startswith("_")]:
            sec.pop(k)

    sys.path[:0] = [f"{editor}/model", f"{editor}/app"]
    import dashmodel
    from checks import published_model, schema_errors

    model = {"dashboard": "muj-cez", "title": "ČEZ", "views": [view, prices]}
    errs = schema_errors(model)
    if errs:
        print("Schema errors:", errs, file=sys.stderr)
        return 1
    rendered = dashmodel.render(published_model(model))
    sections = rendered["views"][0]["sections"]
    price_sections = rendered["views"][1]["sections"]
    if len(sections) != len(meta):
        print("Section count changed while rendering", file=sys.stderr)
        return 1

    text = json.dumps(
        {
            "sections": sections,
            "prices": price_sections,
            "templates": rendered["button_card_templates"],
        }
    )
    for old, new in TEMPLATE_NAMES.items():
        text = text.replace(f'"{old}"', f'"{new}"')
    data = json.loads(text)
    templates = {TEMPLATE_NAMES.get(k, k): v for k, v in data["templates"].items()}

    slugs = slug_keys()
    keys: dict[str, str] = {}
    unknown = set()
    for domain, kind, slug in set(MARKER.findall(text)):
        if kind == "s":
            continue
        key = ACCOUNT_KEYS.get(f"{domain}:{slug}") if kind == "a" else slugs.get(slug)
        if key is None:
            unknown.add(f"{domain}.mujcez_{kind}_{slug}")
        else:
            keys[f"{kind}:{slug}"] = key
    if unknown:
        print("Markers without entity key:", sorted(unknown), file=sys.stderr)
        return 1

    out = {
        "version": 1,
        "view": {k: v for k, v in view.items() if k != "sections"},
        "templates": templates,
        "sections": [
            {
                "requires": m.get("_requires", []),
                **(
                    {"span_without_production": m["_span_without_production"]}
                    if "_span_without_production" in m
                    else {}
                ),
                "config": sec,
            }
            for m, sec in zip(meta, data["sections"], strict=True)
        ],
        "subview": {
            "view": {k: v for k, v in prices.items() if k != "sections"},
            "sections": data["prices"],
        },
        "keys": dict(sorted(keys.items())),
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    print(
        f"written {OUT.relative_to(ROOT)}: {OUT.stat().st_size} bytes, {len(out['sections'])} sections,"
        f" {len(keys)} entity keys"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
