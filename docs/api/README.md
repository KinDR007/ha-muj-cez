# Můj ČEZ portal API (offline reference)

Reference of the REST API behind the Můj ČEZ customer portal (`https://muj.cez.cz/col`), reconstructed offline from the portal's React bundle (release `col-fe@3.66.0`, generated OpenAPI `typescript-fetch` clients) and from responses captured by the probe scripts. It is meant for developing the Home Assistant integration (`custom_components/muj_cez/api.py`) without querying the live portal.

Nothing here is an official specification. Field lists come from the generated (de)serializers, so they are complete for what the web app knows, but types are mostly inferred and many fields are optional.

All examples are anonymized: `859182400000000000` = EAN, `<supplyPointUid>` = 40 character supply point id, `000000000000` = 12 digit agreement/partner number, `<...>` = other ids.

## Base URLs

`https://muj.cez.cz/col/config.js` defines the runtime config (`window._env_`-style `KEY: "value"` pairs):

| Config key | Use |
|---|---|
| `REACT_APP_API_URL` | **COL API**, `https://muj.cez.cz/col-api/prod/1.0`. Everything in these docs unless marked otherwise. |
| `REACT_APP_ANONYMOUS_API_URL` | public part (registration, PayU callbacks, public outages, customer centers). |
| `REACT_APP_AUTHORIZATION_ENDPOINT` | `https://auth.cez.cz/oauth2/authorize` |
| `REACT_APP_TOKEN_ENDPOINT` | `https://api.cez.cz/token` |
| `REACT_APP_CONSUMER_KEY` | OAuth2 `client_id` (public, read it from config.js at runtime) |
| `REACT_APP_DOC_API_URL`, `REACT_APP_DOC_CASE_API_URL`, `REACT_APP_CAMUNDA_API_URL`, `REACT_APP_FEE_API_URL`, `REACT_APP_VALIDATION_API_URL`, `REACT_APP_WHISPERER_API_URL`, `REACT_APP_CODEBOOK_API_URL` | other back ends used by internal/agent screens, listed at the end of [other.md](other.md) |

The generated clients build URLs as `basePath + path` with path params URL-encoded (`"/supply-points/{supplyPointId}/ReadMeterReading".replace("{supplyPointId}", encodeURIComponent(...))`) and the query string from defined parameters only; dates in query params are `YYYY-MM-DD` (`toISOString().substr(0,10)`), booleans `true`/`false`.

## Authentication

OAuth2 authorization code flow with PKCE (implemented in `api.py` `CezClient._login`):

1. `GET {AUTHORIZATION_ENDPOINT}?client_id=<client_id>&redirect_uri=https://muj.cez.cz/col&scope=openid%20device_<uuid4>&response_type=code&code_challenge=<S256>&code_challenge_method=S256` returns the CAS login page (`form#fm1`, hidden `execution`).
2. `POST` the form (`username`, `password`, `execution`, `_eventId=submit`, `geolocation=`) without following redirects, then follow `Location` headers until one starts with `https://muj.cez.cz/col` and carries `?code=`. The login form shown again means wrong credentials.
3. `POST {TOKEN_ENDPOINT}` (form): `grant_type=authorization_code`, `code`, `client_id`, `redirect_uri`, `code_verifier`, `scope`. Response: `access_token`, `refresh_token`, `id_token`, `scope`, `token_type` (`Bearer`), `expires_in` (900 s).
4. Refresh: `POST {TOKEN_ENDPOINT}` with `grant_type=refresh_token`, `refresh_token`, `client_id`, `redirect_uri`.

## Common request headers

| Header | Value |
|---|---|
| `Authorization` | `Bearer <access_token>` |
| `Accept` | `application/json` (`*/*` for file downloads) |
| `X-COL-PARTNER` | selected customer account (`partnerIdCrm`, see `GET /user/token-data` `partners`); the web app always sends it (empty string = default account). The integration sends it only when an account is chosen. |
| `X-Correlation-Id` | random UUID v4 per request (sent by the web app, optional) |
| `X-COL-USER-CLIENT` | `mc-web` or `mc-mobile` (web app, optional) |
| `X-COL-APPID`, `X-COL-ACTIVE-ROLES`, `X-COL-SIMULATED-USER` | internal (agent/simulation), not needed |
| `Content-Type` | `application/json` for JSON bodies; multipart endpoints (self meter reading, complaints, uploads) use `multipart/form-data` with a JSON part |

