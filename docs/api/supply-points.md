# Supply points, consumption history, meter readings

Supply point list and detail, consumption history, meter readings recorded by the distributor/ISU, advance plan, dynamic tariff, HDO signal and EDC (energy sharing).

Identifiers: `{supplyPointId}` in these paths is the 40 character `supplyPointUniqueId` (`<supplyPointUid>`), i.e. 12 digit agreement number + 10 digits + 18 digit EAN (see README). `supplyPointCode` is the EAN (`859182400000000000`).

`ReadConsumptionHistory?aggregation=` accepts `year` (and `YEAR`); captured probes with `ALL`, `DAY` and `ROK` returned error `GENERIC`.

`ReadMeterReading` returns all register readings (distributor readings, customer self readings, simulated readings). `meterReadingType.entryId` values seen: `ODE_SAMO` (self reading); the integration filters out the type with value `Odečet pro použití v simulaci faktury` (simulated reading). For submitting a reading see [self-meter-reading.md](self-meter-reading.md).

Generated from the portal bundle (`tools/probe/index.js`, `tools/probe/chunks/*.js`, release col-fe@3.66.0). Field names are the JSON wire names; `(XxxDto)` marks a nested object, `CodebookEntryDto` is described in [README](README.md#codebook-entries). Types not shown are plain strings/numbers/booleans.

| Method | Path | Operation | Integration | Sample |
|---|---|---|---|---|
| GET | [`/dynamic-tariff/consumption-summary/{supplyPointUid}`](#get-dynamic-tariffconsumption-summarysupplypointuid) | getDynamicTariffConsumptionSummary |  |  |
| GET | [`/dynamic-tariff/data/{supplyPointUid}`](#get-dynamic-tariffdatasupplypointuid) | getDynamicTariffData |  |  |
| GET | [`/dynamic-tariff/dynamic-price-info/{supplyPointUid}`](#get-dynamic-tariffdynamic-price-infosupplypointuid) | getDynamicPriceInfo |  |  |
| POST | [`/edc/contract-preview`](#post-edccontract-preview) | getContractPreview |  |  |
| GET | [`/edc/overview/{supplyPointCode}`](#get-edcoverviewsupplypointcode) | getSharingData |  |  |
| POST | [`/edc/submit`](#post-edcsubmit) | submitFormData |  |  |
| GET | [`/edc/validate-ean/{supplyPointCode}`](#get-edcvalidate-eansupplypointcode) | validateEAN |  |  |
| POST | [`/hdo-signal/create`](#post-hdo-signalcreate) | createHDOSignal |  |  |
| GET | [`/hdo-signal/get`](#get-hdo-signalget) | getHDOSignal |  |  |
| GET | [`/supply-points/ReadCasesAndServicesInActivationProcess`](#get-supply-pointsreadcasesandservicesinactivationprocess) | readCasesAndServicesInActivationProcess |  |  |
| GET | [`/supply-points/RetrieveSupplyPoints`](#get-supply-pointsretrievesupplypoints) | retrieveSupplyPoints | get_supply_points | yes |
| GET | [`/supply-points/RetrieveSupplyPointsProducts`](#get-supply-pointsretrievesupplypointsproducts) | retrieveSupplyPointsProducts |  | yes |
| POST | [`/supply-points/consumption-place-names`](#post-supply-pointsconsumption-place-names) | readConsumptionPlaceNames |  |  |
| GET | [`/supply-points/create-snapshot`](#get-supply-pointscreate-snapshot) | createSnapshot |  |  |
| POST | [`/supply-points/ean-confirm-responsibility`](#post-supply-pointsean-confirm-responsibility) | confirmResponsibilityEAN |  |  |
| GET | [`/supply-points/fixed-products/last-import`](#get-supply-pointsfixed-productslast-import) | getLastSupplyPointWithFixedProductImport |  |  |
| GET | [`/supply-points/historical`](#get-supply-pointshistorical) | readHistoricalSupplyPoints | fetch_all | yes |
| POST | [`/supply-points/import-fixed-products`](#post-supply-pointsimport-fixed-products) | importSupplyPointsWithFixedProducts |  |  |
| POST | [`/supply-points/supply-points-by-import`](#post-supply-pointssupply-points-by-import) | getSupplyPointsByImport |  |  |
| GET | [`/supply-points/{supplyPointId}/ReadAdvancePlan`](#get-supply-pointssupplypointidreadadvanceplan) | readAdvancePlan | get_advance_plan | yes |
| GET | [`/supply-points/{supplyPointId}/ReadConsumptionHistory`](#get-supply-pointssupplypointidreadconsumptionhistory) | readConsumption | get_consumption_periods, get_payouts | yes |
| GET | [`/supply-points/{supplyPointId}/ReadMassRemoteControlInfo`](#get-supply-pointssupplypointidreadmassremotecontrolinfo) | getMassRemoteControlInfo |  |  |
| GET | [`/supply-points/{supplyPointId}/ReadMeterReading`](#get-supply-pointssupplypointidreadmeterreading) | readMeter | get_meter_reading, get_register_readings | yes |
| GET | [`/supply-points/{supplyPointId}/ReadSupplyPointDetail`](#get-supply-pointssupplypointidreadsupplypointdetail) | getOMDetail |  |  |
| PATCH | [`/supply-points/{supplyPointId}/UpdateSupplyPointName`](#patch-supply-pointssupplypointidupdatesupplypointname) | patchSPName |  |  |

### `GET /dynamic-tariff/consumption-summary/{supplyPointUid}`

- Operation `getDynamicTariffConsumptionSummary` (CPRCOLDYNAMICTARIFFApi; `6465.eff5a544.js`)
- Path params: `supplyPointUid`
- Response: JSON object:
  - `date` (date)
  - `dynamicTariffConsumptionPeriods` (array)

### `GET /dynamic-tariff/data/{supplyPointUid}`

- Operation `getDynamicTariffData` (CPRCOLDYNAMICTARIFFApi; `6465.eff5a544.js`)
- Path params: `supplyPointUid`
- Response: JSON object:
  - `dynamicTariffActualState` (object)
  - `dynamicTariffConsumptionSummary` (object)

### `GET /dynamic-tariff/dynamic-price-info/{supplyPointUid}`

- Operation `getDynamicPriceInfo` (CPRCOLDYNAMICTARIFFApi; `6465.eff5a544.js`)
- Path params: `supplyPointUid`
- Response: JSON object:
  - `roundingForPrice`
  - `doubleTariff`
  - `seasonPriceInfos` (array)

### `POST /edc/contract-preview`

- Operation `getContractPreview` (CPRCOLEDCApi; `3198.ff80a4db.js`, `817.d61ee489.js`)
- Body (JSON `ContractPreviewRequestDto`):
  - `sharingMethod`
  - `formData` (object)
  - `supplyPoints` (array)
  - `supplyPointCode`
- Response: JSON object:
  - `attachmentKey`

### `GET /edc/overview/{supplyPointCode}`

- Operation `getSharingData` (CPRCOLEDCApi; `3198.ff80a4db.js`, `817.d61ee489.js`)
- Path params: `supplyPointCode`
- Query: `onlyActive`
- Response: JSON object:
  - `groupNumber`
  - `supplyPointShares` (array)

### `POST /edc/submit`

- Operation `submitFormData` (CPRCOLEDCApi; `3198.ff80a4db.js`, `817.d61ee489.js`)
- Body: `multipart/form-data` parts `SubmitFormDataRequest`, `attachments`
- Response: JSON object:
  - `activityId`

### `GET /edc/validate-ean/{supplyPointCode}`

- Operation `validateEAN` (CPRCOLEDCApi; `3198.ff80a4db.js`, `817.d61ee489.js`)
- Path params: `supplyPointCode`
- Response: JSON object:
  - `isValid`
  - `supplyPointCode`
  - `messages` (array)
  - `attachmentRequired`

### `POST /hdo-signal/create`

- Operation `createHDOSignal` (CPRCOLMAINHDOSIGNALApi; `1367.dc46cc94.js`, `3748.9d555bdc.js`)
- Body (JSON `HDOSignalRequestDto`):
  - `supplyPointId`
  - `signalId`
- Response: empty (HTTP 200/204)

### `GET /hdo-signal/get`

- Operation `getHDOSignal` (CPRCOLMAINHDOSIGNALApi; `1367.dc46cc94.js`, `3748.9d555bdc.js`)
- Query: `supplyPointId`
- Response: JSON object:
  - `timeSwitchingHdoSignal`

### `GET /supply-points/ReadCasesAndServicesInActivationProcess`

- Operation `readCasesAndServicesInActivationProcess` (CPRCOLSUPPLYPOINTApi; `3998.ada47cff.js`)
- Response: JSON array of `EntityInActivationProcessDto`:
  - `address` (AddressWrapperDto)
    - `addressHouseNumber`
    - `addressCity` (CodebookEntryDto)
    - `addressCountry` (CodebookEntryDto)
    - `addressStreet` (CodebookEntryDto)
    - `addressZipCode`
    - `addressRegion` (CodebookEntryDto)
    - `addressName`
    - `addressLandRegistryNumber`
    - `addressFloor`
  - `agreementIdIsu`
  - `commodityId`
  - `consumptionPlaceIdIsu`
  - `supplyPointCode`
  - `caseStatusId`

### `GET /supply-points/RetrieveSupplyPoints`

- Operation `retrieveSupplyPoints` (CPRCOLSUPPLYPOINTApi; `3998.ada47cff.js`)
- **Used by integration**: `api.py` get_supply_points
- Query: `loadAdvancePaymentInfo`, `hiddenByFilter`
- Response: JSON array of `SupplyPointOverviewDto`:
  - `consumptionPlaceIdIsu`
  - `prodExtOrderType`
  - `productDashboardText`
  - `parentAgreement` (ParentAgreementDto)
    - `parentAgreementIdIsu`
  - `agreement` (AgreementDto)
    - `agreementIdIsu`
    - `agreementAccountClass` (CodebookEntryDto)
    - `agreementElectronicInvoicingTypeId`
    - `isAggregated`
    - `isGrouped`
  - `supplyPointCode`
  - `contract` (ContractDto)
    - `contractIdIsu`
    - `contractAdvancePaymentAmount`
    - `contractAdvancePaymentFrequency` (CodebookEntryDto)
    - `contractName`
    - `contractValidityStartDate` (date)
    - `contractValidityEndDate` (date)
  - `consumptionPlaceName`
  - `contactValue`
  - `advancePaymentChangeNotPossibleReason` (CodebookEntryDto)
  - `canChangeAdvancePayments`
  - `address` (AddressPartsDto)
    - `addressCity` (CodebookEntryDto)
    - `addressLandRegistryNumber`
    - `addressHouseNumber`
    - `addressZipCode`
    - `addressStreet` (CodebookEntryDto)
  - `supplyPointCommodity` (CodebookEntryDto)
  - `supplyPointUniqueId`
  - `productInstanceId`
  - `hasCsvDataFile`
  - `hasMonthlyInvoicing`
  - `supplyPointMeasurementSubKind`
  - `supplyPointNumber`
  - `hiddenByFilter`
  - `Product`
  - `hasFixedProduct`
  - `supplyPointType` (CodebookEntryDto)
  - `productBannerText`
  - `productInfoText`
  - `supplyPointIsContinuousMeasurement`
- Captured sample: probe_out: `supply-points_RetrieveSupplyPoints_loadAdvancePaymentInfo=true`; snapshot: `/supply-points/RetrieveSupplyPoints`

  Response shape (anonymized, values replaced by types):

```json
[
 {
  "consumptionPlaceIdIsu": "string",
  "prodExtOrderType": "",
  "productDashboardText": "string",
  "parentAgreement": {
   "parentAgreementIdIsu": "string"
  },
  "agreement": {
   "agreementIdIsu": "string",
   "agreementElectronicInvoicingTypeId": "Elfa",
   "isAggregated": "boolean",
   "isGrouped": "boolean"
  },
  "supplyPointCode": "string",
  "contract": {
   "contractIdIsu": "string",
   "contractAdvancePaymentAmount": "number",
   "contractAdvancePaymentFrequency": {
    "value": "01"
   },
   "contractName": "string"
  },
  "consumptionPlaceName": "string",
  "canChangeAdvancePayments": "boolean",
  "address": {
   "addressCity": {
    "value": "string"
   },
   "addressLandRegistryNumber": "string",
   "addressHouseNumber": "string",
   "addressZipCode": "string",
   "addressStreet": {
    "value": "string"
   }
  },
  "supplyPointCommodity": {
   "value": "E1"
  },
  "supplyPointUniqueId": "string",
  "productInstanceId": "string",
  "hasCsvDataFile": "boolean",
  "hasMonthlyInvoicing": "boolean",
  "supplyPointMeasurementSubKind": "",
  "supplyPointNumber": "string",
  "hiddenByFilter": "string",
  "Product": "string",
  "hasFixedProduct": "boolean",
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
  "supplyPointIsContinuousMeasurement": "boolean"
 }
]
```

### `GET /supply-points/RetrieveSupplyPointsProducts`

- Operation `retrieveSupplyPointsProducts` (CPRCOLSUPPLYPOINTApi; `3998.ada47cff.js`)
- Query: `loadAdvancePaymentInfo`, `hiddenByFilter`
- Response: JSON array of `SupplyPointOverviewDto`:
  - `consumptionPlaceIdIsu`
  - `prodExtOrderType`
  - `productDashboardText`
  - `parentAgreement` (ParentAgreementDto)
    - `parentAgreementIdIsu`
  - `agreement` (AgreementDto)
    - `agreementIdIsu`
    - `agreementAccountClass` (CodebookEntryDto)
    - `agreementElectronicInvoicingTypeId`
    - `isAggregated`
    - `isGrouped`
  - `supplyPointCode`
  - `contract` (ContractDto)
    - `contractIdIsu`
    - `contractAdvancePaymentAmount`
    - `contractAdvancePaymentFrequency` (CodebookEntryDto)
    - `contractName`
    - `contractValidityStartDate` (date)
    - `contractValidityEndDate` (date)
  - `consumptionPlaceName`
  - `contactValue`
  - `advancePaymentChangeNotPossibleReason` (CodebookEntryDto)
  - `canChangeAdvancePayments`
  - `address` (AddressPartsDto)
    - `addressCity` (CodebookEntryDto)
    - `addressLandRegistryNumber`
    - `addressHouseNumber`
    - `addressZipCode`
    - `addressStreet` (CodebookEntryDto)
  - `supplyPointCommodity` (CodebookEntryDto)
  - `supplyPointUniqueId`
  - `productInstanceId`
  - `hasCsvDataFile`
  - `hasMonthlyInvoicing`
  - `supplyPointMeasurementSubKind`
  - `supplyPointNumber`
  - `hiddenByFilter`
  - `Product`
  - `hasFixedProduct`
  - `supplyPointType` (CodebookEntryDto)
  - `productBannerText`
  - `productInfoText`
  - `supplyPointIsContinuousMeasurement`
- Captured sample: probe_out: `supply-points_RetrieveSupplyPointsProducts_loadAdvancePaymentInfo=true`
  (captured response: error `GENERIC` (ERROR))

### `POST /supply-points/consumption-place-names`

- Operation `readConsumptionPlaceNames` (CPRCOLSUPPLYPOINTApi; `3998.ada47cff.js`)
- Body (JSON `ReadConsumtpionPlaceNamesRequestDto`):
  - `overpaymentRefundVariableSymbols`
- Response: JSON array of `ConsumptionPlaceNameInfoDto`:
  - `overpaymentRefundVariableSymbols`
  - `supplyPointUniqueId`
  - `supplyPointCommodity` (CodebookEntryDto)
  - `Address` (AddressDto)
    - `addressHouseNumber`
    - `addressZipCode`
    - `addressCity` (CodebookEntryDto)
    - `addressStreet` (CodebookEntryDto)
    - `addressLandRegistryNumber`
  - `consumptionPlaceName`

### `GET /supply-points/create-snapshot`

- Operation `createSnapshot` (CPRCOLSUPPLYPOINTApi; `3998.ada47cff.js`)
- Response: empty (HTTP 200/204)

### `POST /supply-points/ean-confirm-responsibility`

- Operation `confirmResponsibilityEAN` (CPRCOLSUPPLYPOINTApi; `3998.ada47cff.js`)
- Query: `supplyPointCode`
- Response: empty (HTTP 200/204)

### `GET /supply-points/fixed-products/last-import`

- Operation `getLastSupplyPointWithFixedProductImport` (CPRCOLSUPPLYPOINTApi; `3998.ada47cff.js`)
- Response: JSON `LastSupplyPointImportWithFixedProductResponseBodyDto`:
  - `fileName`
  - `createdAt` (date)

### `GET /supply-points/historical`

- Operation `readHistoricalSupplyPoints` (CPRCOLSUPPLYPOINTApi; `3998.ada47cff.js`)
- **Used by integration**: `api.py` fetch_all
- Response: JSON array of `SupplyPointOverviewDto`:
  - `consumptionPlaceIdIsu`
  - `prodExtOrderType`
  - `productDashboardText`
  - `parentAgreement` (ParentAgreementDto)
    - `parentAgreementIdIsu`
  - `agreement` (AgreementDto)
    - `agreementIdIsu`
    - `agreementAccountClass` (CodebookEntryDto)
    - `agreementElectronicInvoicingTypeId`
    - `isAggregated`
    - `isGrouped`
  - `supplyPointCode`
  - `contract` (ContractDto)
    - `contractIdIsu`
    - `contractAdvancePaymentAmount`
    - `contractAdvancePaymentFrequency` (CodebookEntryDto)
    - `contractName`
    - `contractValidityStartDate` (date)
    - `contractValidityEndDate` (date)
  - `consumptionPlaceName`
  - `contactValue`
  - `advancePaymentChangeNotPossibleReason` (CodebookEntryDto)
  - `canChangeAdvancePayments`
  - `address` (AddressPartsDto)
    - `addressCity` (CodebookEntryDto)
    - `addressLandRegistryNumber`
    - `addressHouseNumber`
    - `addressZipCode`
    - `addressStreet` (CodebookEntryDto)
  - `supplyPointCommodity` (CodebookEntryDto)
  - `supplyPointUniqueId`
  - `productInstanceId`
  - `hasCsvDataFile`
  - `hasMonthlyInvoicing`
  - `supplyPointMeasurementSubKind`
  - `supplyPointNumber`
  - `hiddenByFilter`
  - `Product`
  - `hasFixedProduct`
  - `supplyPointType` (CodebookEntryDto)
  - `productBannerText`
  - `productInfoText`
  - `supplyPointIsContinuousMeasurement`
- Captured sample: probe_out: `supply-points_historical`; snapshot: `/supply-points/historical`

  Response shape (anonymized, values replaced by types):

```json
[
 {
  "consumptionPlaceIdIsu": "string",
  "prodExtOrderType": "",
  "productDashboardText": "string",
  "parentAgreement": {
   "parentAgreementIdIsu": "string"
  },
  "agreement": {
   "agreementIdIsu": "string",
   "agreementElectronicInvoicingTypeId": "",
   "isAggregated": "boolean",
   "isGrouped": "boolean"
  },
  "supplyPointCode": "string",
  "contract": {
   "contractIdIsu": "string",
   "contractAdvancePaymentAmount": "number",
   "contractAdvancePaymentFrequency": {},
   "contractName": "string",
   "contractValidityStartDate": "YYYY-MM-DD",
   "contractValidityEndDate": "YYYY-MM-DD"
  },
  "consumptionPlaceName": "string",
  "address": {
   "addressCity": {
    "value": "string"
   },
   "addressLandRegistryNumber": "string",
   "addressHouseNumber": "string",
   "addressZipCode": "string",
   "addressStreet": {
    "value": "string"
   }
  },
  "supplyPointCommodity": {
   "value": "P1"
  },
  "supplyPointUniqueId": "string",
  "productInstanceId": "string",
  "hasCsvDataFile": "boolean",
  "hasMonthlyInvoicing": "boolean",
  "supplyPointMeasurementSubKind": "",
  "supplyPointNumber": "string",
  "hiddenByFilter": "string",
  "Product": "string",
  "hasFixedProduct": "boolean",
  "productBannerText": "string",
  "productInfoText": "string",
  "supplyPointIsContinuousMeasurement": "boolean"
 }
]
```

### `POST /supply-points/import-fixed-products`

- Operation `importSupplyPointsWithFixedProducts` (CPRCOLSUPPLYPOINTApi; `3998.ada47cff.js`)
- Body: `multipart/form-data` parts `importFile`
- Response: JSON array of `SupplyPointFixedProductImportItemDto`:
  - `consumptionPlaceIdIsu`
  - `partnerId`
  - `supplyPointCode`

### `POST /supply-points/supply-points-by-import`

- Operation `getSupplyPointsByImport` (CPRCOLSUPPLYPOINTApi; `3998.ada47cff.js`)
- Body: `multipart/form-data` parts `contentHighTariff`
- Response: JSON array of `SupplyPointByImportDto`:
  - `selfMeterReadingLowTariff` (SmrLowTariffDto)
    - `meterReadingTariff` (CodebookEntryDto)
    - `meterReadingUnit` (CodebookEntryDto)
    - `meterReadingValue`
    - `meterReadingDocumentId`
  - `supplyPointOverview` (SupplyPointOverviewDto)
    - `consumptionPlaceIdIsu`
    - `prodExtOrderType`
    - `productDashboardText`
    - `parentAgreement` (ParentAgreementDto)
    - `agreement` (AgreementDto)
    - `supplyPointCode`
    - `contract` (ContractDto)
    - `consumptionPlaceName`
    - `contactValue`
    - `advancePaymentChangeNotPossibleReason` (CodebookEntryDto)
    - `canChangeAdvancePayments`
    - `address` (AddressPartsDto)
    - `supplyPointCommodity` (CodebookEntryDto)
    - `supplyPointUniqueId`
    - `productInstanceId`
    - `hasCsvDataFile`
    - `hasMonthlyInvoicing`
    - `supplyPointMeasurementSubKind`
    - `supplyPointNumber`
    - `hiddenByFilter`
    - `Product`
    - `hasFixedProduct`
    - `supplyPointType` (CodebookEntryDto)
    - `productBannerText`
    - `productInfoText`
    - `supplyPointIsContinuousMeasurement`
  - `selfMeterReadingHighTariff` (SmrHighTariffDto)
    - `meterReadingUnit` (CodebookEntryDto)
    - `meterReadingValue`
    - `meterReadingTariff` (CodebookEntryDto)
    - `meterReadingDocumentId`
  - `meterReadingRegisterDate` (date)
  - `supplyPointImportErrors` (SupplyPointImportErrorDto[])
    - `errorMessage`
    - `columnNumber`

### `GET /supply-points/{supplyPointId}/ReadAdvancePlan`

- Operation `readAdvancePlan` (CPRCOLSUPPLYPOINTApi; `3998.ada47cff.js`)
- **Used by integration**: `api.py` get_advance_plan
- Path params: `supplyPointId`
- Response: JSON array of `AdvancePlanDto`:
  - `stavText`
  - `stav`
  - `splatnost`
  - `kDoplaceni`
  - `castkaSplatkyKDoplaceni`
  - `castkaPojisteni`
  - `mena`
  - `castka`
  - `castkaSplatky`
  - `castkaPojisteniKDoplaceni`
- Captured sample: snapshot: `/supply-points/<supplyPointUid>/ReadAdvancePlan`

  Response shape (anonymized, values replaced by types):

```json
[
 {
  "stavText": "string",
  "stav": "number",
  "splatnost": "YYYY-MM-DD",
  "kDoplaceni": "number",
  "castkaSplatkyKDoplaceni": "number",
  "castkaPojisteni": "number",
  "mena": "string",
  "castka": "number",
  "castkaSplatky": "number",
  "castkaPojisteniKDoplaceni": "number"
 }
]
```

### `GET /supply-points/{supplyPointId}/ReadConsumptionHistory`

- Operation `readConsumption` (CPRCOLSUPPLYPOINTApi; `3998.ada47cff.js`)
- **Used by integration**: `api.py` get_consumption_periods, get_payouts
- Path params: `supplyPointId`
- Query: `aggregation`
- Response: JSON array of `ConsumptionDto`:
  - `dateTo` (date)
  - `dateFrom` (date)
  - `consumptionHT`
  - `consumptionLT`
  - `consumptionSum`
  - `consumptionCurrency`
  - `methodOfReading`
  - `consumptionAmount`
  - `product`
  - `graphType`
  - `consumptionSharedLT`
  - `consumptionSharedHT`
  - `consumptionSharedAmountLT`
  - `consumptionSharedAmountHT`
  - `consumptLtShareSap`
  - `consumptHtShareSap`
- Captured sample: probe_out: `supply-points_<supplyPointUid>_ReadConsumptionHistory_aggregation=ALL`; probe_out: `supply-points_<supplyPointUid>_ReadConsumptionHistory_aggregation=DAY`; probe_out: `supply-points_<supplyPointUid>_ReadConsumptionHistory_aggregation=ROK`

  Response shape (anonymized, values replaced by types):

```json
[
 {
  "dateTo": "YYYY-MM-DD",
  "dateFrom": "YYYY-MM-DD",
  "consumptionHT": "number",
  "consumptionLT": "number",
  "consumptionSum": "number",
  "consumptionCurrency": "CZK",
  "methodOfReading": "string",
  "consumptionAmount": "number",
  "product": "string",
  "graphType": "Y",
  "consumptLtShareSap": "string",
  "consumptHtShareSap": "string"
 }
]
```

### `GET /supply-points/{supplyPointId}/ReadMassRemoteControlInfo`

- Operation `getMassRemoteControlInfo` (CPRCOLSUPPLYPOINTApi; `3998.ada47cff.js`)
- Path params: `supplyPointId`
- Response: JSON `TimeSwitchingDto`:
  - `Weekdays` (WeekdaysDto[])
    - `timeSwitchingTimeTo`
    - `timeSwitchingId`
    - `timeSwitchingValidityFrom` (date)
    - `timeSwitchingTimeFrom`
    - `timeSwitchingDayName`
    - `timeSwitchingValidityTo` (date)
    - `timeSwitchingDayOfWeek`
    - `timeSwitchingHdoSignal`
    - `timeSwitchingSignalText`
  - `Weekend` (WeekendDto[])
    - `timeSwitchingTimeTo`
    - `timeSwitchingId`
    - `timeSwitchingValidityFrom` (date)
    - `timeSwitchingTimeFrom`
    - `timeSwitchingDayName`
    - `timeSwitchingValidityTo` (date)
    - `timeSwitchingDayOfWeek`
    - `timeSwitchingHdoSignal`
    - `timeSwitchingSignalText`

### `GET /supply-points/{supplyPointId}/ReadMeterReading`

- Operation `readMeter` (CPRCOLSUPPLYPOINTApi; `3998.ada47cff.js`)
- **Used by integration**: `api.py` get_meter_reading, get_register_readings
- Path params: `supplyPointId`
- Response: JSON array of `MeterReadingDto`:
  - `meterReadingRegisterDate` (date)
  - `selfMeterReadingReason` (CodebookEntryDto)
  - `meterReadingDeviceNumber`
  - `meterReadingType` (CodebookEntryDto)
  - `meterReadingKey`
  - `selfMeterReadingType` (CodebookEntryDto)
  - `selfMeterReadingCompletionDate` (date)
  - `selfMeterReadingInvoiced`
  - `selfMeterReadingStatus` (CodebookEntryDto)
  - `meterReadingTariff` (CodebookEntryDto)
  - `meterReadingUnit` (CodebookEntryDto)
  - `meterReadingValue`
- Captured sample: snapshot: `/supply-points/<supplyPointUid>/ReadMeterReading`

  Response shape (anonymized, values replaced by types):

```json
[
 {
  "meterReadingRegisterDate": "YYYY-MM-DD",
  "meterReadingDeviceNumber": "string",
  "meterReadingType": {
   "entrySystemSpecificId": "ODE_SAMO",
   "systemId": "ODS",
   "entryId": "ODE_SAMO",
   "longValue": "string",
   "entryOrder": "number",
   "language": "CZ",
   "validTo": "date-time",
   "validFrom": "date-time",
   "codebookId": "TP_MET_READ",
   "value": "string"
  },
  "meterReadingKey": "number",
  "meterReadingTariff": {
   "entrySystemSpecificId": "VT",
   "systemId": "ODS",
   "entryId": "VT",
   "longValue": "string",
   "entryOrder": "number",
   "language": "CZ",
   "validTo": "date-time",
   "validFrom": "date-time",
   "codebookId": "TP_MET_READ_TARIFF",
   "value": "string"
  },
  "meterReadingUnit": {
   "entrySystemSpecificId": "KWH",
   "systemId": "ODS",
   "entryId": "KWH",
   "longValue": "string",
   "entryOrder": "number",
   "language": "CZ",
   "validTo": "date-time",
   "validFrom": "date-time",
   "codebookId": "TP_UNIT",
   "value": "string"
  },
  "meterReadingValue": "number"
 }
]
```

### `GET /supply-points/{supplyPointId}/ReadSupplyPointDetail`

- Operation `getOMDetail` (CPRCOLSUPPLYPOINTApi; `3998.ada47cff.js`)
- Path params: `supplyPointId`
- Query: `loadSupplyPointInActiovation`
- Response: JSON `SupplyPointDetailDto`:
  - `BusinessPartner` (BusinessPartnerDto)
    - `individualSurname`
    - `individualFirstName`
    - `partnerType` (CodebookEntryDto)
    - `legalEntityName`
    - `partnerIdentifierId`
  - `Address` (AddressDto)
    - `addressHouseNumber`
    - `addressZipCode`
    - `addressCity` (CodebookEntryDto)
    - `addressStreet` (CodebookEntryDto)
    - `addressLandRegistryNumber`
  - `Product` (ProductDto)
    - `productInstanceValidityEndDate` (date)
    - `productInstancePlannedEndDate` (date)
    - `productInstanceValidityStartDate` (date)
    - `productInstanceName`
    - `ElectronicInvoice` (ElectronicInvoiceDto)
    - `hasOutageInformation`
    - `productPackageIdCrm`
    - `productContractText`
  - `GassSupplyPoint` (GassSupplyPointDto)
  - `HeatSupplyPoint` (HeatSupplyPointDto)
  - `ElectricitySupplyPoint` (ElectricitySupplyPointDto)
  - `Referent` (ReferentDto)
    - `Contact` (ContactDto[])
    - `referentFullName`
    - `partnerId`
  - `SupplyPointDetailAgreement` (SupplyPointDetailAgreementDto)
    - `agreementType` (CodebookEntryDto)
    - `agreementIdIsu`
  - `hasMonthlyInvoicing`
  - `PaymentSettings` (PaymentSettingsDto)
    - `actualPaymentConfiguration` (ActualPaymentConfigurationDto[])
    - `actualAdvancePaymentMethod` (PaymentMethodDto)
    - `actualAdditionalPaymentMethod` (PaymentMethodDto)
    - `actualOverpaymentMethod` (PaymentMethodDto)
  - `vopdDate` (date)
  - `electricitySupplyPointProductionFlag`
  - `showSolarPanel`
  - `productType`

### `PATCH /supply-points/{supplyPointId}/UpdateSupplyPointName`

- Operation `patchSPName` (CPRCOLSUPPLYPOINTApi; `3998.ada47cff.js`)
- Path params: `supplyPointId`
- Body (JSON `BodyDto`):
  - `consumptionPlaceName`
  - `supplyPointId`
- Response: empty (HTTP 200/204)

