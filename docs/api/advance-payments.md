# Advance payments, overpayments, repayments, housing allowance

Advance payment settings and change, payment prescriptions (events), overpayment refunds, instalment (repayment) plans and housing allowance. The advance plan itself is `GET /supply-points/{supplyPointId}/ReadAdvancePlan` in [supply-points.md](supply-points.md).

Generated from the portal bundle (`tools/probe/index.js`, `tools/probe/chunks/*.js`, release col-fe@3.66.0). Field names are the JSON wire names; `(XxxDto)` marks a nested object, `CodebookEntryDto` is described in [README](README.md#codebook-entries). Types not shown are plain strings/numbers/booleans.

| Method | Path | Operation | Integration | Sample |
|---|---|---|---|---|
| GET | [`/advance-payments/due-days`](#get-advance-paymentsdue-days) | getDueDays |  |  |
| GET | [`/advance-payments/state-benefits`](#get-advance-paymentsstate-benefits) | existStateBenefitsForAdvancePayments |  |  |
| POST | [`/advance-payments/{supplyPointId}`](#post-advance-paymentssupplypointid) | advancePaymentUpdate |  |  |
| GET | [`/advance-payments/{supplyPointId}/events`](#get-advance-paymentssupplypointidevents) | getAdvancePaymentEvents | get_advance_settings | yes |
| GET | [`/advance-payments/{supplyPointId}/settings`](#get-advance-paymentssupplypointidsettings) | getAdvancePaymentDetail | get_advance_settings | yes |
| GET | [`/advance-payments/{supplyPointId}/state-benefits`](#get-advance-paymentssupplypointidstate-benefits) | stateBenefits |  |  |
| POST | [`/housing-allowance/financial-data`](#post-housing-allowancefinancial-data) | getFinancialData |  |  |
| GET | [`/housing-allowance/selection`](#get-housing-allowanceselection) | selectSupplyPoints |  | yes |
| POST | [`/housing-allowance/submit`](#post-housing-allowancesubmit) | submitHousingAllowance |  |  |
| POST | [`/overpayments/process`](#post-overpaymentsprocess) | processOverpayment |  |  |
| POST | [`/overpayments/simulation`](#post-overpaymentssimulation) | createOverpaymentSimulation |  |  |
| PATCH | [`/prepayments/change`](#patch-prepaymentschange) | changePrepayment |  |  |
| POST | [`/prepayments/check`](#post-prepaymentscheck) | checkPrepayment |  |  |
| GET | [`/prepayments/first-date/{advancePaymentPlanId}`](#get-prepaymentsfirst-dateadvancepaymentplanid) | getPrepaymentFirstDate |  |  |
| POST | [`/repayments/advance-payments`](#post-repaymentsadvance-payments) | createRepaymentAdvancePayments |  |  |
| POST | [`/repayments/options`](#post-repaymentsoptions) | getRepaymentOptions |  |  |
| GET | [`/repayments/repayment-plan`](#get-repaymentsrepayment-plan) | getRepaymentPlan |  |  |
| POST | [`/repayments/repayment-plan`](#post-repaymentsrepayment-plan) | repaymentPlan |  |  |
| GET | [`/repayments/repayment-plan-id`](#get-repaymentsrepayment-plan-id) | getRepaymentPlanId |  |  |

### `GET /advance-payments/due-days`

- Operation `getDueDays` (CPRCOLADVANCEPAYMENTCHANGEApi; `503.23821561.js`)
- Response: JSON array of `CodebookEntryDto`

### `GET /advance-payments/state-benefits`

- Operation `existStateBenefitsForAdvancePayments` (CPRCOLADVANCEPAYMENTCHANGEApi; `503.23821561.js`)
- Response: JSON object:
  - `existStateBenefitsForAdvancePayments`

### `POST /advance-payments/{supplyPointId}`

- Operation `advancePaymentUpdate` (CPRCOLADVANCEPAYMENTCHANGEApi; `503.23821561.js`)
- Path params: `supplyPointId`
- Body (JSON `AdvancePaymentUpdateRequestDto`):
  - `advancePaymentPermanentAmountEnabled`
  - `advancePaymentChangeValidFrom` (date (YYYY-MM-DD))
  - `advancePaymentChangeAmountNew`
  - `advancePaymentChangeFromLimitExceeded`
  - `advancePaymentCurrentDueDay` (object)
  - `advancePaymentChangeToLimitExceeded`
  - `agreementIdIsu`
  - `useStateBenefitsForAdvancePayments`
  - `advancePaymentChangeWithOverpayment`
  - `advancePaymentPlanCurrentAmount`
  - `advancePaymentPlanId`
  - `advancePaymentDueDay` (object)
- Response: JSON object:
  - `activityId`
  - `appId`

### `GET /advance-payments/{supplyPointId}/events`

- Operation `getAdvancePaymentEvents` (CPRCOLADVANCEPAYMENTCHANGEApi; `503.23821561.js`)
- **Used by integration**: `api.py` get_advance_settings
- Path params: `supplyPointId`
- Response: JSON array of object
- Captured sample: probe_out: `advance-payments_<supplyPointUid>_events`; snapshot: `/advance-payments/<supplyPointUid>/events`

  Response shape (anonymized, values replaced by types):

```json
[
 {
  "paymentPrescriptionPrescribedAmount": "number",
  "paymentPrescriptionVariableSymbol": "string",
  "paymentPrescriptionDueDate": "YYYY-MM-DD",
  "bankAccountFullNumber": "string",
  "bankAccountBankCode": {
   "value": "string"
  },
  "supplyPointCommodity": {
   "value": "E1"
  }
 }
]
```

### `GET /advance-payments/{supplyPointId}/settings`

- Operation `getAdvancePaymentDetail` (CPRCOLADVANCEPAYMENTCHANGEApi; `503.23821561.js`)
- **Used by integration**: `api.py` get_advance_settings
- Path params: `supplyPointId`
- Response: JSON object:
  - `advancePaymentChangeFromLimit`
  - `advancePaymentChangeToLimit`
  - `advancePaymentLastChangePartyId` (CodebookEntryDto)
  - `advancePaymentPlanFartherestDate` (date)
  - `advancePaymentPlanRecommendedAmount`
  - `showUnderpaymentRiskInfo`
  - `advancePaymentChangeWithOverpayment`
  - `agreementIdIsu`
  - `advancePaymentPlanLastChangeDate` (date)
  - `advancePaymentPlanDueDay` (CodebookEntryDto)
  - `advancePaymentPlanCurrentAmount`
  - `advancePaymentPlanFarthestDate` (date)
  - `supplyPointCommodity` (CodebookEntryDto)
  - `isGrouped`
  - `advancePaymentChangePlannedAdvancePaymentInsuranceAmount`
  - `isAggregated`
  - `advancePaymentChangePlannedAdvancePaymentPaymentAmount`
  - `firstFollowingPaymentPrescription` (object)
  - `advancePaymentChangeNewFollowingAmount`
  - `isSipo`
  - `advancePaymentChangeRemainingPayments`
  - `lastFollowingPaymentPrescription` (object)
  - `advancePaymentChangeNewFollowingAmountDate` (date)
  - `supplyPointCode`
  - `advancePaymentPlanId`
  - `advancePaymentPermanentAmountEnabled`
- Captured sample: probe_out: `advance-payments_<supplyPointUid>_settings`; snapshot: `/advance-payments/<supplyPointUid>/settings`

  Response shape (anonymized, values replaced by types):

```json
{
 "advancePaymentChangeFromLimit": "number",
 "advancePaymentChangeToLimit": "number",
 "advancePaymentPlanFartherestDate": "YYYY-MM-DD",
 "advancePaymentChangeWithOverpayment": "boolean",
 "agreementIdIsu": "string",
 "advancePaymentPlanDueDay": {
  "entrySystemSpecificId": "15",
  "systemId": "",
  "entryId": "",
  "longValue": "string",
  "language": "",
  "validTo": "string",
  "validFrom": "string",
  "codebookId": "",
  "value": "string"
 },
 "advancePaymentPlanCurrentAmount": "number",
 "advancePaymentPlanFarthestDate": "YYYY-MM-DD",
 "supplyPointCommodity": {
  "value": "E1"
 },
 "isGrouped": "boolean",
 "isAggregated": "boolean",
 "firstFollowingPaymentPrescription": {
  "paymentPrescriptionDueDate": "YYYY-MM-DD"
 },
 "advancePaymentChangeNewFollowingAmount": "number",
 "isSipo": "boolean",
 "advancePaymentChangeRemainingPayments": "number",
 "lastFollowingPaymentPrescription": {
  "paymentPrescriptionDueDate": "YYYY-MM-DD"
 },
 "advancePaymentChangeNewFollowingAmountDate": "YYYY-MM-DD",
 "supplyPointCode": "string",
 "advancePaymentPlanId": "string",
 "advancePaymentPermanentAmountEnabled": "boolean"
}
```

### `GET /advance-payments/{supplyPointId}/state-benefits`

- Operation `stateBenefits` (CPRCOLADVANCEPAYMENTCHANGEApi; `503.23821561.js`)
- Path params: `supplyPointId`
- Response: JSON object:
  - `stateBenefitsBalance`
  - `useStateBenefitsForAdvancePayments`
  - `stateBenefitsTotalAmount`
  - `stateBenefitsExist`

### `POST /housing-allowance/financial-data`

- Operation `getFinancialData` (CPRCOLHOUSINGALLOWANCEApi; `6795.5111927b.js`, `9176.ea4237f1.js`)
- Body (JSON `FinancialDataRequestBodyDto`):
  - `supplyPointIds`
- Response: JSON object:
  - `supplyPointData` (array)

### `GET /housing-allowance/selection`

- Operation `selectSupplyPoints` (CPRCOLHOUSINGALLOWANCEApi; `6795.5111927b.js`, `9176.ea4237f1.js`)
- Query: `supplyPointId`
- Response: JSON object:
  - `supplyPointIds`
- Captured sample: probe_out: `housing-allowance_selection_supplyPointId=<supplyPointUid>`

  Response shape (anonymized, values replaced by types):

```json
{
 "supplyPointIds": [
  "string"
 ]
}
```

### `POST /housing-allowance/submit`

- Operation `submitHousingAllowance` (CPRCOLHOUSINGALLOWANCEApi; `6795.5111927b.js`, `9176.ea4237f1.js`)
- Body (JSON `SubmitHousingAllowanceRequestBodyDto`):
  - `supplyPointIds`
- Response: JSON object:
  - `email`
  - `mpsvHash`

### `POST /overpayments/process`

- Operation `processOverpayment` (CPRCOLFASAPOOVERPAYMENTSApi; `3261.d60b1221.js`, `5642.2e4b584b.js`)
- Body (JSON `ProcessOverpaymentRequestDto`):
  - `processOverpaymentRefundPrinteringDocumentId`
  - `partnerIdCol`
  - `simulatedOverpaymentAmount` (array)
  - `paymentInformation` (object)
- Response: JSON object:
  - `activityId`
  - `appId`

### `POST /overpayments/simulation`

- Operation `createOverpaymentSimulation` (CPRCOLFASAPOOVERPAYMENTSApi; `3261.d60b1221.js`, `5642.2e4b584b.js`)
- Body (JSON `InlineObject1Dto`):
  - `processOverpaymentRefundPrinteringDocumentId`
- Response: JSON object

### `PATCH /prepayments/change`

- Operation `changePrepayment` (CPRCOLFASAPOOVERPAYMENTSApi; `3261.d60b1221.js`, `5642.2e4b584b.js`)
- Query: `appId`
- Body (JSON `ChangePrepaymentRequestDto`):
  - `overpaymentRefundDueDateAdvancePaymentPlanChange` (date)
  - `advancePaymentPlanId`
  - `paymentInformation` (object)
  - `simulatedPrepaymentAmount` (array)
  - `advancePaymentPlanCurrentAmount`
  - `overpaymentRefundCountChangedAdvancePaymentItems`
- Response: text

### `POST /prepayments/check`

- Operation `checkPrepayment` (CPRCOLFASAPOOVERPAYMENTSApi; `3261.d60b1221.js`, `5642.2e4b584b.js`)
- Query: `appId`
- Body (JSON `InlineObjectDto`):
  - `advancePaymentPlanCurrentAmount`
  - `overpaymentRefundDueDateAdvancePaymentPlanChange` (date)
  - `advancePaymentPlanId`
  - `overpaymentRefundCountChangedAdvancePaymentItems`
- Response: JSON object:
  - `overpaymentRefundAdvancePaymentPlanChangeMode`
  - `actualPrepaymentAmount` (array)
  - `payablePrepaymentItems` (array)
  - `prepaymentInformation` (object)
  - `simulatedPrepaymentAmount` (array)

### `GET /prepayments/first-date/{advancePaymentPlanId}`

- Operation `getPrepaymentFirstDate` (CPRCOLFASAPOOVERPAYMENTSApi; `3261.d60b1221.js`, `5642.2e4b584b.js`)
- Path params: `advancePaymentPlanId`
- Query: `appId`
- Response: text

### `POST /repayments/advance-payments`

- Operation `createRepaymentAdvancePayments` (CPRCOLFASAPOREPAYMENTSApi; `475.d00b1234.js`)
- Body (JSON `CreateAdvancePaymentRepaymentRequestBodyDto`):
  - `advPaymentRepaymentSimulationHeader` (object)
  - `repaymentsRequestHeader` (object)
  - `simulate`
- Response: JSON object:
  - `repaymentPlanRepaymentAmount`
  - `repaymentPlanTotalOverdueAmount`
  - `paymentPrescriptionDocumentNumber`
  - `repaymentPlanTotalRepaymentCount`
  - `repaymentPlanStartDate` (date)
  - `repaymentPlanEndDate` (date)
  - `repaymentPlanTotalInterestAmount`
  - `repaymentPlanInterestRate`
  - `repaymentPlanTotalRepaymentAmount`
  - `paymentPrescriptionVariableSymbol`

### `POST /repayments/options`

- Operation `getRepaymentOptions` (CPRCOLFASAPOREPAYMENTSApi; `475.d00b1234.js`)
- Body (JSON `RepaymentOptionsRequestBodyDto`):
  - `repaymentsRequestHeader` (object)
  - `repaymentPlanStartDate`
- Response: JSON object:
  - `repaymentStartDatePicker` (object)
  - `repaymentPaymentPrescriptions` (array)
  - `advPaymntRepaymentSimulations` (object)
  - `repaymentSimulations` (object)

### `GET /repayments/repayment-plan`

- Operation `getRepaymentPlan` (CPRCOLFASAPOREPAYMENTSApi; `475.d00b1234.js`)
- Query: `contractIdIsu`, `agreementIdIsu`, `paymentPrescriptionDocumentNumber`
- Response: JSON object:
  - `paymentPrescriptionPrescribedAmountPaid`
  - `contractName`
  - `paymentPrescriptionVariableSymbol`
  - `repaymentPrescriptionItems` (array)
  - `paymentPrescriptionPrescribedAmountTotal`
  - `bankAccountIdentifier`
  - `bankAccountBankCode` (CodebookEntryDto)
  - `consumptionPlaceIdIsu`
  - `supplyPointCommodity` (CodebookEntryDto)
  - `address` (object)

### `POST /repayments/repayment-plan`

- Operation `repaymentPlan` (CPRCOLFASAPOREPAYMENTSApi; `475.d00b1234.js`)
- Body (JSON `CreateRepaymentPlanRequestBodyDto`):
  - `repaymentPlanSimulation` (object)
  - `simulate`
  - `repaymentsRequestHeader` (object)
  - `repaymentPlanStartDate` (date (YYYY-MM-DD))
- Response: JSON object:
  - `paymentPrescriptionDocumentNumber`
  - `repaymentPlanTotalRepaymentAmount`
  - `repaymentPlanTotalRepaymentCount`
  - `repaymentPlanStartDate` (date)
  - `repaymentPlanEndDate` (date)
  - `repaymentPlanTotalInterestAmount`
  - `repaymentPlanRepaymentAmount`
  - `repaymentPlanTotalOverdueAmount`
  - `repaymentPlanInterestRate`
  - `repaymentPlanItems` (array)
  - `paymentPrescriptionVariableSymbol`

### `GET /repayments/repayment-plan-id`

- Operation `getRepaymentPlanId` (CPRCOLFASAPOREPAYMENTSApi; `475.d00b1234.js`)
- Query: `invoiceIdIsu`
- Response: JSON object:
  - `paymentPrescriptionHeaderDocumentNumber`

