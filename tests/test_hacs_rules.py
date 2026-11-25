"""Rules from the HACS default-list review (hacs/default#14678); do not relax them."""

from __future__ import annotations

import json
import re
from pathlib import Path

SOURCE = Path(__file__).parent.parent / "custom_components" / "muj_cez"
CODE = {p.name: p.read_text() for p in SOURCE.glob("*.py")}
FORBIDDEN = {
    # Installing other repositories through HACS / Marketplace internals.
    r"hass\.data\.get\(\s*[\"']websocket_api|hass\.data\[\s*[\"']websocket_api": "store handlers",
    r"hacs/repository|marketplace/repository": "store install commands",
    # Downloading third-party code at runtime and serving it as a resource.
    r"api\.github\.com|releases/latest|browser_download_url": "GitHub release download",
    r"res_type": "registering Lovelace resources",
    # Runtime installation of Python packages instead of manifest requirements.
    r"async_process_requirements|homeassistant\.requirements": "runtime requirements",
}

# Known exception, not flagged in the review: HA keeps the Lovelace dashboards collection
# only in a local variable, so "Nový dashboard ČEZ" reads it from the core
# lovelace/dashboards/create handler (no install, no fake admin connection).
ALLOWED = {"dashboard.py: store handlers"}


def test_no_forbidden_patterns() -> None:
    hits = {
        f"{name}: {why}"
        for name, text in CODE.items()
        for pattern, why in FORBIDDEN.items()
        if re.search(pattern, text)
    }
    assert hits - ALLOWED == set()


def test_requirements_in_manifest() -> None:
    manifest = json.loads((SOURCE / "manifest.json").read_text())
    assert "pypdf==5.1.0" in manifest["requirements"]


def test_dashboard_service_is_admin_only() -> None:
    text = CODE["services.py"]
    assert re.search(r"async_register_admin_service\([^)]*SERVICE_UPDATE_DASHBOARD", text, re.S)
