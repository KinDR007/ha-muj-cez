"""Invoice store (download once, CSV first, PDF fallback) and the prices websocket command."""

from __future__ import annotations

from datetime import date
from typing import Any
from unittest.mock import AsyncMock, patch

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.typing import WebSocketGenerator

from custom_components.muj_cez import api, pricing
from custom_components.muj_cez.const import DOMAIN

from .conftest import FIXTURES, PASSWORD, UID, USERNAME, sample_data

AGREEMENT = "000011111111"


def _row(number: str, kind: str = "INV", agreement: str = AGREEMENT) -> dict[str, Any]:
    return {
        "billingReceivablesAndPayablesAccountDocumentNumber": number,
        "billingAccountingDocumentType2": kind,
        "agreementIdIsu": agreement,
        "billingAccountingDocumentDate": "2026-02-19",
        "billingSourceSystem": "RTT",
        "partnerIdCrm": "0011111111",
        "billingAccountingDocumentHeaderId": 11,
        "billingBalanceSnapshotId": "1",
    }


def _client() -> AsyncMock:
    client = AsyncMock(spec=api.CezClient)
    client.get_invoice_rows.return_value = [
        _row("A1"),  # CSV
        _row("A2"),  # no CSV, PDF
        _row("A3"),  # nothing
        _row("X1", agreement="000099999999"),  # other contract (e.g. gas)
        _row("S1", kind="SLF"),  # payout type on a consumption contract: skipped
    ]
    csv = (FIXTURES / "invoice_settlement.csv").read_text()
    client.get_invoice_csv.side_effect = lambda row: (
        csv if row["billingReceivablesAndPayablesAccountDocumentNumber"] == "A1" else None
    )
    client.get_invoice_pdf.side_effect = lambda row: (
        b"%PDF" if row["billingReceivablesAndPayablesAccountDocumentNumber"] == "A2" else None
    )
    return client


async def test_store_downloads_once(hass: HomeAssistant, hass_storage: dict[str, Any]) -> None:
    store = pricing.InvoiceStore(hass, "e1")
    client = _client()
    text = (FIXTURES / "invoice_settlement_pdf.txt").read_text()
    with (
        patch.object(pricing, "pdf_text", return_value=text),
        patch.object(pricing, "REQUEST_PAUSE", 0),
    ):
        assert await store.async_update(client, sample_data(), date(2026, 3, 1)) == 2
        saved = hass_storage[f"{DOMAIN}.e1.invoices"]["data"]
        assert set(saved["invoices"]) == {"A1", "A2"}
        assert saved["invoices"]["A1"]["invoice"]["source"] == "csv"
        assert saved["invoices"]["A2"]["invoice"]["source"] == "pdf"
        assert saved["invoices"]["A1"]["invoice"]["issued"] == "2026-02-19"
        assert not saved["invoices"]["A1"]["invoice"]["corrective"]
        assert saved["failed"] == {"A3": "2026-03-01"}
        assert client.get_invoice_rows.call_args.args == (date(2022, 1, 1),)

        # next day: nothing downloaded again, the failed one waits RETRY_DAYS
        client.get_invoice_csv.reset_mock()
        client.get_invoice_pdf.reset_mock()
        assert await store.async_update(client, sample_data(), date(2026, 3, 2)) == 0
        assert not client.get_invoice_csv.called and not client.get_invoice_pdf.called
        await store.async_update(client, sample_data(), date(2026, 3, 9))
        assert [
            c.args[0]["billingReceivablesAndPayablesAccountDocumentNumber"]
            for c in client.get_invoice_pdf.call_args_list
        ] == ["A3"]

    invoices = await pricing.InvoiceStore(hass, "e1").async_invoices({AGREEMENT})
    assert sorted(i.number for i in invoices) == ["A1", "A2"]
    assert await store.async_invoices({"nope"}) == []


async def test_store_corrective_and_old_entries(
    hass: HomeAssistant, hass_storage: dict[str, Any]
) -> None:
    store = pricing.InvoiceStore(hass, "e3")
    client = _client()
    row = _row("A1") | {"billingAccountingDocumentTypeText": "Opravná faktura - přeplatek"}
    client.get_invoice_rows.return_value = [row]
    with patch.object(pricing, "REQUEST_PAUSE", 0):
        await store.async_update(client, sample_data(), date(2026, 3, 1))
    (parsed,) = await store.async_invoices({AGREEMENT})
    assert parsed.corrective and parsed.issued == date(2026, 2, 19)
    # entry of the first version: date and type only in the wrapper
    data = await store._load()
    entry = data["invoices"]["A1"]
    del entry["invoice"]["issued"], entry["invoice"]["corrective"]
    (parsed,) = await store.async_invoices({AGREEMENT})
    assert parsed.corrective and parsed.issued == date(2026, 2, 19)


async def test_store_error_marks_failed(hass: HomeAssistant) -> None:
    store = pricing.InvoiceStore(hass, "e2")
    client = _client()
    client.get_invoice_rows.return_value = [_row("A1")]
    client.get_invoice_csv.side_effect = api.CezConnectionError("boom")
    with patch.object(pricing, "REQUEST_PAUSE", 0):
        assert await store.async_update(client, sample_data(), date(2026, 3, 1)) == 0
    assert (await store._load())["failed"] == {"A1": "2026-03-01"}


