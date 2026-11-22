"""Card URLs change with the card content (browsers keep cached modules otherwise)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.muj_cez import frontend


def test_fingerprint_follows_content(tmp_path: Path) -> None:
    for name in frontend.CARD_FILES:
        (tmp_path / name).write_text("a")
    before = frontend._fingerprints(tmp_path)
    (tmp_path / frontend.CARD_FILES[0]).write_text("b")
    after = frontend._fingerprints(tmp_path)
    assert before[frontend.CARD_FILES[0]] != after[frontend.CARD_FILES[0]]
    assert before[frontend.CARD_FILES[1]] == after[frontend.CARD_FILES[1]]


async def test_urls_carry_version_and_fingerprint() -> None:
    hass = MagicMock()
    hass.config.components = {"frontend"}
    hass.http.async_register_static_paths = AsyncMock()

    async def run(func, *args):
        return func(*args)

    hass.async_add_executor_job = run
    with patch.object(frontend, "add_extra_js_url") as add:
        await frontend.async_register_frontend(hass, "1.6.0b2")
    urls = [c.args[1] for c in add.call_args_list]
    hashes = frontend._fingerprints(Path(frontend.__file__).parent)
    assert urls == [
        f"{frontend.URL_BASE}/{name}?v=1.6.0b2-{hashes[name]}" for name in frontend.CARD_FILES
    ]
