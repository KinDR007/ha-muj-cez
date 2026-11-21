# Self meter reading (samoodečet)

Submitting a customer meter reading and everything the web app reads around it. API package `@cz.cez.cpr.restapi/col-smr` 1.0.67, class `CPRCOLSMRApi`, generated client in `tools/probe/chunks/657.90594729.js`. The form, its validations and texts are in `2387.f2dd760f.js`; sagas (which call the API) in `1212.07eba32b.js`; shared enums (reason, status, method) are webpack modules `3617`, `83167`, `16796` (duplicated in several chunks, e.g. `2387`, `1212`).

All paths are relative to `https://muj.cez.cz/col-api/prod/1.0` and need the usual `Authorization: Bearer` (+ optional `X-COL-PARTNER`) headers, see [README](README.md).

Identifiers used here:

| Name | Meaning | Example (placeholder) |
|---|---|---|
| `supplyPointCode` | EAN of the supply point | `859182400000000000` |
| `supplyPointUid` | 40 char `supplyPointUniqueId` | `<supplyPointUid>` |
| `consumptionPlaceIdIsu` | ISU place id from `RetrieveSupplyPoints` | `<consumptionPlaceIdIsu>` |
| `deviceSerialNumber` / `meterReadingDeviceNumber` | meter serial number; the form defaults to `electricitySupplyPoint.supplyPointNumber` (gas: `gassSupplyPoint.supplyPointNumber`) of `GET /supply-points/{supplyPointId}/ReadSupplyPointDetail` | `<meterSerialNumber>` |
| `selfMeterReadingGuidIsu` | id of an existing reading request to attach the reading to, `""` for a new one | `<selfMeterReadingGuidIsu>` |

## Endpoints

