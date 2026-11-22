"""Generate the ČEZ dashboard view from the shipped template and the entities in HA.

The template (dashboard_template.json, exported by tools/dashboard/export_dashboard.py)
contains every section with marker entity ids and the data each section needs. Markers
are replaced with entity ids looked up in the entity registry by unique id, so renamed
entities and other languages work. Sections are kept only when their data exist
(smart meter, production point), so accounts with and without PV get a fitting view.

Every consumption supply point gets one tab (panel view, path "cez-<EAN>", title
"⚡ <street> · <EAN end>") with the integration's own card muj-cez-tabs: inner tabs
Přehled, Ceny (price breakdown on) and Odečet (meter reading card of the point).
Views are written into a storage dashboard chosen in the options; other views are kept.
A view belongs to the config entry named in its tabs card, so several entries (customer
accounts) share one dashboard without overwriting each other. Tabs of older versions
(cez, cez-2, cez-ceny, cez-odecet) are replaced. The views use custom cards (button-card,
stack-in-card, mini-graph-card); missing ones are installed with the user's consent
(option, or the repair issue's fix button), see cards.py.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
import re
from functools import cache
from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir

from .api import CezData
from .cards import async_install_cards, async_missing_cards
from .const import (
    CONF_DASHBOARD,
    CONF_INSTALL_CARDS,
    CONF_REFERENCE_EXPORT_SENSOR,
    CONF_REFERENCE_SENSOR,
    CONF_SPOT_PRICE_SENSOR,
    DASHBOARD_DEFAULT,
    DASHBOARD_NEW,
    DASHBOARD_NEW_URL,
    DASHBOARD_OFF,
    DOMAIN,
    docs_url,
    price_breakdown_enabled,
)

_LOGGER = logging.getLogger(__name__)

TEMPLATE_FILE = Path(__file__).parent / "dashboard_template.json"
MARKER = re.compile(r"\b(sensor|select|calendar)\.mujcez_([cgvas])_([a-z0-9_]+)")
MISSING = "muj_cez_unavailable"
VIEW_PATH = "cez"
PRICES_PATH = "cez-ceny"
READING_PATH = "cez-odecet"
TABS_CARD = "custom:muj-cez-tabs"
READING_CARD = "custom:muj-cez-reading-card"
READING_MAX_WIDTH = 720
ACCOUNT_UNIQUE = {
    "chart_unit": "{entry}_chart_unit",
    "documents": "{entry}_documents",
    "unread_messages": "{entry}_unread_messages",
}
ISSUE_CARDS = "dashboard_missing_cards"
ISSUE_FAILED = "dashboard_failed"


class DashboardError(Exception):
    """The dashboard could not be written."""


@cache
def _template_text() -> str:
    return TEMPLATE_FILE.read_text(encoding="utf-8")


def load_template() -> dict[str, Any]:
    return json.loads(_template_text())


# --- Energy dashboard and spot price sensors ---------------------------------------


def grid_sensors_from_energy(prefs: dict[str, Any] | None) -> tuple[str | None, str | None]:
    """Grid import and export statistics from Energy preferences (new and legacy format)."""
    imp = exp = None
    for source in (prefs or {}).get("energy_sources") or []:
        if source.get("type") != "grid":
            continue
        imp = imp or source.get("stat_energy_from")
        exp = exp or source.get("stat_energy_to")
        for flow in source.get("flow_from") or []:
            imp = imp or flow.get("stat_energy_from")
        for flow in source.get("flow_to") or []:
            exp = exp or flow.get("stat_energy_to")
    # Only entities can be selected (external statistics contain ':').
    return (
        imp if imp and ":" not in imp else None,
        exp if exp and ":" not in exp else None,
    )


async def async_energy_grid_sensors(hass: HomeAssistant) -> tuple[str | None, str | None]:
    try:
        from homeassistant.components.energy.data import async_get_manager

        manager = await async_get_manager(hass)
    except Exception:  # energy not set up
        return None, None
    return grid_sensors_from_energy(manager.data)


def detect_spot_sensors(hass: HomeAssistant) -> tuple[str | None, str | None]:
    """Today/tomorrow hourly spot price sensors of cz_energy_spot_prices, when installed."""
    registry = er.async_get(hass)
    today = tomorrow = None
    for entry in registry.entities.values():
        if entry.platform != "cz_energy_spot_prices" or entry.domain != "sensor":
            continue
        if entry.entity_id.endswith("current_spot_electricity_price") or (
            "spot_electricity_price" in (entry.unique_id or "") and "current" in entry.entity_id
        ):
            today = today or entry.entity_id
        if "tomorrow" in entry.entity_id and "hour_order" in entry.entity_id:
            tomorrow = tomorrow or entry.entity_id
    return today, tomorrow


def suggested_options(hass: HomeAssistant, energy: tuple[str | None, str | None]) -> dict[str, Any]:
    """Defaults for the settings form: Energy dashboard grid sensors, spot sensor."""
    today, _tomorrow = detect_spot_sensors(hass)
    out: dict[str, Any] = {}
    if energy[0]:
        out[CONF_REFERENCE_SENSOR] = energy[0]
    if energy[1]:
        out[CONF_REFERENCE_EXPORT_SENSOR] = energy[1]
    if today:
        out[CONF_SPOT_PRICE_SENSOR] = today
    return out


# --- Dashboards ----------------------------------------------------------------------


def _lovelace(hass: HomeAssistant) -> Any:
    from homeassistant.components.lovelace.const import LOVELACE_DATA

    return hass.data.get(LOVELACE_DATA)


async def async_dashboard_choices(hass: HomeAssistant) -> list[dict[str, str]]:
    """Storage dashboards the view can be written to (value = url path)."""
    from homeassistant.components.lovelace.const import ConfigNotFound

    lovelace = _lovelace(hass)
    choices: list[dict[str, str]] = []
    if lovelace is None:
        return choices
    for url, dash in lovelace.dashboards.items():
        if getattr(dash, "mode", None) != "storage":
            continue
        title = (getattr(dash, "config", None) or {}).get("title") or url or "Přehled"
        # Skip dashboards generated by a strategy (e.g. map) and the default dashboard
        # without a stored config (auto generated); writing would replace their content.
        try:
            config = await dash.async_load(False)
        except ConfigNotFound:
            if url is None:
                continue
            config = {}
        if "strategy" in (config or {}):
            continue
        if url == DASHBOARD_NEW_URL:
            continue
        choices.append({"value": url or DASHBOARD_DEFAULT, "label": title})
    return sorted(choices, key=lambda c: c["label"].lower())


def _dashboards_collection(hass: HomeAssistant) -> Any:
    """The storage dashboards collection (only reachable through its websocket handler)."""
    handlers = hass.data.get("websocket_api") or {}
    handler = handlers.get("lovelace/dashboards/create")
    if not handler:
        return None
    func = inspect.unwrap(handler[0])
    owner = getattr(func, "__self__", None)
    return getattr(owner, "storage_collection", None)


async def async_ensure_new_dashboard(hass: HomeAssistant) -> str:
    """Create the dedicated "ČEZ" dashboard when it does not exist; returns its url."""
    lovelace = _lovelace(hass)
    if lovelace is not None and DASHBOARD_NEW_URL in lovelace.dashboards:
        return DASHBOARD_NEW_URL
    collection = _dashboards_collection(hass)
    if collection is None:
        raise DashboardError("Dashboards cannot be created")
    await collection.async_create_item(
        {
            "url_path": DASHBOARD_NEW_URL,
            "title": "ČEZ",
            "icon": "mdi:lightning-bolt-circle",
            "show_in_sidebar": True,
            "require_admin": False,
        }
    )
    return DASHBOARD_NEW_URL


# --- View generation -----------------------------------------------------------------


def point_path(sp: Any) -> str:
    """Stable, unique path of the tab of a supply point."""
    return f"{VIEW_PATH}-{re.sub(r'[^a-z0-9]', '', (sp.ean or sp.uid).lower())}"


def point_title(sp: Any) -> str:
    """Street and number with the end of the EAN (as on the meter reading card)."""
    ident = (sp.ean or sp.uid)[-7:]
    street = (sp.name or "").split(",")[0].strip()  # without the town
    mark = "🔥" if sp.gas else "⚡"
    return f"{mark} {street} · {ident}" if street else f"{mark} {ident}"


def build_views(
    hass: HomeAssistant,
    entry_id: str,
    data: CezData,
    spot_today: str | None = None,
    spot_tomorrow: str | None = None,
    prices: bool = True,
    reading: bool = True,
) -> list[dict[str, Any]]:
    """One tab per consumption supply point, sections fitting the existing entities."""
    template = load_template()
    registry = er.async_get(hass)
    keys: dict[str, str] = template["keys"]

    def unique(domain: str, unique_id: str) -> str | None:
        return registry.async_get_entity_id(domain, DOMAIN, unique_id)

    consumption = [s for s in data.supply_points.values() if not s.supply_point.production]
    views = []
    for spd in consumption:
        sp = spd.supply_point
        prod = next(
            (
                s.supply_point
                for s in data.supply_points.values()
                if s.supply_point.production and s.supply_point.place_id == sp.place_id
            ),
            None,
        )

        def resolve(match: re.Match[str], sp=sp, prod=prod) -> str:
            domain, kind, slug = match.groups()
            entity: str | None = None
            if kind == "s":
                entity = spot_today if slug == "today" else spot_tomorrow
            elif (key := keys.get(f"{kind}:{slug}")) is not None:
                if kind == "a":
                    entity = unique(domain, ACCOUNT_UNIQUE[key].format(entry=entry_id))
                elif kind == "v":
                    entity = unique(domain, f"{prod.uid}_{key}") if prod else None
                else:
                    entity = unique(domain, f"{sp.uid}_{key}")
            return entity or f"{domain}.{MISSING}"

        def has(kind: str, key: str, sp=sp, prod=prod) -> bool:
            owner = prod if kind == "v" else sp
            return owner is not None and unique("sensor", f"{owner.uid}_{key}") is not None

        grid = has("g", "grid_data_date")
        production = has("v", "last_payout")
        hdo = has("c", "hdo_tariff")
        flags = {
            "electricity": not sp.gas,
            "gas": sp.gas,
            "grid": grid,
            "production": production,
            "no_grid": not grid,
            "hdo": hdo,
            "no_hdo": not hdo,
        }
        sections = []
        for item in template["sections"]:
            if not all(flags.get(r, False) for r in item["requires"]):
                continue
            text = MARKER.sub(resolve, json.dumps(item["config"], ensure_ascii=False))
            section = json.loads(text)
            if not production and "span_without_production" in item:
                section["column_span"] = item["span_without_production"]
            sections.append(section)
        main = template["view"]
        tabs: list[dict[str, Any]] = [
            {
                "title": "Přehled",
                "icon": main["icon"],
                "max_columns": main.get("max_columns", 3),
                "sections": sections,
            }
        ]
        if prices and (sub := template.get("subview")):
            text = MARKER.sub(resolve, json.dumps(sub["sections"], ensure_ascii=False))
            price_sections = json.loads(text)
            if button := unique("button", f"{sp.uid}_refresh_invoices"):
                _add_refresh_badge(price_sections, button)
            tabs.append(
                {
                    "title": "Ceny",
                    "icon": sub["view"]["icon"],
                    "max_columns": sub["view"].get("max_columns", 2),
                    "sections": price_sections,
                }
            )
        if reading:
            tabs.append(reading_tab(entry_id, sp.ean))
        path = point_path(sp)
        card = {"type": TABS_CARD, "id": path, "entry_id": entry_id, "tabs": tabs}
        views.append({"title": point_title(sp), "path": path, "type": "panel", "cards": [card]})
    return views


def _add_refresh_badge(sections: list[dict[str, Any]], button: str) -> None:
    """Refresh icon in the heading of the price breakdown, asks before downloading."""
    heading = next(
        (c for sec in sections for c in sec.get("cards", []) if c.get("type") == "heading"),
        None,
    )
    if heading is None:
        return
    heading.setdefault("badges", []).append(
        {
            "type": "entity",
            "entity": button,
            "icon": "mdi:refresh",
            "show_state": False,
            "show_icon": True,
            "tap_action": {
                "action": "perform-action",
                "perform_action": "button.press",
                "target": {"entity_id": button},
                "confirmation": {
                    "text": "Opravdu znovu načíst faktury a ceníky tohoto odběrného místa?"
                },
            },
        }
    )


def reading_tab(entry_id: str, ean: str) -> dict[str, Any]:
    """Meter reading tab: the integration's own card fixed to one supply point."""
    return {
        "title": "Odečet",
        "icon": "mdi:counter",
        "max_columns": 1,
        "max_width": READING_MAX_WIDTH,
        "cards": [{"type": READING_CARD, "entry_id": entry_id, "ean": ean}],
    }


