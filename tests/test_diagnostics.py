"""Diagnostics: pseudonymized raw portal data for issue reports."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.muj_cez.anonymize import Anonymizer
from custom_components.muj_cez.api import CezConnectionError
from custom_components.muj_cez.const import CONF_PARTNER, DOMAIN
from custom_components.muj_cez.diagnostics import async_get_config_entry_diagnostics

from .conftest import PASSWORD, UID, USERNAME, load

OWN, SHARED = "0011111111", "0022222222"
TOKEN = {
    "individualFirstName": "Jan",
    "individualSurname": "Novák",
    "partners": [SHARED, OWN],
    "defaultPartner": SHARED,
    "email": USERNAME,
    "roleName": ["ZCOL_ZAK"],
}


def test_anonymizer_keeps_structure_and_relations() -> None:
    anon = Anonymizer()
    data = {
        "supplyPointCode": "859100000000000001",
        "consumptionPlaceName": "Testovací 123",
        "meterReadingValue": 13160.0,
        "meterReadingRegisterDate": "2026-10-31T00:00:00Z",
        "meterReadingTariff": {"entryId": "NT", "value": "Nízký tarif"},
        "path": "/supply-points/0000111111110002222222859100000000000001/x",
        "partnerIdCrm": OWN,
        "flag": True,
        "address": {
            "addressCity": {"@class": "cz.cez.CodebookEntryDto", "value": "Horní Dolní"},
            "addressStreet": {"value": "Polní"},
        },
    }
    out = anon(data)
    text = json.dumps(out, ensure_ascii=False)
    for secret in (
        "859100000000000001",
        "Testovací",
        OWN,
        "0000111111110002222222",
        "Horní",
        "Polní",
    ):
        assert secret not in text
    assert out["meterReadingValue"] == 13160.0 and out["flag"] is True
    assert out["meterReadingRegisterDate"].startswith("2026-10-31")
    assert out["meterReadingTariff"] == {"entryId": "NT", "value": "Nízký tarif"}
    assert out["address"]["addressCity"]["@class"] == "cz.cez.CodebookEntryDto"
    assert len(out["supplyPointCode"]) == 18
    # The same value gets the same placeholder in another response.
    assert anon({"ean": "859100000000000001"})["ean"] == out["supplyPointCode"]
    assert anon(OWN, "partner") == out["partnerIdCrm"]


async def test_diagnostics_portal_section(hass: HomeAssistant, mock_client: AsyncMock) -> None:
    raw = {
        "/user/token-data": TOKEN,
        "/supply-points/RetrieveSupplyPoints": load("supply_points.json"),
        f"/supply-points/{UID}/ReadMeterReading": load("meter_readings.json"),
    }

    async def get_raw(path: str, params: object = None) -> object:
        if path not in raw:
            raise CezConnectionError(f"GET {path}: HTTP 404")
        return raw[path]

    mock_client.get_raw.side_effect = get_raw
    mock_client.get_accounts.return_value = ([SHARED, OWN], SHARED)
    mock_client.with_partner.return_value = mock_client
    mock_client.partner = OWN
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=f"{USERNAME} ({OWN})",
        unique_id=f"{USERNAME}_{OWN}",
        data={CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD, CONF_PARTNER: OWN},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    diag = await async_get_config_entry_diagnostics(hass, entry)
    text = json.dumps(diag, ensure_ascii=False, default=str)
    sp = load("supply_points.json")[0]
    for secret in (
        USERNAME,
        PASSWORD,
        OWN,
        SHARED,
        "Novák",
        sp["supplyPointCode"],
        UID,
        sp["consumptionPlaceName"],  # contract names of documents are the address
    ):
        assert secret not in text, secret
    portal = diag["portal"]
    assert [a["default"] for a in portal["accounts"]] == [True, False]
    assert portal["selected_account"] == portal["accounts"][1]["partner"]
    assert len(portal["accounts"][0]["supply_points"]) == len(sp and load("supply_points.json"))
    readings = next(iter(portal["meter_readings"].values()))
    assert readings and all("simulaci" not in json.dumps(r, ensure_ascii=False) for r in readings)
    assert portal["token_data"]["roleName"] == ["ZCOL_ZAK"]
