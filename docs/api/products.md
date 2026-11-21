# Products, price lists, product calculator

Product (tariff) information of a supply point, the product calculator and price list documents.

Price lists ("Ceník ...") are archive documents of type `DOC_TYPE=CEN`, downloaded through the document API, see [billings-documents.md](billings-documents.md#document-download-flow-used-by-the-integration) (`api.py` `get_price_lists`, `get_document_pdf`).

## Product calculator (`col-product-calculator`)

The generated client of this API lives in webpack chunk `997`, which is **not** part of the downloaded bundle (`tools/probe/chunks/` has only `1919.*.js`, the shared runtime). Paths below come from the integration, the probe scripts and captured responses; operation names come from the sagas in `1212.07eba32b.js` (`productCalculatorApi.<op>`).

### `GET /product-calculator/{agreementIdIsu}/supply-point/{supplyPointCode}`

- Operation `getTechnicalData` (`{agreementIdIsu, supplyPointCode, commodity}`)
- **Used by integration**: `api.py` get_contract_info, _fetch_production
- Path params: `agreementIdIsu` (12 digits, `agreement.agreementIdIsu` of `RetrieveSupplyPoints`), `supplyPointCode` (EAN)
- Query: `commodity` (required, `E1` electricity, `G1` gas presumably). Without it: HTTP 400 RFC 7807 body `{"type":"about:blank","title":"Bad Request","status":400,"detail":"Required parameter 'commodity' is not present.","instance":"..."}`.
- Captured sample: probe_out `product-calculator_<id>_supply-point_<ean>_commodity=E1`; snapshot `/product-calculator/<id>/supply-point/<ean>?commodity=E1`

  Response shape (anonymized):

```json
{
 "isCalculatorProducts": "boolean",
 "descriptionCalc": "string",
 "phase": "number",
 "productCrm": "string",
 "highTariffConsumption": "number",
 "circuitBreakerValue": "number",
 "showAdditionalProducts": "boolean",
 "tariffType": "D02D",
 "lowTariffConsumption": "number",
 "serviceId": "string",
 "calculationType": "01",
 "priceIncreaseDate": "YYYY-MM-DD",
 "showFixation": "boolean",
 "showCancelledProduct": "boolean",
 "hasDoubleTariff": "boolean",
 "loginDate": "date-time",
 "additionalSupplyPointProducts": [],
 "contractPlannedEndDate": "YYYY-MM-DD"
}
```

`tariffType` is the distribution rate (e.g. `D02d`, `D25d`, `D57d`), `phase` and `circuitBreakerValue` the main breaker, `highTariffConsumption`/`lowTariffConsumption` the expected annual consumption in kWh.

### `GET /product-calculator/{agreementIdIsu}/products/{supplyPointCode}`

- Operation `getProducts` (`{supplyPointCode, agreementIdIsu, commodity}`)
- Query: `commodity` (required, same 400 error without it)
- Response: JSON array of offered products (`id`, `fixationDate`, ...). Captured response for a test account was `[]`.

### `POST /product-calculator/calculations`

- Operation `getCalculations`
- Body (`calculationRequestDto`):

```json
{
 "commodity": "E1",
 "agreementIdIsu": "000000000000",
 "supplyPointCode": "859182400000000000",
 "productCalculationInfo": [{"productId": "<productId>", "calculationDate": "YYYY-MM-DD"}],
 "dateOfChange": "YYYY-MM-DD"
}
```

  The web app fills `productCalculationInfo` from `getProducts` (`productId: id`, `calculationDate: fixationDate`) and `dateOfChange` from `getTechnicalData.priceIncreaseDate`.
- Response: JSON array (captured `[]` with an empty product list).

### Other operations (path unknown, chunk missing)

`getProductDetail({productId})`, `checkParallelProcesses({..., supplyPointCode})` (returns `parallelProcessesExist`), `getProductValidations`, `calculateIntervalConsumption({calculateIntervalConsumptionRequestBodyDto: {massReadingInfo: [...]}})`, `activateProduct({activateProductRequestDto})`, `getProductActivationData` (polled up to 100 times, `ProductActivationDataDtoProductActivationStatusEnum.Success`), `createProductCalculatorLead({leadProductCalculatorRequestDto})`.

## Other product endpoints

Generated from the portal bundle (`tools/probe/index.js`, `tools/probe/chunks/*.js`, release col-fe@3.66.0). Field names are the JSON wire names; `(XxxDto)` marks a nested object, `CodebookEntryDto` is described in [README](README.md#codebook-entries). Types not shown are plain strings/numbers/booleans.

| Method | Path | Operation | Integration | Sample |
|---|---|---|---|---|
| POST | [`/dashboard/products`](#post-dashboardproducts) | getProducts |  |  |
| GET | [`/products/all`](#get-productsall) | allProducts |  | yes |
| GET | [`/supply-points/addons`](#get-supply-pointsaddons) | getAddons |  | yes |
| GET | [`/supply-points/assistant-product-configurations`](#get-supply-pointsassistant-product-configurations) | getAssistantProductConfigurations |  |  |
| GET | [`/supply-points/{supplyPointId}/product-configuration`](#get-supply-pointssupplypointidproduct-configuration) | getProductConfiguration |  | yes |

### `POST /dashboard/products`

- Operation `getProducts` (CPRCOLDASHBOARDApi; `2100.03a79f61.js`)
- Body (JSON `DashboardProductInputDto`):
  - `uidList`
  - `fullLoadingWait`
  - `sessionId`
- Response: JSON `ProductsResponseDto`:
  - `tiles` (DashboardProductDto[])
    - `addLogging` (AppActionInDto[])
    - `tapp` (DashboardTileTappDto)
    - `id`
    - `subtitle`
    - `uId`
    - `address` (AddressDto)
    - `title`
    - `marketing` (DashboardTileMarketingDto)
    - `mvno` (DashboardTileMvnoDto)
    - `category`
    - `links` (DashboardProductButtonLinkDto[])
    - `commodity` (DashboardTileCommodityDto)
    - `statuses` (DashboardTileStatusDto[])
    - `paymentWarning` (PaymentWarningDto)
    - `type`
    - `activityStatus` (DashboardTileActivityStatusDto)
    - `notFullyLoaded`

### `GET /products/all`

- Operation `allProducts` (CPRCOLCONTRACTApi; `3209.3573e7cf.js`)
- Response: JSON array of object:
  - `prodExtOrderType`
  - `address` (object)
  - `supplyPointId`
  - `customerIdentifier`
  - `supplyPointCommodity` (CodebookEntryDto)
  - `customerDescription`
  - `agreementIdIsu`
  - `supplyPointType` (CodebookEntryDto)
  - `productBannerText`
  - `productInfoText`
  - `commodity` (object)
  - `hasDynamicProduct`
- Captured sample: probe_out: `products_all`

  Response shape (anonymized, values replaced by types):

```json
[
 {
  "prodExtOrderType": "",
  "address": {
   "addressStreet": {
    "value": "string"
   },
   "addressZipCode": "string",
   "addressCity": {
    "value": "string"
   },
   "addressLandRegistryNumber": "string",
   "addressHouseNumber": "string"
  },
  "supplyPointId": "string",
  "customerIdentifier": "string",
  "supplyPointCommodity": {
   "entrySystemSpecificId": "",
   "systemId": "",
   "entryId": "",
   "longValue": "string",
   "language": "",
   "validTo": "string",
   "validFrom": "string",
   "codebookId": "",
   "value": "E1"
  },
  "customerDescription": "string",
  "agreementIdIsu": "string",
  "supplyPointType": {
   "entrySystemSpecificId": "SPOTR",
   "systemId": "INT",
   "entryId": "SPOTR",
   "longValue": "string",
   "entryOrder": "number",
   "language": "CZ",
   "validTo": "date-time",
   "validFrom": "date-time",
   "codebookId": "TP_SUPPL_PNT",
   "value": "string"
  },
  "productBannerText": "string",
  "productInfoText": "string",
  "commodity": {
   "title": "string",
   "be": "string",
   "fe": "string"
  }
 }
]
```

### `GET /supply-points/addons`

- Operation `getAddons` (CPRCOLSUPPLYPOINTApi; `3998.ada47cff.js`)
- Query: `supplyPointCode`
- Response: JSON array of `AddonDto`:
  - `productInstanceProductId`
  - `productInstanceValidityEndDate` (date)
  - `productInstanceDescription`
  - `productInstanceName`
  - `productInstanceNameMc`
  - `productInstanceValidityStartDate` (date)
  - `discountConfigurationValue`
  - `discountKind` (CodebookEntryDto)
  - `unitName`
- Captured sample: probe_out: `supply-points_addons_supplyPointCode=<ean>`
  (captured response: empty `[]`)

### `GET /supply-points/assistant-product-configurations`

- Operation `getAssistantProductConfigurations` (CPRCOLCONTRACTApi; `3209.3573e7cf.js`)
- Response: JSON array of object:
  - `supplyPointCode`
  - `configurations` (array)

### `GET /supply-points/{supplyPointId}/product-configuration`

- Operation `getProductConfiguration` (CPRCOLCONTRACTApi; `3209.3573e7cf.js`)
- Path params: `supplyPointId`
- Response: JSON array of object:
  - `productInstanceConfigurationId`
  - `productInstanceConfigurationKey`
- Captured sample: probe_out: `supply-points_<supplyPointUid>_product-configuration`

  Response shape (anonymized, values replaced by types):

```json
[
 {
  "productInstanceConfigurationId": "string",
  "productInstanceConfigurationKey": "string"
 }
]
```

