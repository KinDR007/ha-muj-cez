# Smart meter data, spot prices, home devices (TAPP)

Interval (smart meter / AMM) data, spot prices and the "Chytrá domácnost" device overview.

Conventions:
- Date-times are ISO 8601 UTC with milliseconds, e.g. `2025-11-01T23:00:00.000Z` (local midnight Europe/Prague). The integration splits requests into windows of 40 days (grid-data), 28 days (profile-data) and 7 days (spot prices), see `grid.py`.
- `profileReadingRoleId`: `SPOTREBA` (import from the grid) or `VYROBA` (export). grid-data rows carry `profileReadingRole` codes such as `ODBER-DODANE`, `ODBER-OBCHOD`, `DODAVKA-DODANE`, `DODAVKA-OBCHOD` (preference order in `grid.py`).
- `profileReadingIntervalId`: `DEN` (day) for grid-data, `HODINA` (hour; data is 15 min) for profile-data; `pricelistSpotConfigurationIntervalId` `HODINA`.
- `meterReadingUnitId` `KWH`; `pricelistConfigurationUnitId` `MWH`; currency `CZK`.
- Errors seen: `TAPP_DEVICES_NOT_FOUND`, `TAPP_CURRENT_DATA_NOT_FOUND` (no home devices), `TAPP_CLIENT_REST_CLIENT` (spot prices for a window not available), HTTP 404 for some spot windows.

