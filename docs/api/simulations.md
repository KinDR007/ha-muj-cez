# Invoice simulations

Estimate of the next settlement invoice. The integration uses `GET /simulations/invoices/{supplyPointCode}?supplyPointUid=<supplyPointUid>` (path param is the EAN). Item codes used by the integration: `ZUCT_SPOTR_VT` (VT energy), `ZUCT_SPOTR_NT` (NT energy), `ZUCT_STAL_PLAT_EE` (fixed monthly fee).

Generated from the portal bundle (`tools/probe/index.js`, `tools/probe/chunks/*.js`, release col-fe@3.66.0). Field names are the JSON wire names; `(XxxDto)` marks a nested object, `CodebookEntryDto` is described in [README](README.md#codebook-entries). Types not shown are plain strings/numbers/booleans.

| Method | Path | Operation | Integration | Sample |
|---|---|---|---|---|
| POST | [`/invoice-simulations`](#post-invoice-simulations) | getSimulationList |  |  |
| POST | [`/invoice-simulations/calculate`](#post-invoice-simulationscalculate) | calculateInvoiceSimulation |  |  |
| POST | [`/invoice-simulations/create-standard`](#post-invoice-simulationscreate-standard) | createSimulation |  |  |
| GET | [`/invoice-simulations/{invoiceSimulationIdIsu}`](#get-invoice-simulationsinvoicesimulationidisu) | getInvoiceSimulation |  |  |
| GET | [`/simulation-invoice`](#get-simulation-invoice) | getSimulationInvoice |  | yes |
| POST | [`/simulation-invoice/simulation`](#post-simulation-invoicesimulation) | createSimulationInvoice |  |  |
| GET | [`/simulation/invoices/{supplyPointUid}/slicer`](#get-simulationinvoicessupplypointuidslicer) | getInvoiceSimulationDetailSlicer |  |  |
| GET | [`/simulations/invoices`](#get-simulationsinvoices) | getInvoiceSimulations |  |  |
| POST | [`/simulations/invoices/recommend-amount`](#post-simulationsinvoicesrecommend-amount) | recommendAdvancePayment |  |  |
| GET | [`/simulations/invoices/{supplyPointCode}`](#get-simulationsinvoicessupplypointcode) | getInvoiceSimulationDetail | get_simulation | yes |
| GET | [`/simulations/mobile/invoices/{supplyPointUid}`](#get-simulationsmobileinvoicessupplypointuid) | getInvoiceSimulationMobileDetail |  |  |

### `POST /invoice-simulations`

- Operation `getSimulationList` (CPRCOLFASAPOSIMULATIONSApi; `949.4d680241.js`)
- Body (JSON `GetInvoiceSimulationsRequestDto`):
  - `invoiceSimulationSimulationDateTo`
  - `invoiceSimulationSimulationDateFrom`
  - `supplyPointCode`
  - `blockCreateSimulation`
- Response: JSON array of object

### `POST /invoice-simulations/calculate`

- Operation `calculateInvoiceSimulation` (CPRCOLFASAPOSIMULATIONSApi; `949.4d680241.js`)
- Body (JSON `CalculateInvoiceSimulationsRulesRequestDto`):
  - `invoiceSimulationIdIsu`
- Response: JSON array of object

### `POST /invoice-simulations/create-standard`

- Operation `createSimulation` (CPRCOLFASAPOSIMULATIONSApi; `949.4d680241.js`)
- Body (JSON `CreateInvoiceSimulationRequestDto`):
  - `invoiceSimulationSimulationDate`
  - `invoiceSimulationLanguage`
  - `supplyPointCode`
  - `partnerIdCrm`
  - `invoiceSimulationCallHeader` (object)
- Response: JSON array of object

### `GET /invoice-simulations/{invoiceSimulationIdIsu}`

- Operation `getInvoiceSimulation` (CPRCOLFASAPOSIMULATIONSApi; `949.4d680241.js`)
- Path params: `invoiceSimulationIdIsu`
- Query: `invoiceSimulationLanguage`
- Response: JSON array of object

### `GET /simulation-invoice`

- Operation `getSimulationInvoice` (CPRCOLINVOICESIMApi; `4279.beef34f2.js`, `6660.a4da4de4.js`)
- Query: `supplyPointCode`, `supplyPointId`
- Response: JSON object:
  - `invoiceSimulationSimulationDate` (date)
  - `supplyPointId`
  - `supplyPointCode`
  - `meterReadingDoubleTariffFlag`
  - `selfMeterReadingLowTariff`
  - `meterReadingOneTariffFlag`
  - `meterNumber`
  - `selfMeterReadingHighTariff`
  - `meterReadingDeviceNumber`
  - `meterReadingCompletionDate` (date)
  - `invoiceSimulationReason`
  - `invoiceSimulationNumber`
  - `invoiceSimulationMeterReadingItemDescription`
  - `invoiceSimulationForm`
  - `meterReadingInvoicedFlag`
  - `invoiceSimulationCertification`
  - `invoiceSimulationType`
  - `invoiceSimulationInvalidationFlag`
  - `invoiceSimulationWeek`
  - `meterReadingKind`
  - `invoiceSimulationEan`
- Captured sample: probe_out: `simulation-invoice_supplyPointCode=<ean>&supplyPointId=<supplyPointUid>`
  (captured response: error `SAP_ZCOL-259` (ERROR))

### `POST /simulation-invoice/simulation`

- Operation `createSimulationInvoice` (CPRCOLINVOICESIMApi; `4279.beef34f2.js`, `6660.a4da4de4.js`)
- Body (JSON `SimulationRequestBodyDto`):
  - `invoiceSimulationNumber`
  - `invoiceSimulationSimulationDate`
  - `invoiceSimulationEan`
  - `invoiceSimulationReason`
  - `selfMeterReadingLowTariff`
  - `selfMeterReadingHighTariff`
  - `meterReadingDoubleTariffFlag`
  - `invoiceSimulationForm`
  - `invoiceSimulationInvalidationFlag`
  - `invoiceSimulationType`
  - `meterReadingInvoicedFlag`
  - `meterReadingKind`
  - `invoiceSimulationCertification`
  - `meterReadingOneTariffFlag`
  - `supplyPointCode`
  - `invoiceSimulationWeek`
  - `meterReadingCompletionDate`
  - `supplyPointId`
  - `meterReadingDeviceNumber`
  - `invoiceSimulationMeterReadingItemDescription`
  - `meterNumber`
- Response: JSON object:
  - `date` (date)
  - `invoiceSimulationdistributionPart`
  - `invoiceSimulationConsumptionAssumption`
  - `invoiceSimulationbusinessPart`
  - `invoiceSimulationDifference`
  - `invoiceSimulationReceivedPayments`
  - `actId`
  - `invoiceSimulationSurcharge`
  - `invoiceSimulationConsumptionPrice`

### `GET /simulation/invoices/{supplyPointUid}/slicer`

- Operation `getInvoiceSimulationDetailSlicer` (CPRCOLINVOICESIMULATIONApi; `9797.dbfd3b80.js`)
- Path params: `supplyPointUid`
- Query: `aggregateByLevel`
- Response: JSON object:
  - `invoiceSimulationBillingPeriodFrom` (date)
  - `invoiceSimulationBillingPeriodTo` (date)
  - `invoiceSimulationNationalSubsidyFlag`
  - `invoiceSimulationOriginDate` (date)
  - `invoiceSimulationFirstRecommendedAdvancePayment`
  - `InvoiceSimulationInvoiceItemSlicer` (array)
  - `InvoiceSimulationConsumptionSlicer` (array)
  - `InvoiceSimulationDetailAdvancePaymentSlicer` (array)
  - `InvoiceSimulationDetailHeaderSlicer` (array)
  - `InvoiceSimulationDetailPaymentSlicer` (array)
  - `InvoiceSimulationShortSlicer` (array)

### `GET /simulations/invoices`

- Operation `getInvoiceSimulations` (CPRCOLINVOICESIMULATIONApi; `9797.dbfd3b80.js`)
- Response: JSON array of object

### `POST /simulations/invoices/recommend-amount`

- Operation `recommendAdvancePayment` (CPRCOLINVOICESIMULATIONApi; `9797.dbfd3b80.js`)
- Query: `supplyPointUid`
- Body (JSON `ShowRecommendedAdvancePaymentRequestDto`):
  - `supplyPointCode`
- Response: JSON object:
  - `isRecommended`
  - `supplyPointCode`

### `GET /simulations/invoices/{supplyPointCode}`

- Operation `getInvoiceSimulationDetail` (CPRCOLINVOICESIMULATIONApi; `9797.dbfd3b80.js`)
- **Used by integration**: `api.py` get_simulation
- Path params: `supplyPointCode`
- Query: `supplyPointUid`, `aggregateTimeSlices`
- Response: JSON object:
  - `invoiceSimulationDetailPayment` (array)
  - `invoiceSimulationConsumption` (array)
  - `invoiceSimulationDetailHeader` (array)
  - `invoiceSimulationShort` (array)
  - `invoiceSimulationInvoiceItem` (array)
  - `invoiceSimulationBillingPeriodTo` (date)
  - `invoiceSimulationFirstRecommendedAdvancePayment`
  - `invoiceSimulationOriginDate` (date)
  - `invoiceSimulationDetailAdvancePayment` (array)
  - `invoiceSimulationBillingPeriodFrom` (date)
  - `invoiceSimulationNationalSubsidyFlag`
- Captured sample: snapshot: `/simulations/invoices/<ean>?supplyPointUid=<supplyPointUid>`

  Response shape (anonymized, values replaced by types):

```json
{
 "invoiceSimulationConsumption": [
  {
   "consumptionInvoiceQuantityUnit": {
    "entrySystemSpecificId": "KWH",
    "systemId": "ODS",
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
   "consumptionValue": "number",
   "consumptionPeriodTo": "YYYY-MM-DD",
   "consumptionPeriodFrom": "YYYY-MM-DD",
   "consumptionTariff": {
    "entrySystemSpecificId": "VT",
    "systemId": "ODS",
    "entryId": "VT",
    "longValue": "string",
    "entryOrder": "number",
    "language": "CZ",
    "validTo": "date-time",
    "validFrom": "date-time",
    "codebookId": "TP_MET_READ_TARIFF",
    "value": "string",
    "otherValues": []
   },
   "invoiceSimulationIdIsu": "string",
   "consumptionQuantityUnit": {
    "entrySystemSpecificId": "KWH",
    "systemId": "ODS",
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
    "value": "string",
    "otherValues": []
   },
   "meterReadingPreviousValue": "number",
  … (truncated)
```

### `GET /simulations/mobile/invoices/{supplyPointUid}`

- Operation `getInvoiceSimulationMobileDetail` (CPRCOLINVOICESIMULATIONApi; `9797.dbfd3b80.js`)
- Path params: `supplyPointUid`
- Response: JSON object:
  - `actualChart` (object)
  - `predictiveChart` (object)
  - `meterReadingDetails` (array)
  - `invoiceSimulationInvoiceItems` (array)