| Method | Path | Operation | Purpose |
|---|---|---|---|
| POST | [`/self-meter-reading`](#post-self-meter-reading) | setSelfMeterReadingISU | **submit a reading** (multipart) |
| GET | [`/self-meter-reading`](#get-self-meter-reading) | readSelfMeterReadingRequestISU | reading history / last reading |
| DELETE | [`/self-meter-reading/delete`](#delete-self-meter-readingdelete) | deleteSelfMeterReading | delete a reading of a given day |
| GET | [`/self-meter-reading/form-config`](#get-self-meter-readingform-config) | getSelfMeterReadingFormConfig | allowed date range for a reason |
| POST | [`/self-meter-reading/validation`](#post-self-meter-readingvalidation) | validateSelfMeterReading | server validation (not called by the current UI) |
| GET | [`/meter-reading-consumption-vals`](#get-meter-reading-consumption-vals) | readSelfMeterReadingConsumptionVals | last billing consumption + limits (for "unusually high" and remaining count) |
| GET | [`/meter-reading-requests`](#get-meter-reading-requests) | readSelfMeterReadingRequestsCRM | open reading requests (processes waiting for a reading) |
| GET | [`/meter-reading-requests-advanced`](#get-meter-reading-requests-advanced) | readSelfMeterReadingRequestsCRMAdvanced | reading types (reasons) the customer may choose now |
| GET | [`/meter-reading-request`](#get-meter-reading-request) | readSelfMeterReadingRequestCRM | one request by `meterReadingIdIsu` |
| POST | [`/meter-reading-request`](#post-meter-reading-request) | createSelfMeterReadingRequestCRM | create request(s) (back office) |
| PUT | [`/meter-reading-request`](#put-meter-reading-request) | updateSelfMeterReadingRequestCRM | change a request (back office) |

Related, read only: `GET /supply-points/{supplyPointUid}/ReadMeterReading` (all readings of the meter including distributor readings, used by the integration, see [supply-points.md](supply-points.md#get-supply-pointssupplypointidreadmeterreading)) and `GET /supply-points/{supplyPointUid}/ReadSupplyPointDetail` (meter number, `doubleTariff`).

## Enums

### Reading reason (`selfMeterReadingReason.entryId`, `meterReadingReasonId`, `selfMeterReadingReasonId`)

Module `3617` (enum `z`), labels from the `TRANSLATE_PAYMENT_TYPE` messages:

| Code | Enum name | Label (cs) | Notes |
|---|---|---|---|
| `01` | EXTRA_INVOICE | Mimořádná faktura | extraordinary billing; "Mimořádné vyúčtování může být zpoplatněno dle ceníku distributora"; sub type `MO-31-12` = extra invoice for end of year; some distributors only allow the last day of a month |
| `02` | CONTROL_METERING | Kontrolní odečet | control reading for the distributor ("Přidat kontrolní odečet pro distributora"); limited count per year, see `Limits` |
| `03` | SUPPLIER_CHANGE | Odečet ke změně dodavatele | |
| `04` | METERING_FOR_REQUEST_WITHOUT_CHANGING_SUPPLIER | Odečet při přepisu bez ZD | |
| `05` | METERING_BEFORE_SUPPLY | Odečet před zahájením dodávky | |
| `06` | ESTIMATE_METERING | Odhad obchodníka k měsíční mimořádné fakturaci | supplier estimate, ignored by the value checks |
| `07` | ONE_STEP_CHANGE | Přepis odběrného místa | |
| `08` | DIARY_METERING | Deníkový odečet | diary reading; the UI calls it "Sledování spotřeby" (consumption tracking) and uses it for a plain reading with `selfMeterReadingGuidIsu: ""` |
| `10` | UNDECLARED_METERING | Neurčitý měsíční odečet | |
| `11` | DISTRIBUTION_DATA_CHANGE | Odečet pro změnu distribučních dat | |
| `12` | CONSUMPTION_RECALCULATION_METERING | Odečet pro přepočet spotřeby | |
| `13` | METERING_FOR_REPEAT_REJECTED_METERING | Odečet po zamítnutí | correction after rejection, photos (`contentHighTariff`/`contentLowTariff`) required |
| `14` | STATE_STATEMENT_DECREE_METERING | Odečet k informaci o vyúčtování | billing information ("Informace o vyúčtování budou vystaveny během 10 dnů") |
| `15` | DEVICE_CHANGE_ASSEMBLY / CEZ_DIST_SMR_INSTALL | Odečet distributora | |
| `16` | DEVICE_CHANGE_DISASSEMBLY / CEZ_DIST_SMR_UNINSTALL | Odečet distributora | |
| `17` | CEZ_DIST_SMR_SIGN_IN | Odečet distributora | |
| `18` | CEZ_DIST_SMR_CONTROL | Odečet distributora | |

Reason sub type (`meterReadingReasonSubTypeId`, module `37384`): `MO-31-12` (EXTRA_INVOICE_FOR_END_OF_YEAR).

### Reading status (`selfMeterReadingStatusId`, module `83167`)

| Code | Name | In progress (blocks another reading that day) |
|---|---|---|
| `0` | NO_COMMUNICATION | yes |
| `1` | ENTERED | yes |
| `2` | SENT_DSO | yes |
| `3` | CONFIRMED_DSO | yes |
| `4` | REJECTED | no |
| `5` | WAITING_FOR_PROCESSING | yes |
| `6` | NOT_SENT | no |
| `C` | CANCELLED | no |

### Reading method (`selfMeterReadingMethodId`, module `16796`, labels from module `44981`)

| Code | Label (cs) |
|---|---|
| `01`, `07`, `ZO` | Odhad distributora (distributor estimate) |
| `02`, `06`, `YS`, `ZS` | Odečet zákazníkem (customer reading) |
| `03`, `04`, `05` | ČEZ Prodej |
| `YO` | Odhad obchodníka k měsíční mimořádné fakturaci (supplier estimate) |
| `ZN` | Odečet distributora (distributor reading) |

### Distributor (module `26183`)

`CEZ-DI` (ČEZ Distribuce), `PRE-DI`, `EON-DI`, `EON-DI-PL` (EG.D), `RWE_GN-DI`, `PP-DI`, `NPPD-DI`, `-` unknown. Several rules differ for ČEZ Distribuce (see validations).

## POST /self-meter-reading

Submit a reading. Operation `setSelfMeterReadingISU`.

- Content type: `multipart/form-data` (the generated client builds a `FormData`; no explicit `Content-Type` header, the boundary is set by the HTTP library).
- Parts:
  - `selfMeterReadingRequestBody`: JSON (`Blob` with type `application/json`) = `SelfMeterReadingRequestBodyDto`, see below. Required in practice.
  - `contentHighTariff`: optional file, photo of the meter (VT / single tariff display).
  - `contentLowTariff`: optional file, photo of the NT display.
- Response JSON `SetSelfMeterReadingResponseDto`:
  - `activityId` (string, required)
  - `meterReadingImplausible` (boolean, required): values are unusual compared to the history (e.g. meter replaced). The success screen then says "Zadané hodnoty měřidla jsou neobvyklé vůči ostatním hodnotám, které u nás evidujeme (důvodem může být např. výměna měřidla)" and consumption charts/estimates wait until the next billing period.
  - `isAttachmentNeeded` (boolean, optional): ČEZ Distribuce rejected the values ("Distributor odečet zamítl", "Pokud jsou vámi zadané hodnoty správné, přiložte fotografii pro ověření."). The UI then offers to resubmit with photos (reason `13`).
- Errors: on failure the UI shows "Samoodečet nebyl uložen ... z technických důvodů se nám nepodařilo samoodečet uložit a odeslat distributorovi". Validation with ČEZ Distribuce can take up to 20 s ("Chvilku strpení, může to trvat až 20 vteřin").

### `SelfMeterReadingRequestBodyDto`

Serializer `U` in `657.90594729.js`. Required fields (`instanceOfSelfMeterReadingRequestBodyDto`): `selfMeterReadingReason`, `selfMeterReadingDescription`, `meterReadingDeviceNumber`, `meterReadingRegisterDate`, `selfMeterReadingGuidIsu`, `supplyPointCode`, `checkSnaps`.

| Field | Type | Meaning |
|---|---|---|
| `selfMeterReadingGuidIsu` | string | id of the request the reading belongs to (`guid` from `/meter-reading-requests` / `/self-meter-reading` / URL param `Guid`), `""` for a new reading |
| `selfMeterReadingReason` | `{entryId}` | reason code, table above |
| `meterReadingRegisterDate` | `YYYY-MM-DD` | reading date (local date; the app shifts by the timezone offset before `toISOString().substring(0,10)`, multi-SP form sets 03:00 local) |
| `meterReadingDeviceNumber` | string | meter serial number |
| `supplyPointCode` | string | EAN |
| `selfMeterReadingDescription` | string | note, max 160 characters ("Poznámka pro vás"), `""` when empty |
| `selfMeterReadingHighTariff` | `SmrHighTariffDto` | VT (T1) or the only register |
| `selfMeterReadingLowTariff` | `SmrLowTariffDto` | NT (T2); value `0` for single tariff meters |
| `selfMeterReadingStatus` | `{entryId, systemId, entrySystemSpecificId}` | `""` normally; for the supplier estimate flow the status of that request |
| `negativeMeterReadingFlag` | boolean | optional, not set by the web app |
| `checkSnaps` | boolean | `true`, except `false` for a supply point still in the activation process (and `true` in the multi supply point form) |

`SmrHighTariffDto` / `SmrLowTariffDto` (required `meterReadingUnit`, `meterReadingValue`, `meterReadingTariff`):

| Field | Type | Value sent by the web app |
|---|---|---|
| `meterReadingTariff` | CodebookEntryIdentifier | `{"entryId": "highTariff"}` / `{"entrySystemSpecificId": "", "systemId": "", "entryId": "lowTariff"}` |
| `meterReadingUnit` | CodebookEntryIdentifier | `{"entryId": ""}` (server fills the unit) |
| `meterReadingValue` | number | integer register value (kWh, gas m³), digits before the decimal point only |
| `meterReadingDocumentId` | string | optional; `""` or the ISU document id of the supplier estimate (`ablbelnrVt` / `ablbelnrNt`) when confirming it |

### Exact body sent by the web app (single supply point form)

From `submitSelfMeterReadingData` in `2387.f2dd760f.js`:

```json
{
  "selfMeterReadingGuidIsu": "",
  "selfMeterReadingLowTariff": {
    "meterReadingUnit": {"entryId": ""},
    "meterReadingTariff": {"entrySystemSpecificId": "", "systemId": "", "entryId": "lowTariff"},
    "meterReadingValue": 5432,
    "meterReadingDocumentId": ""
  },
  "selfMeterReadingHighTariff": {
    "meterReadingUnit": {"entryId": ""},
    "meterReadingTariff": {"entryId": "highTariff"},
    "meterReadingValue": 12345,
    "meterReadingDocumentId": ""
  },
  "selfMeterReadingReason": {"entryId": "08"},
  "meterReadingRegisterDate": "2026-11-21",
  "meterReadingDeviceNumber": "<meterSerialNumber>",
  "supplyPointCode": "859182400000000000",
  "selfMeterReadingDescription": "",
  "checkSnaps": true,
  "selfMeterReadingStatus": {"entryId": "", "systemId": "", "entrySystemSpecificId": ""}
}
```

The multi supply point form (bulk / CSV import, chunk `2387`) sends the same structure with `selfMeterReadingReason.entryId = "02"` (CONTROL_METERING), `checkSnaps: true` and no `meterReadingDocumentId`.

Example request (Python, aiohttp):

```python
form = aiohttp.FormData()
form.add_field("selfMeterReadingRequestBody", json.dumps(body), content_type="application/json")
# optional: form.add_field("contentHighTariff", jpeg_bytes, filename="vt.jpg", content_type="image/jpeg")
await session.post(f"{api}/self-meter-reading", data=form, headers=auth_headers)
```

### Client side validations (web app)

| Rule | Where | Message (cs) |
|---|---|---|
| value required, integer, `min 0`, max 9 digits, no `.` or `e` (`{maxLength: 9, min: 0, pattern: /^[^.e]*$/}`) | `aR`/`U` in `2387` | "Maximální délka je 9 číslic.", "Povinné pole, nejsou povoleny speciální znaky." |
| note max 160 characters (counter `n/160`) | `2387` | |
| device number at least 2 characters (submit disabled otherwise); different number than the registered meter asks "Evidujeme jiné číslo měřidla než je načteno, došlo u Vás k výměně měřidla?" | `2387` | |
| date within `meterReadingMinDate` .. `meterReadingMaxDate` of form-config; picker hidden/disabled per `isDatePickerVisible` / `isDateChangeDisabled` | `2387` | |
| one reading per day: invalid if a reading already exists that day with reason in {`01`,`02`,`13`,`14`,`15`-`18`}, method not `YO`, reason not `08`, and status `""` or in progress (`0`,`1`,`2`,`3`,`5`) | module `11385` | "Pro toto datum jste stavy zadali. V jeden den je možné zaznamenat stavy pouze jednou." |
| lower than previous: value < VT/NT value of the nearest older reading (history from `GET /self-meter-reading`, ignoring reason `06` and method `ZO`) | `F` in `2387` | "Hodnota je nižší než předchozí stav ze dne {date} ({value} kWh)"; "Stav elektroměru je nižší, než předchozí" |
| higher than newer: value > nearest newer reading (not for ČEZ Distribuce) | `F` | "Hodnota je vyšší než novější stav ze dne {date} ({value} kWh)"; confirmation dialog "Došlo k výměně měřidla?" |
| unusually high (not for ČEZ Distribuce): `value > lastCons / LastBillPeriod * days(date - previousReadingDate) * 1.5 + previousValue`, with `lastConsVT` or `lastConsNT` and `LastBillPeriod` from `/meter-reading-consumption-vals` (assumed: consumption of the last billing period and its length in days) | `F` | "Hodnota je nezvykle vysoká" |
| ČEZ Distribuce: only the "lower than previous" check, and it blocks the form (validator returns the message) | `U` in `2387` | |
| remaining control readings: `Limits` item with `smrType == reason` and `period == "YEAR"`: remaining = `limitMax - limitActual`; reason `02` blocked when remaining < 1 | module `98342` | "Do ročního vyúčtování vám můžeme zohlednit {maxLimit} samoodečtů.", "V tomto ročním vyúčtování vám další stavy elektroměrů nemůžeme zobrazit. Limit je již vyčerpán." |
| photos: total size of both attachments max 25 MB; reason `13` requires the photo(s) | `2387` | "Přílohy přesahují maximální povolenou velikost 25MB" |

The two warnings ("lower than previous", "unusually high") are client side only for distributors other than ČEZ Distribuce; the server may still accept the reading and flag it with `meterReadingImplausible`.

## GET /self-meter-reading

Reading history (ISU). Operation `readSelfMeterReadingRequestISU`. All query params optional:

| Param | Type | Notes |
|---|---|---|
| `supplyPointCode` | string | EAN |
| `consumptionPlaceIdIsu` | string | the web app calls it with this and `meterReadingRequestRegisterDate=<today>` to load the history for the form |
| `meterReadingRequestRegisterDate` | `YYYY-MM-DD` | |
| `deviceSerialNumber` | string | |
| `isLastAvailable` | boolean | `true` returns only the last reading |
| `isSnap` | boolean | |

Response: array of `MeterReadingHistoryDto`:

| Field | Type | Notes |
|---|---|---|
| `meterReadingRequestRegisterDate` | `YYYY-MM-DD` | reading date |
| `meterReadingValueHT` | number | VT / single register |
| `meterReadingValueLT` | number | NT (`0` single tariff) |
| `meterReadingDoubleTariffFlag` | boolean | |
| `deviceSerialNumber` | string | meter serial |
| `meterNumber` | string | |
| `meterReadingTariff`, `consumptionTariff`, `meterReadingUnit` | CodebookEntry | unit `KWH` |
| `selfMeterReadingGuidIsu` | string | 32 hex chars (all zeros seen) |
| `selfMeterReadingReasonId` | string | reason code |
| `selfMeterReadingStatusId` | string | status code |
| `selfMeterReadingMethodId` | string | method code |
| `selfMeterReadingTypeId` | string | e.g. `02` |
| `selfMeterReadingSourceId` | string | e.g. `P` |
| `meterReadingTypeId` | string | |
| `selfMeterReadingInvoiced` | boolean | already used in a settlement |
| `attachExist` | boolean | photo attached |
| `note` | string | |
| `ablbelnrVt`, `ablbelnrNt` | string | ISU document ids (supplier estimate) |

Captured sample (probe_out `self-meter-reading_supplyPointCode=<ean>&isLastAvailable=true`), anonymized:

```json
[
 {
  "meterReadingTariff": {"entryId": "0E-14"},
  "meterReadingUnit": {"entryId": "KWH"},
  "ablbelnrVt": "",
  "attachExist": false,
  "note": "",
  "deviceSerialNumber": "<meterSerialNumber>",
  "meterReadingValueHT": 12345,
  "meterNumber": "",
  "consumptionTariff": {"entryId": "0E-14"},
  "ablbelnrNt": "",
  "selfMeterReadingGuidIsu": "00000000000000000000000000000000",
  "meterReadingValueLT": 0,
  "selfMeterReadingSourceId": "P",
  "meterReadingRequestRegisterDate": "2026-11-16",
  "selfMeterReadingTypeId": "02",
  "selfMeterReadingInvoiced": false,
  "selfMeterReadingStatusId": "0",
  "selfMeterReadingReasonId": "08",
  "selfMeterReadingMethodId": "ZS",
  "meterReadingDoubleTariffFlag": false
 }
]
```

(Codebook objects also carry `"@class": "cz.cez.cpr.restapi.common.v1_0.dto.CodebookEntryDto"`.)

## DELETE /self-meter-reading/delete

Operation `deleteSelfMeterReading`. JSON body `DeleteSMRRequestBodyDto` (both required):

```json
{"supplyPointCode": "859182400000000000", "meterReadingRegisterDate": "2026-11-21"}
```

Response empty. The web app deletes by supply point and day (hook `deleteMeterReading(supplyPointCode, date)` in `1806`/`1940`/`2387` chunks).

## GET /self-meter-reading/form-config

Operation `getSelfMeterReadingFormConfig`. Query:

| Param | Required | Notes |
|---|---|---|
| `meterReadingReasonId` | yes | reason code |
| `meterReadingReasonSubTypeId` | no | e.g. `MO-31-12` |
| `meterReadingRegisterDate` | no | `YYYY-MM-DD` (date of the request) |
| `supplyPointCode` | no | EAN (the web app sends it; query only runs when reason and EAN are known) |
| `supplyPointUid` | no | |
| `ticketTaskGuid` | no | task id when the reading belongs to a case |

Response `SelfMeterReadingFormConfigDto` (all required): `isDatePickerVisible` (boolean), `isDateChangeDisabled` (boolean), `meterReadingDefaultDate`, `meterReadingMinDate`, `meterReadingMaxDate` (`YYYY-MM-DD`).

## POST /self-meter-reading/validation

Operation `validateSelfMeterReading`. JSON body `{"supplyPointCode": "859182400000000000"}`. Response JSON or text (the client accepts both). Defined in the client but not called anywhere in the current bundle.

## GET /meter-reading-consumption-vals

Operation `readSelfMeterReadingConsumptionVals`. Query `supplyPointCode` (required). Response `SmrConsumptionValsDto` (note the capitalized wire names):

| Field | Type | Notes |
|---|---|---|
| `dateFrom`, `dateTo` | `YYYY-MM-DD` | last billing period |
| `lastConsVT`, `lastConsNT` | number | consumption in that period |
| `LastBillPeriod` | number | used as divisor (days, assumed) |
| `distributionRegion` | string | |
| `Limits` | array of `LimitsDto` | |

`LimitsDto`: `smrType` (reason code), `period` (`DAY` or `YEAR`, required), `limitActual` (number, required), `limitMax` (number, required), `types`, `statuses`, `checkLow`, `checkHigh`, `esbValidate`, `takeoverNotif`.

## GET /meter-reading-requests

Open reading requests of a supply point (e.g. a supplier change waiting for a reading). Operation `readSelfMeterReadingRequestsCRM`. Query: `supplyPointCode` (required), `readOnlyActiveRequests` (boolean), `isWaitingForMeterReading` (boolean), `meterReadingRequestRegisterDate` (`YYYY-MM-DD`). The form calls it with `readOnlyActiveRequests=true&isWaitingForMeterReading=true`; if there are requests, it asks "K čemu chcete stavy využít?" and the chosen request supplies `selfMeterReadingGuidIsu`, the reason and the date; "Sledování spotřeby" = reason `08` with guid `""`.

Response array of `SelfMeterReadingRequestsDto`: `meterReadingRequestId`, `meterReadingRequestStatus` (CodebookEntry), `meterReadingRequestGuidCrm`, `supplyPointCode`, `meterReadingRequestValidFrom`, `meterReadingRequestValidTo`, `meterReadingRequestRegisterDate` (`YYYY-MM-DD`), `meterReadingRequestCreateDate` (date-time), `meterReadingDateFixed` (boolean), `selfMeterReadingReason` (CodebookEntry), `selfMeterReadingRejectionReasionId` (sic), `selfMeterReadingGuidIsu`, `suppressNotifications`, `ticketTaskGuid`.

Captured (probe_out `meter-reading-requests_supplyPointCode=<ean>&readOnlyActiveRequests=true`): `[]`.

## GET /meter-reading-requests-advanced

Reading types offered on the "Vyberte typ samoodečtu" screen. Operation `readSelfMeterReadingRequestsCRMAdvanced`. Query: `supplyPointCode` (required), `meterReadingRequestRegisterDate`.

Response array of `SelfMeterReadingRequestsCRMAdvancedsDto`: `meterReadingReasonId` (required), `meterReadingReasonEnabled` (boolean, required), `meterReadingReasonName` (required), `meterReadingReasonDescription` (required), `meterReadingReasonSubTypeId`, `reasonId`, `reasonName`, `reasonDescription`, `reasonEnabled`, `reasonSubType`, `reasonDate`, `reasonShowFrom`, `reasonShowTo` (`YYYY-MM-DD`). The UI lists only items with `meterReadingReasonEnabled`; an `01` item with sub type `MO-31-12` is the end of year extra invoice.

## GET /meter-reading-request

Operation `readSelfMeterReadingRequestCRM`. Query `meterReadingIdIsu` (required). Response `SelfMeterReadingRequestDto`: `meterReadingIdIsu`, `meterReadingRequestStatus` (CodebookEntry), `selfMeterReadingGuidIsu`, `meterReadingRequestGuidCrm`, `suppressNotifications`, `partnerIdCrm`, `supplyPointCode`, `meterReadingDateFixed`, `meterReadingRequestValidFrom`, `meterReadingRequestValidTo`, `meterReadingRequestCreateDate`, `selfMeterReadingRejectionReasionId`.

## POST /meter-reading-request

Operation `createSelfMeterReadingRequestCRM` (not used by the customer UI). JSON **array** of `CreateSelfMeterReadingRequestRequestBodyDto`: `supplyPointCode`, `meterReadingRequestReason` (`{entryId}`), `meterReadingRequestRegisterDate` (`YYYY-MM-DD`), `partnerIdCrm` (all required), `meterReadingRequestValidFrom`, `meterReadingRequestValidTo`. Response array of `{selfMeterReadingGuidIsu, meterReadingIdIsu, createSelfMeterReadingSuccess, errorMessage}`.

## PUT /meter-reading-request

Operation `updateSelfMeterReadingRequestCRM` (not used by the customer UI). JSON body `{selfMeterReadingGuidIsu, meterReadingRequestRegisterDate, meterReadingRequestValidFrom?, meterReadingRequestValidTo?}` (dates `YYYY-MM-DD`). Response `{updateSelfMeterReadingSuccess}`.

## Web app flow (summary)

1. Load supply point detail (`ReadSupplyPointDetail`: meter number, `doubleTariff`), history (`GET /self-meter-reading?consumptionPlaceIdIsu=...&meterReadingRequestRegisterDate=<today>`), consumption values (`/meter-reading-consumption-vals`), open requests (`/meter-reading-requests?...readOnlyActiveRequests=true&isWaitingForMeterReading=true`) and offered types (`/meter-reading-requests-advanced`).
2. Choose reason (and request guid), then `GET /self-meter-reading/form-config` for the date range.
3. Validate on the client (table above), `POST /self-meter-reading` (multipart).
4. If `isAttachmentNeeded`, resubmit with photos; if `meterReadingImplausible`, show the "unusual values" note.

## Verified against real responses (2026-11, two accounts, read only)

- `/meter-reading-consumption-vals`: `lastConsVT` / `lastConsNT` are kWh of the last billing
  period, `LastBillPeriod` its length in days (annual billing 356, monthly 30);
  `distributionRegion` is `"CEZ"` for ČEZ Distribuce. `Limits` holds a `DAY` and a `YEAR` item
  per reason `01`–`18`; observed `limitMax` 1 per day and 20 per year for `01`, `02`, `14`, 0 for
  the others; extra fields `types` (`"01;02;11;12;13;14"`), `statuses`, `esbValidate`,
  `takeoverNotif`, `checkLow` / `checkHigh` (50).
- `/self-meter-reading/form-config`: `meterReadingMaxDate` = today, `meterReadingMinDate`
  = today − 30 days for `02`, `08`, `14` and today − 8 days for `01`.
- `/meter-reading-requests-advanced`: the offered reasons differ per supply point (e.g. `14`
  missing on a monthly billed point with PV).
- `/self-meter-reading?supplyPointCode=`: all readings of the meter, distributor readings have
  an empty `selfMeterReadingReasonId` / `selfMeterReadingStatusId` (method `ZN`), customer
  readings reason `08` with status `0` and method `ZS`.
- `POST /self-meter-reading` (diary reading `08`, single tariff, JSON part as above, no
  photos): HTTP 200 with `{"activityId": "", "isAttachmentNeeded": false}`
  (`meterReadingImplausible` missing). The reading appears in `GET /self-meter-reading` right
  away: reason `08`, status `0`, method `ZS`, source `P`, `note` = `selfMeterReadingDescription`,
  and in `ReadMeterReading` as `ODE_SAMO`.