Generated from the portal bundle (`tools/probe/index.js`, `tools/probe/chunks/*.js`, release col-fe@3.66.0). Field names are the JSON wire names; `(XxxDto)` marks a nested object, `CodebookEntryDto` is described in [README](README.md#codebook-entries). Types not shown are plain strings/numbers/booleans.

| Method | Path | Operation | Integration | Sample |
|---|---|---|---|---|
| GET | [`/tapp/device-header`](#get-tappdevice-header) | getDeviceHeader |  | yes |
| GET | [`/tapp/distribution-data`](#get-tappdistribution-data) | getDistributionData |  | yes |
| GET | [`/tapp/house`](#get-tapphouse) | getDeviceData |  | yes |
| GET | [`/tapp/metering/grid-data`](#get-tappmeteringgrid-data) | getGridData | get_grid_daily | yes |
| GET | [`/tapp/metering/price-lists/spot-prices`](#get-tappmeteringprice-listsspot-prices) | getSpotPrices |  |  |
| GET | [`/tapp/metering/price-lists/spot-prices-simple`](#get-tappmeteringprice-listsspot-prices-simple) | getSpotPricesSimple | get_spot_prices | yes |
| GET | [`/tapp/metering/profile-data`](#get-tappmeteringprofile-data) | getProfileData | get_profile_quarters |  |
| GET | [`/tapp/metering/profile-data/export`](#get-tappmeteringprofile-dataexport) | getProfileDataExport |  |  |
| GET | [`/tapp/metering/profile-data/time-intervals`](#get-tappmeteringprofile-datatime-intervals) | getProfileDataTimeIntervals | get_grid_availability | yes |
| GET | [`/tapp/metering/spot-prices`](#get-tappmeteringspot-prices) | getProfileSpotPrices |  |  |
| GET | [`/tapp/operational-data`](#get-tappoperational-data) | getOperationalData |  | yes |
| GET | [`/tapp/overview`](#get-tappoverview) | getTappOverview |  | yes |
| GET | [`/tapp/virtual-battery`](#get-tappvirtual-battery) | getVirtualBatteryData |  |  |

### `GET /tapp/device-header`

- Operation `getDeviceHeader` (CPRCOLTAPPApi; `9575.df0d1d2e.js`)
- Query: `supplyPointUid`
- Response: JSON object:
  - `supplyPointUid`
  - `supplyPointIdIsu`
  - `consumptionPlaceName`
  - `address` (object)
- Captured sample: probe_out: `tapp_device-header_supplyPointUid=<supplyPointUid>`
  (captured response: error `TAPP_DEVICES_NOT_FOUND` (ERROR))

### `GET /tapp/distribution-data`

- Operation `getDistributionData` (CPRCOLTAPPApi; `9575.df0d1d2e.js`)
- Query: `supplyPointUid`, `intervalTypeId`
- Response: JSON object:
  - `deviceOutflow` (array)
  - `deviceConsumption` (array)
  - `intervalType` (CodebookEntryDto)
  - `dataUnavailable`
- Captured sample: probe_out: `tapp_distribution-data_supplyPointUid=<supplyPointUid>&intervalTypeId=DEN`

  Response shape (anonymized, values replaced by types):

```json
{
 "intervalType": {
  "entrySystemSpecificId": "DEN",
  "systemId": "INT",
  "entryId": "DEN",
  "longValue": "string",
  "entryOrder": "number",
  "language": "CZ",
  "validTo": "date-time",
  "validFrom": "date-time",
  "codebookId": "TP_INTRV",
  "value": "string"
 },
 "dataUnavailable": "boolean"
}
```

### `GET /tapp/house`

- Operation `getDeviceData` (CPRCOLTAPPApi; `9575.df0d1d2e.js`)
- Query: `supplyPointUid`
- Response: JSON object:
  - `hasActiveProdContract`
  - `hasVirtualBattery`
  - `dataState`
  - `dataTimestamp` (date)
  - `fveInflowData` (object)
  - `nextRefreshTimestamp` (date)
  - `fvePowerData` (object)
  - `supplyPointTotalConsumptionData` (object)
  - `heatPumpData` (object)
  - `batteryData` (object)
  - `electricitySupplyPointProductionFlag`
  - `hasMissingProdEAN`
  - `deviceLiveDataFlag`
  - `deviceLiveDataRefreshPeriod`
- Captured sample: probe_out: `tapp_house_supplyPointUid=<supplyPointUid>`
  (captured response: error `TAPP_CURRENT_DATA_NOT_FOUND` (ERROR))

### `GET /tapp/metering/grid-data`

- Operation `getGridData` (CPRCOLTAPPApi; `9575.df0d1d2e.js`)
- **Used by integration**: `api.py` get_grid_daily
- Query: `supplyPointUid`, `profileReadingIntervalId`, `profileReadingDatetimeFrom`, `profileReadingDatetimeTo`, `meterReadingUnitId`, `profileReadingRoleId`
- Response: JSON object:
  - `gridDataAggregate` (array)
  - `periodData` (object)
  - `previousPeriodData` (object)
  - `isNextPeriodData`
- Captured sample: snapshot: `/tapp/metering/grid-data?meterReadingUnitId=KWH&profileReadingDatetimeFrom=2023-11-12T23:00:00.000Z&profileReadingDatetimeTo=2023-12-22T23:00:00.000Z&profileReadingIntervalId=DEN&profileReadingRoleId=SPOTREBA&supplyPointUid=<supplyPointUid>`; snapshot: `/tapp/metering/grid-data?meterReadingUnitId=KWH&profileReadingDatetimeFrom=2023-11-12T23:00:00.000Z&profileReadingDatetimeTo=2023-12-22T23:00:00.000Z&profileReadingIntervalId=DEN&profileReadingRoleId=VYROBA&supplyPointUid=<supplyPointUid>`; snapshot: `/tapp/metering/grid-data?meterReadingUnitId=KWH&profileReadingDatetimeFrom=2023-12-22T23:00:00.000Z&profileReadingDatetimeTo=2024-01-31T23:00:00.000Z&profileReadingIntervalId=DEN&profileReadingRoleId=SPOTREBA&supplyPointUid=<supplyPointUid>`

  Response shape (anonymized, values replaced by types):

```json
{
 "gridDataAggregate": [],
 "periodData": {
  "weightedAverage": "number"
 },
 "previousPeriodData": {}
}
```

### `GET /tapp/metering/price-lists/spot-prices`

- Operation `getSpotPrices` (CPRCOLTAPPApi; `9575.df0d1d2e.js`)
- Query: `pricelistConfigurationUnitId`, `pricelistSpotConfigurationDatetimeFrom`, `pricelistSpotConfigurationDatetimeTo`, `pricelistSpotConfigurationIntervalId`, `pricelistSpotConfigurationPriceCurrencyId`
- Response: JSON object:
  - `SpotPriceData` (object)
  - `tommorowDataAvailable`

### `GET /tapp/metering/price-lists/spot-prices-simple`

- Operation `getSpotPricesSimple` (CPRCOLTAPPApi; `9575.df0d1d2e.js`)
- **Used by integration**: `api.py` get_spot_prices
- Query: `pricelistSpotConfigurationDatetimeTo`, `pricelistSpotConfigurationDatetimeFrom`, `pricelistSpotConfigurationPriceCurrencyId`, `pricelistConfigurationUnitId`, `pricelistSpotConfigurationIntervalId`
- Response: JSON object:
  - `pricelistSpotConfigurationPriceCurrency` (CodebookEntryDto)
  - `pricelistConfigurationUnit` (CodebookEntryDto)
  - `pricelistSpotConfigurationInterval` (CodebookEntryDto)
  - `pricelistSpotConfigurationDatetimeTo` (date)
  - `pricelistSpotConfigurationPriceMaximumTotal`
  - `pricelistSpotConfigurationPriceAverageTotal`
  - `pricelistSpotConfigurationPriceMinimumTotal`
  - `pricelistSpotConfigurationDatetimeFrom` (date)
  - `spotConfigurations` (array)
- Captured sample: probe_out: `tapp_metering_price-lists_spot-prices-simple_file=spot_a`; probe_out: `tapp_metering_price-lists_spot-prices-simple_file=spot_b`

  Response shape (anonymized, values replaced by types):

```json
{
 "pricelistSpotConfigurationPriceCurrency": {
  "entrySystemSpecificId": "CZK",
  "systemId": "INT",
  "entryId": "CZK",
  "longValue": "string",
  "entryOrder": "number",
  "language": "CZ",
  "validTo": "date-time",
  "validFrom": "date-time",
  "codebookId": "TP_CCY",
  "value": "string",
  "otherValues": []
 },
 "pricelistConfigurationUnit": {
  "entrySystemSpecificId": "KWH",
  "systemId": "INT",
  "entryId": "KWH",
  "longValue": "string",
  "entryOrder": "number",
  "language": "CZ",
  "validTo": "date-time",
  "validFrom": "date-time",
  "codebookId": "TP_UNIT",
  "value": "string",
  "otherValues": [
   {
    "key": "ApppOrder",
    "value": "string"
   }
  ]
 },
 "pricelistSpotConfigurationInterval": {
  "entrySystemSpecificId": "15MIN",
  "systemId": "INT",
  "entryId": "15MIN",
  "longValue": "string",
  "entryOrder": "number",
  "language": "CZ",
  "validTo": "date-time",
  "validFrom": "date-time",
  "codebookId": "TP_INTRV",
  "value": "string",
  "otherValues": []
 },
 "pricelistSpotConfigurationDatetimeTo": "date-time",
 "pricelistSpotConfigurationPriceMaximumTotal": "number",
 "pricelistSpotConfigurationPriceAverageTotal": "number",
 "pricelistSpotConfigurationPriceMinimumTotal": "number",
 "pricelistSpotConfigurationDatetimeFrom": "date-time",
 "spotConfigurations": [
  {
   "pricelistSpotConfigurationDatetimeTo": "date-time",
   "pricelistSpotConfigurationPriceAverage": "number",
   "pricelistSpotConfigurationPriceMinimum": "number",
   "pricelistSpotConfigurationPriceMaximum": "number",
   "pricelistSpotConfigurationDatetimeFrom": "date-time"
  }
 ]
}
```

### `GET /tapp/metering/profile-data`

- Operation `getProfileData` (CPRCOLTAPPApi; `9575.df0d1d2e.js`)
- **Used by integration**: `api.py` get_profile_quarters
- Query: `profileReadingDatetimeFrom`, `profileReadingDatetimeTo`, `profileReadingRoleId`, `supplyPointUid`, `meterReadingUnitId`
- Response: JSON array of object

### `GET /tapp/metering/profile-data/export`

- Operation `getProfileDataExport` (CPRCOLTAPPApi; `9575.df0d1d2e.js`)
- Query: `meterReadingUnitId`, `supplyPointUid`, `profileReadingDatetimeTo`, `profileReadingDatetimeFrom`, `profileReadingRoleId`
- Response: binary file (blob)

### `GET /tapp/metering/profile-data/time-intervals`

- Operation `getProfileDataTimeIntervals` (CPRCOLTAPPApi; `9575.df0d1d2e.js`)
- **Used by integration**: `api.py` get_grid_availability
- Query: `profileReadingDatetimeFrom`, `profileReadingDatetimeTo`, `supplyPointUid`, `profileReadingRoleId`
- Response: JSON array of object
- Captured sample: snapshot: `/tapp/metering/profile-data/time-intervals?profileReadingDatetimeFrom=2023-11-12T23:00:00.000Z&profileReadingDatetimeTo=2026-11-16T23:00:00.000Z&profileReadingRoleId=SPOTREBA&supplyPointUid=<supplyPointUid>`; snapshot: `/tapp/metering/profile-data/time-intervals?profileReadingDatetimeFrom=2023-11-12T23:00:00.000Z&profileReadingDatetimeTo=2026-11-16T23:00:00.000Z&profileReadingRoleId=VYROBA&supplyPointUid=<supplyPointUid>`

  Response shape (anonymized, values replaced by types):

```json
[
 {
  "consumptionPlaceIdIsu": "string",
  "data": [
   {
    "profileReadingRole": {
     "entrySystemSpecificId": "M12",
     "systemId": "INT",
     "entryId": "M12",
     "longValue": "string",
     "entryOrder": "number",
     "language": "CZ",
     "validTo": "date-time",
     "validFrom": "date-time",
     "codebookId": "TP_PRFL_ROLE",
     "value": "string",
     "otherValues": []
    },
    "profileReadingDatetimeFrom": "date-time",
    "profileReadingTariff": {
     "entrySystemSpecificId": "ODB",
     "systemId": "INT",
     "entryId": "ODB",
     "longValue": "string",
     "entryOrder": "number",
     "language": "CZ",
     "validTo": "date-time",
     "validFrom": "date-time",
     "codebookId": "TP_MET_READ_TARIFF",
     "value": "string",
     "otherValues": []
    },
    "profileReadingDatetimeTo": "date-time"
   }
  ],
  "supplyPointIdIsu": "string",
  "partnerIdCrm": "string",
  "profileReadingDatetimeMin": "date-time",
  "profileReadingDatetimeMax": "date-time"
 }
]
```

### `GET /tapp/metering/spot-prices`

- Operation `getProfileSpotPrices` (CPRCOLTAPPApi; `9575.df0d1d2e.js`)
- Query: `profileReadingRoleId`, `supplyPointUid`, `profileReadingDatetimeFrom`, `profileReadingDatetimeTo`, `meterReadingUnitId`, `profileReadingIntervalId`, `profileReadingSpotProfilePriceCurrencyId`
- Response: JSON object:
  - `profileSpotPrices` (array)
  - `weightedAverage`

### `GET /tapp/operational-data`

- Operation `getOperationalData` (CPRCOLTAPPApi; `9575.df0d1d2e.js`)
- Query: `supplyPointUid`, `intervalTypeId`
- Response: JSON object:
  - `deviceSelfSufficiency` (array)
  - `deviceProduction` (array)
  - `intervalType` (CodebookEntryDto)
  - `deviceConsumption` (array)
  - `dataUnavailable`
- Captured sample: probe_out: `tapp_operational-data_supplyPointUid=<supplyPointUid>&intervalTypeId=DEN`

  Response shape (anonymized, values replaced by types):

```json
{
 "deviceSelfSufficiency": [],
 "deviceProduction": [],
 "intervalType": {
  "entrySystemSpecificId": "DEN",
  "systemId": "INT",
  "entryId": "DEN",
  "longValue": "string",
  "entryOrder": "number",
  "language": "CZ",
  "validTo": "date-time",
  "validFrom": "date-time",
  "codebookId": "TP_INTRV",
  "value": "string"
 },
 "deviceConsumption": [],
 "dataUnavailable": "boolean"
}
```

### `GET /tapp/overview`

- Operation `getTappOverview` (CPRCOLTAPPApi; `9575.df0d1d2e.js`)
- Response: JSON array of object
- Captured sample: probe_out: `tapp_overview_pricelistSpotConfigurationIntervalId=HODINA`
  (captured response: empty `[]`)

### `GET /tapp/virtual-battery`

- Operation `getVirtualBatteryData` (CPRCOLTAPPApi; `9575.df0d1d2e.js`)
- Query: `supplyPointUid`
- Response: JSON object:
  - `virtualBatteryTimestamp` (date)
  - `virtualBatteryActualCharge`
  - `virtualBatteryPeriodTo` (date)
  - `showFveButton`
  - `virtualBatteryAggregatedProduction`
  - `virtualBatteryAggregatedConsumption`
  - `virtualBatteryInvoicePeriodTo` (date)
  - `virtualBatteryMode`
  - `virtualBatteryDiscountAmount`