async def test_websocket_prices(
    hass: HomeAssistant, hass_ws_client: WebSocketGenerator, mock_client: AsyncMock
) -> None:
    csv = (FIXTURES / "invoice_settlement.csv").read_text()
    mock_client.get_invoice_rows.return_value = [_row("A1")]
    mock_client.get_invoice_csv.return_value = csv
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=USERNAME, data={CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD}
    )
    entry.add_to_hass(hass)
    with patch.object(pricing, "REQUEST_PAUSE", 0):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done(wait_background_tasks=True)

    from homeassistant.helpers import entity_registry as er

    sensor = next(
        e.entity_id
        for e in er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
        if e.unique_id.startswith(f"{UID}_")
    )
    ws = await hass_ws_client(hass)
    await ws.send_json({"id": 1, "type": f"{DOMAIN}/prices", "entity_id": sensor})
    result = (await ws.receive_json())["result"]
    assert result["invoices"][0]["number"] == "A1"
    months = {m["month"]: m for m in result["months"]}
    assert months["2025-07"]["source"] == "invoice"
    assert any(m["source"] in ("simulation", "mixed") for m in result["months"])
    assert result["vat_rate"] == 21

    await ws.send_json({"id": 2, "type": f"{DOMAIN}/prices", "entity_id": "sensor.nope"})
    assert not (await ws.receive_json())["success"]


async def test_store_pricelists(hass: HomeAssistant, hass_storage: dict[str, Any]) -> None:
    import json

    frags = [tuple(f) for f in json.loads((FIXTURES / "pricelist_fragments.json").read_text())]
    store = pricing.InvoiceStore(hass, "e4")
    client = _client()
    client.get_invoice_rows.return_value = []
    client.get_price_lists.return_value = [
        {"doc_id": "C1", "guid": "g1", "name": "Ceník produktu", "valid_from": "2026-01-30"},
        {"doc_id": "C2", "guid": "g2", "name": "Ceník jiný", "valid_from": "2025-01-01"},
    ]
    client.get_document_pdf.side_effect = lambda guid: b"%PDF" if guid == "g1" else None
    data = sample_data()
    sp = next(iter(data.supply_points.values())).supply_point
    with (
        patch.object(pricing, "pdf_fragments", return_value=frags),
        patch.object(pricing, "REQUEST_PAUSE", 0),
    ):
        await store.async_update(client, data, date(2026, 3, 1))
        saved = hass_storage[f"{DOMAIN}.e4.invoices"]["data"]
        assert set(saved["pricelists"]) == {"C1"} and saved["failed"] == {"cen:C2": "2026-03-01"}
        assert client.get_price_lists.call_args.args == (sp,)
        (pl,) = await store.async_pricelists(sp.ean)
        assert pl.product == "Elektřina - na 2 roky v akci"
        assert await store.async_pricelists("other") == []
        client.get_document_pdf.reset_mock()
        await store.async_update(client, data, date(2026, 3, 2))
        assert not client.get_document_pdf.called  # stored / failed recently
        client.get_price_lists.side_effect = api.CezConnectionError("down")
        await store.async_update(client, data, date(2026, 3, 3))  # does not raise


async def test_disabled_price_breakdown(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    hass_storage: dict[str, Any],
    mock_client: AsyncMock,
) -> None:
    """Off: no invoice requests, stored invoices deleted, websocket refuses, no tab."""
    from custom_components.muj_cez import dashboard
    from custom_components.muj_cez.const import CONF_PRICE_BREAKDOWN

    hass_storage[f"{DOMAIN}.off.invoices"] = {
        "version": 1,
        "key": f"{DOMAIN}.off.invoices",
        "data": {"invoices": {"A1": {}}, "failed": {}, "pricelists": {}},
    }
    entry = MockConfigEntry(
        domain=DOMAIN,
        entry_id="off",
        unique_id=USERNAME,
        data={CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD},
        options={CONF_PRICE_BREAKDOWN: False},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)

    assert not mock_client.get_invoice_rows.called
    assert not mock_client.get_price_lists.called
    assert f"{DOMAIN}.off.invoices" not in hass_storage
    from homeassistant.helpers import entity_registry as er

    sensor = next(
        e.entity_id
        for e in er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
        if e.unique_id.startswith(f"{UID}_")
    )
    ws = await hass_ws_client(hass)
    await ws.send_json({"id": 1, "type": f"{DOMAIN}/prices", "entity_id": sensor})
    reply = await ws.receive_json()
    assert not reply["success"] and reply["error"]["code"] == "disabled"
    views = dashboard.build_views(hass, entry.entry_id, entry.runtime_data.data, prices=False)
    assert [v["path"] for v in views] == ["cez", "cez-odecet"]


async def test_pypdf_installed_on_demand(hass: HomeAssistant) -> None:
    from homeassistant.exceptions import HomeAssistantError

    store = pricing.InvoiceStore(hass, "e5")
    client = _client()
    client.get_invoice_rows.return_value = [_row("A2")]
    with (
        patch.object(pricing, "REQUEST_PAUSE", 0),
        patch.object(pricing, "async_process_requirements", AsyncMock()) as req,
        patch.object(pricing, "pdf_text", return_value="x"),
    ):
        await store.async_update(client, sample_data(), date(2026, 3, 1))
        assert req.call_args.args[1:] == (DOMAIN, [pricing.PYPDF_REQUIREMENT])
        assert req.call_args.kwargs == {"is_built_in": False}
    store = pricing.InvoiceStore(hass, "e6")
    with (
        patch.object(pricing, "REQUEST_PAUSE", 0),
        patch.object(
            pricing, "async_process_requirements", AsyncMock(side_effect=HomeAssistantError("no"))
        ),
        patch.object(pricing, "pdf_text") as text,
    ):
        assert await store.async_update(client, sample_data(), date(2026, 3, 1)) == 0
        assert not text.called  # no parsing without pypdf; marked failed, retried later
        assert (await store._load())["failed"] == {"A2": "2026-03-01"}