def _is_legacy(path: Any) -> bool:
    """Tabs written by versions before 1.5 (one set per dashboard)."""
    return isinstance(path, str) and bool(
        re.fullmatch(rf"({VIEW_PATH}|{PRICES_PATH}|{READING_PATH})(-\d{{1,3}})?", path)
    )


def view_owner(view: Any) -> str | None:
    """Config entry of a generated view (named in its tabs card)."""
    cards = view.get("cards") if isinstance(view, dict) else None
    card = cards[0] if isinstance(cards, list) and cards else None
    if isinstance(card, dict) and card.get("type") == TABS_CARD:
        return card.get("entry_id")
    return None


def _lock(hass: HomeAssistant) -> asyncio.Lock:
    """One writer at a time: entries set up together share the dashboard."""
    data = hass.data.setdefault(DOMAIN, {})
    return data.setdefault("dashboard_lock", asyncio.Lock())


async def async_write_dashboard(
    hass: HomeAssistant, url: str, views: list[dict[str, Any]], entry_id: str
) -> bool:
    """Insert/replace the views of the entry in a storage dashboard, keep everything else.
    Returns True when the entry had no tabs there before."""
    from homeassistant.components.lovelace.const import ConfigNotFound

    lovelace = _lovelace(hass)
    if lovelace is None:
        raise DashboardError("Lovelace is not loaded")
    dash = lovelace.dashboards.get(None if url == DASHBOARD_DEFAULT else url)
    if dash is None or getattr(dash, "mode", None) != "storage":
        raise DashboardError(f"Dashboard {url} not found or not editable")
    async with _lock(hass):
        try:
            config = dict(await dash.async_load(False))
        except ConfigNotFound:
            config = {"views": []}
        if "strategy" in config:
            raise DashboardError(f"Dashboard {url} is generated by a strategy")

        def ours(view: Any) -> bool:
            return view_owner(view) == entry_id or _is_legacy(view.get("path"))

        existing = list(config.get("views") or [])
        added = not any(view_owner(v) == entry_id for v in existing)
        position = next((i for i, v in enumerate(existing) if ours(v)), None)
        if position is None:
            # After the tabs of other entries (accounts), else at the end.
            others = [i for i, v in enumerate(existing) if view_owner(v)]
            position = others[-1] + 1 if others else len(existing)
        kept_before = [v for v in existing[:position] if not ours(v)]
        kept_after = [v for v in existing[position:] if not ours(v)]
        config["views"] = kept_before + views + kept_after
        templates = dict(config.get("button_card_templates") or {})
        templates.update(load_template()["templates"])
        config["button_card_templates"] = templates
        await dash.async_save(config)
    return added