## Conventions

### Identifiers

| Name | Format | Where it comes from |
|---|---|---|
| `supplyPointCode`, `consumptionPlaceId` | EAN, 18 digits `859182400000000000` | `RetrieveSupplyPoints[].supplyPointCode` |
| `supplyPointId` / `supplyPointUid` / `supplyPointUniqueId` (path param of `/supply-points/{supplyPointId}/...`, `/advance-payments/{supplyPointId}/...`, TAPP `supplyPointUid`) | 40 digits: 12 digit agreement + 10 digits + EAN | `RetrieveSupplyPoints[].supplyPointUniqueId` |
| `agreementIdIsu` | 12 digits | `RetrieveSupplyPoints[].agreement.agreementIdIsu` |
| `partnerIdCrm` | 10 digits | `GET /user/token-data` |
| `consumptionPlaceIdIsu`, `supplyPointNumber` | ISU place id / meter serial | `RetrieveSupplyPoints`, `ReadSupplyPointDetail` |

### Codebook entries

Enumerations are transferred as codebook objects (`CodebookEntryDto`, Java class `cz.cez.cpr.restapi.common.v1_0.dto.CodebookEntryDto`, serialized with `"@class"`):

```json
{
 "@class": "cz.cez.cpr.restapi.common.v1_0.dto.CodebookEntryDto",
 "entryId": "KWH",
 "entrySystemSpecificId": "KWH",
 "systemId": "ODS",
 "codebookId": "TP_UNIT",
 "value": "kWh",
 "longValue": "N/A",
 "entryOrder": 1,
 "language": "CZ",
 "validFrom": "0999-12-31T23:02:16Z",
 "validTo": "2999-12-30T23:00:00Z",
 "otherValues": [{"key": "...", "value": "..."}]
}
```

