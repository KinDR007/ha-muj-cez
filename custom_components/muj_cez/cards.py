"""Install the custom cards the dashboard needs (button-card, stack-in-card, mini-graph-card).

Preferred: through the HA Marketplace (built into HA since 2026.11) or HACS, using their
own websocket commands (the same as the "Download" button in their UI); they then track
and update the card and register the Lovelace resource themselves.
Without HACS: the latest release asset is downloaded from GitHub into
/config/www/muj_cez/cards/ and registered as a Lovelace module resource.
Only runs with the user's consent (settings option or the repair "fix" button).
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com/repos/{repo}/releases/latest"
LOCAL_DIR = ("www", "muj_cez", "cards")
LOCAL_URL = "/local/muj_cez/cards/{file}?v={tag}"
TIMEOUT = aiohttp.ClientTimeout(total=60)
MAX_SIZE = 5_000_000
STORE_TIMEOUT = 300


@dataclass(frozen=True)
class Card:
    name: str  # card type / resource name fragment
    repo: str  # GitHub and HACS repository
    asset: str  # release asset with the module


CARDS = (
    Card("button-card", "custom-cards/button-card", "button-card.js"),
    Card("stack-in-card", "custom-cards/stack-in-card", "stack-in-card.js"),
    Card("mini-graph-card", "kalkih/mini-graph-card", "mini-graph-card-bundle.js"),
)


class CardInstallError(Exception):
    """A card could not be installed."""


def _resources(hass: HomeAssistant) -> Any:
    from homeassistant.components.lovelace.const import LOVELACE_DATA

    lovelace = hass.data.get(LOVELACE_DATA)
    return lovelace.resources if lovelace is not None else None


async def async_missing_cards(hass: HomeAssistant) -> list[str]:
    """Required cards without a Lovelace resource ([] when it cannot be determined)."""
    resources = _resources(hass)
    if resources is None:
        return [card.name for card in CARDS]
    try:
        if not getattr(resources, "loaded", True):
            await resources.async_load()
        urls = " ".join(str(item.get("url", "")) for item in resources.async_items())
    except Exception:  # YAML resources or not loaded
        return []
    return [card.name for card in CARDS if card.name not in urls]


# Store -> command that installs a repository (Marketplace renamed HACS' "download").
STORES = {
    "marketplace": "marketplace/repository/install",
    "hacs": "hacs/repository/download",
}


class _Connection:
    """Minimal websocket connection to call a store command from Python."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.future: asyncio.Future[dict[str, Any]] = hass.loop.create_future()
        self.user = type("AdminUser", (), {"is_admin": True, "id": None})()
        self.context = lambda msg: None

    def _done(self, message: dict[str, Any]) -> None:
        if not self.future.done():
            self.future.set_result(message)

    def send_message(self, message: Any) -> None:
        self._done(message if isinstance(message, dict) else {"success": True})

    def send_result(self, msg_id: int, result: Any = None) -> None:
        self._done({"success": True, "result": result})

    def send_error(self, msg_id: int, code: str, message: str, *args: Any, **kw: Any) -> None:
        self._done({"success": False, "error": {"code": code, "message": message}})

    def async_handle_exception(self, msg: dict[str, Any], err: Exception) -> None:
        self._done({"success": False, "error": {"code": "exception", "message": str(err)}})


async def _store_call(hass: HomeAssistant, command: str, **payload: Any) -> Any:
    """Run a registered websocket command; None when it does not exist."""
    handlers = hass.data.get("websocket_api") or {}
    if command not in handlers:
        return None
    handler, _schema = handlers[command]
    connection = _Connection(hass)
    handler(hass, connection, {"id": 1, "type": command, **payload})
    async with asyncio.timeout(STORE_TIMEOUT):
        message = await connection.future
    if not message.get("success", True):
        raise CardInstallError(str((message.get("error") or {}).get("message")))
    return message.get("result")


async def _install_store(hass: HomeAssistant, card: Card) -> str | None:
    """Install through Marketplace or HACS; returns the store name or None.

    A store that is missing a command or refuses the install (e.g. its warning was not
    accepted yet) is skipped, so the next store or the GitHub fallback is used.
    """
    for store, install in STORES.items():
        if install not in (hass.data.get("websocket_api") or {}):
            continue
        try:
            repositories = await _store_call(hass, f"{store}/repositories/list")
        except (CardInstallError, TimeoutError) as err:
            _LOGGER.debug("%s repository list failed: %s", store, err)
            continue
        repo = next(
            (r for r in repositories or [] if str(r.get("full_name", "")).lower() == card.repo),
            None,
        )
        if repo is None:
            continue
        try:
            await _store_call(hass, install, repository=str(repo["id"]))
        except (CardInstallError, TimeoutError) as err:
            _LOGGER.warning("Installing %s through %s failed: %s", card.name, store, err)
            continue
        return store
    return None


async def _install_github(hass: HomeAssistant, card: Card) -> None:
    """Download the latest release asset and register it as a Lovelace resource."""
    resources = _resources(hass)
    if resources is None or not hasattr(resources, "async_create_item"):
        raise CardInstallError("Lovelace resources are managed in YAML")
    session = async_get_clientsession(hass)
    try:
        async with session.get(GITHUB_API.format(repo=card.repo), timeout=TIMEOUT) as resp:
            if resp.status != 200:
                raise CardInstallError(f"GitHub {card.repo}: HTTP {resp.status}")
            release = await resp.json()
        tag = str(release.get("tag_name") or "latest")
        asset = next((a for a in release.get("assets") or [] if a.get("name") == card.asset), None)
        if asset is None:
            raise CardInstallError(f"{card.repo} {tag}: asset {card.asset} not found")
        async with session.get(asset["browser_download_url"], timeout=TIMEOUT) as resp:
            if resp.status != 200:
                raise CardInstallError(f"{card.asset}: HTTP {resp.status}")
            content = await resp.read()
    except (aiohttp.ClientError, TimeoutError) as err:
        raise CardInstallError(f"{card.repo}: {err}") from err
    if not content or len(content) > MAX_SIZE or b"customElements" not in content:
        raise CardInstallError(f"{card.asset}: unexpected content")

    path = hass.config.path(*LOCAL_DIR, card.asset)

    def write() -> None:
        import os

        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(content)

    await hass.async_add_executor_job(write)
    url = LOCAL_URL.format(file=card.asset, tag=tag)
    if not getattr(resources, "loaded", True):
        await resources.async_load()
    for item in resources.async_items():
        if f"/{card.asset}" in str(item.get("url", "")):
            await resources.async_update_item(item["id"], {"res_type": "module", "url": url})
            return
    await resources.async_create_item({"res_type": "module", "url": url})


async def async_install_cards(hass: HomeAssistant, names: list[str]) -> dict[str, str]:
    """Install the given cards; returns card name -> "marketplace" / "hacs" / "github" / error."""
    result: dict[str, str] = {}
    for card in CARDS:
        if card.name not in names:
            continue
        try:
            store = await _install_store(hass, card)
            if store is None:
                await _install_github(hass, card)
                store = "github"
            result[card.name] = store
        except CardInstallError as err:
            _LOGGER.warning("Installing %s failed: %s", card.name, err)
            result[card.name] = str(err)
    return result