RELOAD_NOTIFICATION = f"{DOMAIN}_dashboard_ready"
_RELOAD_TEXT = {
    "cs": (
        "Dashboard Můj ČEZ je připravený",
        "Obnovte stránku prohlížeče (F5), aby se načetly karty integrace. Do té doby se "
        "v záložkách ČEZ může zobrazovat „Chyba nastavení“.\n\n[Otevřít dashboard](/{url})",
    ),
    "en": (
        "Můj ČEZ dashboard is ready",
        "Reload the browser page (F5) to load the integration's cards. Until then the ČEZ "
        "tabs may show “Configuration error”.\n\n[Open the dashboard](/{url})",
    ),
}


def notify_reload(hass: HomeAssistant, url: str) -> None:
    """Cards registered after the browser page was loaded load only with the next page
    load: ask for a reload after a new dashboard tab or newly installed cards."""
    from homeassistant.components import persistent_notification

    title, text = _RELOAD_TEXT["cs" if hass.config.language == "cs" else "en"]
    path = "lovelace" if url == DASHBOARD_DEFAULT else url
    persistent_notification.async_create(
        hass, text.format(url=path), title, notification_id=RELOAD_NOTIFICATION
    )


async def async_update_dashboard(hass: HomeAssistant, entry: Any) -> str | None:
    """Generate and write the dashboard selected in the options; returns its url."""
    url = entry.options.get(CONF_DASHBOARD)
    if not url or url == DASHBOARD_OFF:
        return None
    coordinator = entry.runtime_data
    if coordinator.data is None:
        return None
    today, tomorrow = detect_spot_sensors(hass)
    await hass.async_add_executor_job(_template_text)  # read the file outside the loop
    views = build_views(
        hass,
        entry.entry_id,
        coordinator.data,
        today,
        tomorrow,
        prices=price_breakdown_enabled(entry.options),
    )
    try:
        if url == DASHBOARD_NEW:
            url = await async_ensure_new_dashboard(hass)
        added = await async_write_dashboard(hass, url, views, entry.entry_id)
    except DashboardError as err:
        _LOGGER.warning("Dashboard update failed: %s", err)
        ir.async_create_issue(
            hass,
            DOMAIN,
            ISSUE_FAILED,
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key=ISSUE_FAILED,
            translation_placeholders={"error": str(err)},
            learn_more_url=docs_url("potize"),
        )
        return None
    ir.async_delete_issue(hass, DOMAIN, ISSUE_FAILED)
    missing = await async_missing_cards(hass)
    installed = False
    if missing and entry.options.get(CONF_INSTALL_CARDS, True):
        await async_install_cards(hass, missing)
        before, missing = missing, await async_missing_cards(hass)
        installed = len(missing) < len(before)
    if (added or installed) and not missing:
        notify_reload(hass, url)
    if missing:
        ir.async_create_issue(
            hass,
            DOMAIN,
            ISSUE_CARDS,
            is_fixable=True,
            severity=ir.IssueSeverity.WARNING,
            translation_key=ISSUE_CARDS,
            translation_placeholders={"cards": ", ".join(missing)},
            learn_more_url=docs_url("potize"),
        )
    else:
        ir.async_delete_issue(hass, DOMAIN, ISSUE_CARDS)
    return url