Only `entryId` is reliably present; many responses carry just `{"value": "..."}` or `{"entryId": "..."}`. A hierarchical variant adds `parentCodebookEntry`. In request bodies the identifier form `CodebookEntryIdentifierDto` = `{"entryId": "...", "systemId"?: "...", "entrySystemSpecificId"?: "..."}` is used. Whole codebooks: `GET /codebooks/{codebookId}?systemId=` ([other.md](other.md#get-codebookscodebookid)). Codebook ids seen: `TP_UNIT`, `TP_MET_READ` (meter reading type, e.g. `ODE_SAMO`), `TP_MET_READ_TARIFF` (`VT`, `NT`), `TP_SUPPL_PNT` (`SPOTR` consumption, production).

### Dates

- Dates: `YYYY-MM-DD` (local date).
- Date-times: ISO 8601 with zone, e.g. `2026-11-16T11:56:02Z`; TAPP query params use UTC with milliseconds `2025-11-01T23:00:00.000Z` for local midnight.
- Amounts are numbers in CZK, energy in kWh (some price fields per MWh).

### Errors

- Business errors: HTTP 4xx/5xx with `ErrorDto`:

```json
{"@class": "...", "correlationId": "<uuid>", "severity": "ERROR", "time": "date-time", "uuid": "<uuid>", "code": "GENERIC", "parameters": [{"key": "Message", "value": "..."}], "otherMessages": [ ... ]}
```

  `severity`: `ERROR`, `WARNING`, `INFO`. Codes seen: `GENERIC`, `SAP_ZCOL-259` (simulation not available), `TAPP_DEVICES_NOT_FOUND`, `TAPP_CURRENT_DATA_NOT_FOUND`, `TAPP_CLIENT_REST_CLIENT`.
- Spring validation errors (missing required query param): HTTP 400 RFC 7807 `{"type": "about:blank", "title": "Bad Request", "status": 400, "detail": "Required parameter 'commodity' is not present.", "instance": "/..."}`.
- HTTP 401: token expired, refresh and retry once (`api.py` `_get`/`_send`).
- HTTP 404: "no data" for some endpoints (document attachment missing, spot price window not published); `api.py` `_send` maps it to `None`.
- `interactive-invoicing/invoice-detail` returns 400/500 for older invoices (see `.snapshot/*/manifest.json`).
- Empty body with HTTP 200 is possible (`api.py` returns `None`).

## Endpoint groups

The COL API has about 490 operations in the bundle; each group file has a table of all its endpoints with the same markers as below and a section per endpoint (method, path, query params, body fields, response fields, chunk file in `tools/probe/chunks/` for re-checking, anonymized response shape when a sample exists).

| File | Content | Endpoints | Used by integration | With sample |
|---|---|---|---|---|
| [supply-points.md](supply-points.md) | Supply points, consumption history, distributor meter readings, dynamic tariff, HDO, EDC | 25 | 5 | 6 |
| [self-meter-reading.md](self-meter-reading.md) | Self meter reading (submit reading, history, reading requests, limits) | 11 | 0 | 2 |
| [billings-documents.md](billings-documents.md) | Billings, invoices, interactive invoice, document download, payment methods, PayU | 54 | 7 | 7 |
| [advance-payments.md](advance-payments.md) | Advance payments, overpayments, repayment plans, housing allowance | 19 | 2 | 3 |
| [simulations.md](simulations.md) | Invoice simulations | 11 | 1 | 2 |
| [products.md](products.md) | Products, product calculator, price lists | 5 | 0 | 3 |
| [tapp.md](tapp.md) | Smart meter interval data, spot prices, home devices (TAPP) | 13 | 4 | 8 |
| [dashboard-messages-outages.md](dashboard-messages-outages.md) | Dashboard, messages, outages, CMS, navigation | 52 | 2 | 7 |
| [user-accounts.md](user-accounts.md) | User, partners/accounts, agreements, registration, MFA | 88 | 1 | 1 |
| [other.md](other.md) | Cases, complaints, appointments, mobile (MVNO/O2), feedback, codebooks, ... and non-COL APIs | 221 | 0 | 0 |

## Endpoints used by the integration or with a captured sample

"Sample" refers to `tools/probe/probe_out/*.json` or `.snapshot/cez*/` (manifest maps request path to file); both contain personal data and stay local.

| Method | Path | File | Integration (`api.py`) | Sample |
|---|---|---|---|---|
| GET | `/advance-payments/{supplyPointId}/events` | [advance-payments.md](advance-payments.md) | get_advance_settings | yes |
| GET | `/advance-payments/{supplyPointId}/settings` | [advance-payments.md](advance-payments.md) | get_advance_settings | yes |
| GET | `/billings` | [billings-documents.md](billings-documents.md) | fetch_all | yes |
| GET | `/billings/extended` | [billings-documents.md](billings-documents.md) | get_invoice_rows | yes |
| GET | `/billings/sp-filter` | [billings-documents.md](billings-documents.md) |  | yes |
| GET | `/common/customer-outages` | [dashboard-messages-outages.md](dashboard-messages-outages.md) |  | yes |
| GET | `/dashboard/billings` | [dashboard-messages-outages.md](dashboard-messages-outages.md) |  | yes |
| GET | `/dashboard/messages/summary` | [dashboard-messages-outages.md](dashboard-messages-outages.md) | fetch_all | yes |
| GET | `/dashboard/operations` | [dashboard-messages-outages.md](dashboard-messages-outages.md) |  | yes |
| GET | `/dashboard/supply-point-outages` | [dashboard-messages-outages.md](dashboard-messages-outages.md) | fetch_all | yes |
| POST | `/documents` | [billings-documents.md](billings-documents.md) | get_invoice_pdf, get_price_lists |  |
| POST | `/documents/attachment` | [billings-documents.md](billings-documents.md) | get_invoice_csv |  |
| GET | `/documents/{attachmentKey}/attachment` | [billings-documents.md](billings-documents.md) | get_invoice_csv, get_document_pdf |  |
| POST | `/documents/{documentGuidCol}/attachment` | [billings-documents.md](billings-documents.md) | get_document_pdf |  |
| GET | `/housing-allowance/selection` | [advance-payments.md](advance-payments.md) |  | yes |
| GET | `/interactive-invoicing/distribution-rate-banner` | [billings-documents.md](billings-documents.md) | get_contract_info | yes |
| GET | `/interactive-invoicing/invoice-detail` | [billings-documents.md](billings-documents.md) |  | yes |
| GET | `/interactive-invoicing/upcoming-invoice-banner` | [billings-documents.md](billings-documents.md) |  | yes |
| GET | `/messages/bill-shock` | [dashboard-messages-outages.md](dashboard-messages-outages.md) |  | yes |
| GET | `/meter-reading-requests` | [self-meter-reading.md](self-meter-reading.md) |  | yes |
| GET | `/outage` | [dashboard-messages-outages.md](dashboard-messages-outages.md) |  | yes |
| GET | `/payment-methods/GetActualBankAccounts` | [billings-documents.md](billings-documents.md) |  | yes |
| POST | `/product-calculator/calculations` | [products.md](products.md) |  | yes |
| GET | `/product-calculator/{agreementIdIsu}/products/{supplyPointCode}` | [products.md](products.md) |  | yes |
| GET | `/product-calculator/{agreementIdIsu}/supply-point/{supplyPointCode}` | [products.md](products.md) | get_contract_info, _fetch_production | yes |
| GET | `/products/all` | [products.md](products.md) |  | yes |
| GET | `/self-meter-reading` | [self-meter-reading.md](self-meter-reading.md) |  | yes |
| GET | `/simulation-invoice` | [simulations.md](simulations.md) |  | yes |
| GET | `/simulations/invoices/{supplyPointCode}` | [simulations.md](simulations.md) | get_simulation | yes |
| GET | `/supply-points/RetrieveSupplyPoints` | [supply-points.md](supply-points.md) | get_supply_points | yes |
| GET | `/supply-points/RetrieveSupplyPointsProducts` | [supply-points.md](supply-points.md) |  | yes |
| GET | `/supply-points/addons` | [products.md](products.md) |  | yes |
| GET | `/supply-points/historical` | [supply-points.md](supply-points.md) | fetch_all | yes |
| GET | `/supply-points/{supplyPointId}/ReadAdvancePlan` | [supply-points.md](supply-points.md) | get_advance_plan | yes |
| GET | `/supply-points/{supplyPointId}/ReadConsumptionHistory` | [supply-points.md](supply-points.md) | get_consumption_periods, get_payouts | yes |
| GET | `/supply-points/{supplyPointId}/ReadMeterReading` | [supply-points.md](supply-points.md) | get_meter_reading, get_register_readings | yes |
| GET | `/supply-points/{supplyPointId}/product-configuration` | [products.md](products.md) |  | yes |
| GET | `/tapp/device-header` | [tapp.md](tapp.md) |  | yes |
| GET | `/tapp/distribution-data` | [tapp.md](tapp.md) |  | yes |
| GET | `/tapp/house` | [tapp.md](tapp.md) |  | yes |
| GET | `/tapp/metering/grid-data` | [tapp.md](tapp.md) | get_grid_daily | yes |
| GET | `/tapp/metering/price-lists/spot-prices-simple` | [tapp.md](tapp.md) | get_spot_prices | yes |
| GET | `/tapp/metering/profile-data` | [tapp.md](tapp.md) | get_profile_quarters |  |
| GET | `/tapp/metering/profile-data/time-intervals` | [tapp.md](tapp.md) | get_grid_availability | yes |
| GET | `/tapp/operational-data` | [tapp.md](tapp.md) |  | yes |
| GET | `/tapp/overview` | [tapp.md](tapp.md) |  | yes |
| GET | `/user` | [user-accounts.md](user-accounts.md) |  | yes |
| GET | `/user/token-data` | [user-accounts.md](user-accounts.md) | get_accounts |  |

## Re-checking against the bundle

- `tools/probe/ctx.py [-b N] [-a N] [-n hits] needle...` prints context around a substring in `index.js` + all chunks, e.g. `python3 tools/probe/ctx.py -a 800 'path:"/self-meter-reading"'`.
- Every generated operation has the form `async <op>Raw(e,t){... this.request({path:"/...",method:"GET",headers:i,query:i}) ...}` (or the ES5 variant `r.<op>Raw=function(e){...}`); the request body serializer is the `...ToJSON` function of the DTO, the response parser the `...FromJSON` function. Field names on the left of `FromJSON` objects are TypeScript names, the right side (`e.Xxx`) are the wire names (differences: e.g. `LastBillPeriod`, `Limits`, `BusinessPartner`).
- API class to chunk mapping: the module federation table in `index.js` (`@cz.cez.cpr.restapi/col-*` packages) and the `XxxApi:()=>` exports. The product calculator client (chunk `997`) is missing from the download.
