"""Actions (services) of the Muj CEZ integration."""

from __future__ import annotations

from datetime import date
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.service import async_register_admin_service

from .api import BillingDocument, strip_zeros
from .const import DOMAIN
from .coordinator import MujCezConfigEntry

SERVICE_GET_DOCUMENTS = "get_documents"
SERVICE_UPDATE_DASHBOARD = "update_dashboard"

ATTR_CONFIG_ENTRY_ID = "config_entry_id"
ATTR_DATE_FROM = "date_from"
ATTR_DATE_TO = "date_to"
ATTR_DOCUMENT_TYPE = "document_type"
ATTR_CONTRACT = "contract"
ATTR_UNPAID_ONLY = "unpaid_only"
ATTR_LIMIT = "limit"

DEFAULT_LIMIT = 100
MAX_LIMIT = 1000

GET_DOCUMENTS_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Optional(ATTR_DATE_FROM): cv.date,
        vol.Optional(ATTR_DATE_TO): cv.date,
        vol.Optional(ATTR_DOCUMENT_TYPE): cv.string,
        vol.Optional(ATTR_CONTRACT): cv.string,
        vol.Optional(ATTR_UNPAID_ONLY, default=False): cv.boolean,
        vol.Optional(ATTR_LIMIT, default=DEFAULT_LIMIT): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=MAX_LIMIT)
        ),
    }
)


def filter_documents(
    docs: list[BillingDocument],
    date_from: date | None = None,
    date_to: date | None = None,
    document_type: str | None = None,
    contract: str | None = None,
    unpaid_only: bool = False,
) -> list[BillingDocument]:
    """Filter documents; result is newest first.

    document_type and contract match case-insensitively as substrings; contract
    matches the contract number (without leading zeros) or the contract name.
    """
    doc_type = document_type.casefold() if document_type else None
    contract_q = contract.casefold().lstrip("0") if contract else None
    result = []
    for d in docs:
        day = d.event_date
        if date_from and (day is None or day < date_from):
            continue
        if date_to and (day is None or day > date_to):
            continue
        if doc_type and doc_type not in d.doc_type.casefold():
            continue
        if contract_q:
            number = (strip_zeros(d.agreement_id) or "").casefold()
            name = (d.contract_name or "").casefold()
            if contract_q not in number and contract_q not in name:
                continue
        if unpaid_only and d.balance <= 0:
            continue
        result.append(d)
    result.sort(key=lambda d: d.event_date or date.min, reverse=True)
    return result


def _get_entry(hass: HomeAssistant, entry_id: str | None) -> MujCezConfigEntry:
    entries = hass.config_entries.async_loaded_entries(DOMAIN)
    if entry_id:
        entries = [e for e in entries if e.entry_id == entry_id]
    if not entries:
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key="entry_not_loaded")
    if len(entries) > 1:
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key="entry_required")
    entry = entries[0]
    if entry.state is not ConfigEntryState.LOADED or entry.runtime_data.data is None:
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key="entry_not_loaded")
    return entry


async def _async_get_documents(call: ServiceCall) -> ServiceResponse:
    entry = _get_entry(call.hass, call.data.get(ATTR_CONFIG_ENTRY_ID))
    docs = filter_documents(
        entry.runtime_data.data.documents,
        date_from=call.data.get(ATTR_DATE_FROM),
        date_to=call.data.get(ATTR_DATE_TO),
        document_type=call.data.get(ATTR_DOCUMENT_TYPE),
        contract=call.data.get(ATTR_CONTRACT),
        unpaid_only=call.data[ATTR_UNPAID_ONLY],
    )
    limit = call.data[ATTR_LIMIT]
    result: dict[str, Any] = {
        "count": len(docs),
        "returned": min(len(docs), limit),
        "documents": [d.as_dict() for d in docs[:limit]],
    }
    return result


async def _async_update_dashboard(call: ServiceCall) -> ServiceResponse:
    """Regenerate the dashboard of every loaded account with a dashboard selected."""
    from .dashboard import async_update_dashboard

    written = []
    for entry in call.hass.config_entries.async_loaded_entries(DOMAIN):
        url = await async_update_dashboard(call.hass, entry)
        if url:
            written.append(url)
    return {"dashboards": written}


def async_setup_services(hass: HomeAssistant) -> None:
    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_UPDATE_DASHBOARD,
        _async_update_dashboard,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_DOCUMENTS,
        _async_get_documents,
        schema=GET_DOCUMENTS_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
