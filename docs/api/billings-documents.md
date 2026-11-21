# Billings, invoices, documents, payment methods

Billing documents (invoices `INV`, payout self-billing `SLF`, advances, payments), interactive invoice detail, document archive download, bank accounts and online payment.

### Document download flow (used by the integration)

1. Build a `DocumentFilterDto`: `{"documentDomain": "<DocumentFilterDtoDocumentDomainEnum>", "documentParams": [{"key": "<DocumentFilterParamDtoKeyEnum>", "value": "..."}]}`.
   - Settlement invoice (row from `GET /billings/extended`): domain `INVOICES`, params `PARTNER_ID_CRM`, `HEADER_ID` (billingAccountingDocumentHeaderId), `ACCOUNT_DOCUMENT_NUMBER` (billingReceivablesAndPayablesAccountDocumentNumber), `SNAPSHOT_ID` (billingBalanceSnapshotId), `CONTRACT_ID_ISU` (agreementIdIsu), `SOURCE_SYSTEM` (`SAP_R3_RT130` when `billingSourceSystem == "RTT"`, else `SAP_R3_RQ140`). Header and snapshot ids change over time, use a fresh row.
   - Supply point documents (price lists "Ceník", contract documents): domain `SUPPLY_POINT`, params `SUPPLY_POINT_ID` (12 digit place id) and `CONSUMPTION_PLACE_ID` (EAN); optional `VOPD_DATE`.
2. `POST /documents` with the filter returns the archive list; each item has `documentGuidCol` and `documentParams` (keys such as `DOC_TYPE` (`CEN` = price list), `DOC_ID`, `DOCUMENT_DESCRIPTION`, `DOCUMENT_TEXT`, `VALID_FROM`, `VALID_TO`, `CREATED_DATE`, `O_ID`, `ISU_OBJECT_TYPE`).
3. `POST /documents/{documentGuidCol}/attachment` (single PDF) or `POST /documents/attachment?withRetry=false&force=false` with the filter (invoice data file "Datový soubor.csv") returns `{"attachmentKey": "..."}`.
4. `GET /documents/{attachmentKey}/attachment` returns the bytes (PDF or UTF-8 CSV with BOM). HTTP 404 means no such attachment.

Enums: `DocumentFilterDtoDocumentDomainEnum` = `INSTALLMENT_SCHEDULE`, `INVOICES`, `RETURNED_CORRESPONDENCE`, `PAYMENT_SCHEDULE`, `CASES`, `HEATING_SERVICE`, `PHONE`, `SUPPLY_POINT`, `SEGMENTATION`, `LOGISTICS_PARTNER`, `LOGISTICS_PARTNER_EXPORT`, `MENU_HIERARCHY`, `INVOICES_SINGLE`; `DocumentFilterParamDtoKeyEnum` = `DATE`, `ISU_OBJECT_TYPE`, `SNAPSHOT_ID`, `ACCOUNT_DOCUMENT_NUMBER`, `HEADER_ID`, `PARTNER_ID_CRM`, `SOURCE_SYSTEM`, `BILLING_DOCUMENT_TYPE`, `DOCUMENT_ID_CRM`, `BILLING_MAIN_DOCUMENT_NUMBER`, `CASE_ID`, `SUPPLY_POINT_ID`, `CONTRACT_ID_ISU`, `HEATING_SERVICE_ID`, `SUPPLY_POINT_TYPE_ID`, `PHONE_NUMBER`, `MSG_ID`, `CASE_TYPE_FLAG`, `CONSUMPTION_PLACE_ID`, `AGREEMENT_ID_ISU`, `GUID`, `PRODUCT_INSTANCE_VALIDITY_START_DATE`, `VOPD_DATE`.

`BillingModelDto.statusText` (`BillingModelDtoStatusTextEnum`): `TRANSFERRED`, `PAID`, `INVOICED`, `COMPENSATED`, `SETTLED`, `INKASO_REQUESTED`, `SPREAD_OUT_ADVANCE_PAYMENTS`, `NOT_COMPENSATED`, `OVERDUE`, `SPREAD_OUT_INSTALMENTS`, `UNPAID`, `SIPO_REQUESTED`, `PROCESSING`.

Generated from the portal bundle (`tools/probe/index.js`, `tools/probe/chunks/*.js`, release col-fe@3.66.0). Field names are the JSON wire names; `(XxxDto)` marks a nested object, `CodebookEntryDto` is described in [README](README.md#codebook-entries). Types not shown are plain strings/numbers/booleans.

| Method | Path | Operation | Integration | Sample |
|---|---|---|---|---|
| GET | [`/billing-period`](#get-billing-period) | getBillingPeriod |  |  |
| GET | [`/billings`](#get-billings) | getAll | fetch_all | yes |
| POST | [`/billings/banners`](#post-billingsbanners) | getApplicableBanners |  |  |
| POST | [`/billings/banners-close/{supplyPointCode}/{prodExtOrderType}`](#post-billingsbanners-closesupplypointcodeprodextordertype) | closeBanner |  |  |
| POST | [`/billings/banners-to-view`](#post-billingsbanners-to-view) | bannersToView |  |  |
| GET | [`/billings/basket`](#get-billingsbasket) | getBasket |  |  |
| GET | [`/billings/basket-card-widget-settings`](#get-billingsbasket-card-widget-settings) | getBasketCardWidgetSettings |  |  |
| DELETE | [`/billings/basket-clear`](#delete-billingsbasket-clear) | clearBasket |  |  |
| GET | [`/billings/basket-extended`](#get-billingsbasket-extended) | getBasketExtended |  |  |
| POST | [`/billings/basket-pay`](#post-billingsbasket-pay) | createBasketPayment |  |  |
| POST | [`/billings/basket-pay-rest`](#post-billingsbasket-pay-rest) | createBasketRestPayment |  |  |
| POST | [`/billings/basket-pay-single-token`](#post-billingsbasket-pay-single-token) | createBasketSingleTokenPayment |  |  |
| GET | [`/billings/basket-payment-types`](#get-billingsbasket-payment-types) | getBasketPaymentTypes |  |  |
| GET | [`/billings/basket-qr-payment-info`](#get-billingsbasket-qr-payment-info) | getBasketQRPaymentInfo |  |  |
| POST | [`/billings/basket-remove`](#post-billingsbasket-remove) | removeFromBasket |  |  |
| POST | [`/billings/basket-saldo-add`](#post-billingsbasket-saldo-add) | addToBasketSaldo |  |  |
| GET | [`/billings/basket-user-cards`](#get-billingsbasket-user-cards) | getBasketUserCards |  |  |
| POST | [`/billings/can-store-card`](#post-billingscan-store-card) | canStoreCard |  |  |
| GET | [`/billings/check-state-benefits`](#get-billingscheck-state-benefits) | checkStateBenefits |  |  |
| GET | [`/billings/columns`](#get-billingscolumns) | getColumns |  |  |
| GET | [`/billings/create-snapshot`](#get-billingscreate-snapshot) | createSnapshot |  |  |
| GET | [`/billings/default-columns`](#get-billingsdefault-columns) | getDefaultColumns |  |  |
| POST | [`/billings/detail`](#post-billingsdetail) | getBillingDetail |  |  |
| GET | [`/billings/extended`](#get-billingsextended) | getAllMapped | get_invoice_rows | yes |
| GET | [`/billings/latest-payment-types`](#get-billingslatest-payment-types) | getLatestPaymentTypes |  |  |
| POST | [`/billings/payment-success`](#post-billingspayment-success) | paymentSuccess |  |  |
| POST | [`/billings/payu-order-status`](#post-billingspayu-order-status) | payuOrderStatus |  |  |
| POST | [`/billings/remove-token`](#post-billingsremove-token) | removeToken |  |  |
| PATCH | [`/billings/save-columns`](#patch-billingssave-columns) | saveUserColumns |  |  |
| GET | [`/billings/sp-filter`](#get-billingssp-filter) | getBillingSupplyPointFilter |  | yes |
| POST | [`/billings/state-benefits`](#post-billingsstate-benefits) | getStateBenefits |  |  |
| GET | [`/billings/user-columns`](#get-billingsuser-columns) | getUserColumns |  |  |
| POST | [`/documents`](#post-documents) | getDocuments | get_invoice_pdf, get_price_lists |  |
| POST | [`/documents/attachment`](#post-documentsattachment) | prepareDocumentAttachmentByFilter | get_invoice_csv |  |
| POST | [`/documents/attachment/zip`](#post-documentsattachmentzip) | prepareMultipleDocumentAttachments |  |  |
| POST | [`/documents/check`](#post-documentscheck) | checkDocument |  |  |
| POST | [`/documents/preparation`](#post-documentspreparation) | documentPreparation |  |  |
| GET | [`/documents/{attachmentKey}/attachment`](#get-documentsattachmentkeyattachment) | getDocumentAttachment | get_invoice_csv, get_document_pdf |  |
| POST | [`/documents/{documentGuidCol}/attachment`](#post-documentsdocumentguidcolattachment) | prepareSingleDocumentAttachment | get_document_pdf |  |
| GET | [`/interactive-invoicing/distribution-rate-banner`](#get-interactive-invoicingdistribution-rate-banner) | getRecommendedDistributionRateBanner | get_contract_info | yes |
| GET | [`/interactive-invoicing/invoice-detail`](#get-interactive-invoicinginvoice-detail) | getInteractiveInvoiceDetall |  | yes |
| GET | [`/interactive-invoicing/show-advance-payments`](#get-interactive-invoicingshow-advance-payments) | showAdvancePayments |  |  |
| GET | [`/interactive-invoicing/show-interactive-invoice`](#get-interactive-invoicingshow-interactive-invoice) | showInteractiveInvoice |  |  |
| GET | [`/interactive-invoicing/show-savings-link`](#get-interactive-invoicingshow-savings-link) | showSavingsLink |  |  |
| GET | [`/interactive-invoicing/upcoming-invoice-banner`](#get-interactive-invoicingupcoming-invoice-banner) | showUpcomingInvoiceBanner |  | yes |
| GET | [`/payment-methods/GetActualBankAccounts`](#get-payment-methodsgetactualbankaccounts) | getBanks |  | yes |
| GET | [`/payment-methods/bank-accounts`](#get-payment-methodsbank-accounts) | getBankAccounts |  |  |
| PUT | [`/payment-methods/bank-accounts`](#put-payment-methodsbank-accounts) | updateBankAccounts |  |  |
| POST | [`/payment-methods/bank-accounts/hide`](#post-payment-methodsbank-accountshide) | hideBankAccount |  |  |
| POST | [`/payment-methods/change-advance-possible`](#post-payment-methodschange-advance-possible) | canChangeAdvancePayment |  |  |
| POST | [`/payment-methods/get`](#post-payment-methodsget) | getPaymentMethods |  |  |
| POST | [`/payment-methods/set`](#post-payment-methodsset) | setPaymentMethods |  |  |
| GET | [`/payment-methods/{supplyPointId}/GetActualPaymentMethod`](#get-payment-methodssupplypointidgetactualpaymentmethod) | getPaymentMethod |  |  |
| POST | [`/self-service/payment-gateway`](#post-self-servicepayment-gateway) | fetchPayuUrl |  |  |

### `GET /billing-period`

- Operation `getBillingPeriod` (CPRCOLBILLINGApi; `9229.de5cae61.js`)
- Query: `supplyPointId`
- Response: JSON `GetBillingPeriodResponseDto`:
  - `invoiceSimulationBillingPeriodFrom` (date)
  - `invoiceSimulationBillingPeriodTo` (date)

### `GET /billings`

- Operation `getAll` (CPRCOLBILLINGApi; `9229.de5cae61.js`)
- **Used by integration**: `api.py` fetch_all
- Query: `includeNotPayed`
- Response: JSON array of `BillingDto`:
  - `billingOriginalReceivablesAndPayablesAccountDocumentNumber`
  - `billingOriginalAccountingDocumentNumber`
  - `billingOriginalSettlementDate` (date)
  - `billingOriginalVariableSymbol`
  - `billingAccountingDocumentTypeText`
  - `billingOriginalSettlementReason`
  - `billingAccountingDocumentHeaderId`
  - `billingAccountingDocumentStatus`
  - `billingAccountingDocumentExcludedType`
  - `billingDocumentItemMainOperation`
  - `billingIsDocumentDebtFlag`
  - `billingAdvancePaymentPlanNumber`
  - `billingMaturityDate` (date)
  - `billingTotalAmount`
  - `billingAccountingDocumentNumber`
  - `billingSettlementPeriodTo` (date)
  - `billingAccountingDocumentAcquisitionDate` (date)
  - `billingDetailExistsFlag`
  - `billingEColPaidAmount`
  - `billingSubTotalAmount`
  - `billingSourceSystem`
  - `billingReminderFee`
  - `billingMainDocumentType`
  - `billingActualPaymentType`
  - `billingSettlementDate` (date)
  - `contractIdIsu`
  - `billingClearingAmount2`
  - `billingSettlementRestriction`
  - `billingEColClearingAmount`
  - `billingSettlementPeriodFrom` (date)
  - `billingMainDocumentNumber`
  - `billingAccountingDocumentType`
  - `billingSettlementReason`
  - `billingTransactionCurrency`
  - `billingVariableSymbol`
  - `billingIsReadFlag`
  - `billingReceivablesAndPayablesAccountDocumentNumber`
  - `billingPaymentOrder`
  - `contractCompanyCode` (CodebookEntryDto)
  - `billingAccountingDocumentType2`
  - `billingAccountingDocumentDate` (date)
  - `billingBalance`
  - `partnerIdCrm`
  - `billingClaimInvoiceNumber`
  - `agreementIdIsu`
  - `billingBalanceSnapshotId`
  - `billingAmountTransferedToNextBillingPeriod`
  - `consumptionPlaceInfo` (object)
  - `billingEColClearingSign`
  - `billingIsNegative`
  - `billingSourceDocumentType`
  - `billingInvoiceType`
  - `paymentPrescriptionDocumentOriginKey`
- Captured sample: probe_out: `billings_includeNotPayed=true`; snapshot: `/billings?includeNotPayed=true`

  Response shape (anonymized, values replaced by types):

```json
[
 {
  "billingAccountingDocumentTypeText": "string",
  "billingAccountingDocumentHeaderId": "number",
  "billingAccountingDocumentStatus": "string",
  "billingAccountingDocumentExcludedType": "",
  "billingDocumentItemMainOperation": "string",
  "billingAdvancePaymentPlanNumber": "string",
  "billingMaturityDate": "YYYY-MM-DD",
  "billingTotalAmount": "number",
  "billingAccountingDocumentNumber": "string",
  "billingAccountingDocumentAcquisitionDate": "YYYY-MM-DD",
  "billingDetailExistsFlag": "boolean",
  "billingEColPaidAmount": "number",
  "billingSubTotalAmount": "number",
  "billingSourceSystem": "string",
  "billingReminderFee": "number",
  "billingMainDocumentType": "",
  "billingActualPaymentType": "",
  "billingSettlementDate": "YYYY-MM-DD",
  "contractIdIsu": "string",
  "billingClearingAmount2": "number",
  "billingSettlementRestriction": "string",
  "billingEColClearingAmount": "number",
  "billingMainDocumentNumber": "string",
  "billingAccountingDocumentType": "",
  "billingSettlementReason": "string",
  "billingTransactionCurrency": "CZK",
  "billingVariableSymbol": "string",
  "billingReceivablesAndPayablesAccountDocumentNumber": "string",
  "billingPaymentOrder": "string",
  "contractCompanyCode": {
   "entrySystemSpecificId": "",
   "systemId": "",
   "entryId": "",
   "longValue": "string",
   "language": "",
   "validTo": "string",
   "validFrom": "string",
   "codebookId": "",
   "value": "string"
  },
  "billingAccountingDocumentType2": "UPO",
  "billingAccountingDocumentDate": "YYYY-MM-DD",
  "billingBalance": "number",
  "partnerIdCrm": "string",
  "billingClaimInvoiceNumber": "string",
  "agreementIdIsu": "string",
  "billingBalanceSnapshotId": "string",
  "billingAmountTransferedToNextBillingPeriod": "number",
  "consumptionPlaceInfo": {
   "isHeat": "boolean",
   "consumptionPlaceIdIsu": "string",
   "consumptionPlaceName": "string"
  },
  "billingEColClearingSign": "string",
  "billingIsNegative": "boolean",
  "billingSourceDocumentType": "",
  "billingInvoiceType": "",
  "paymentPrescriptionDocumentOriginKey": "string"
 }
]
```

### `POST /billings/banners`

- Operation `getApplicableBanners` (CPRCOLBILLINGApi; `9229.de5cae61.js`)
- Body (JSON `ApplicableBannersRequestDto`):
  - `supplyPointUid`
  - `viewName`
- Response: JSON `ApplicableBannersDto`:
  - `upcomingInvoiceBanner` (UpcomingInvoiceBannerDto)
    - `statusMotive`
    - `order`
  - `predictiveInvoiceBanner` (PredictiveInvoiceBannerDto)
    - `invoiceSimulationTotalAmount`
    - `order`
    - `statusMotive`
    - `currency`
    - `isContinuousMeasurement`
  - `advanceRecommendationBanner` (AdvanceRecommendationBannerDto)
    - `order`
    - `recommendationVariant`
    - `statusMotive`
    - `recommendationAdvanceAmount`
    - `currency`
  - `productOfferBanner` (ProductOfferBannerDto)
    - `billingMaturityDate` (date)
    - `billingVariableSymbol`
    - `billingTransactionCurrency`
    - `billingTotalAmount`
    - `bankAccountIban`
    - `bankAccountFullNumber`
  - `dynamicTariffBanner` (DynamicTariffBannerDto)
    - `acquisitionDate` (date)
    - `currency`
    - `order`
    - `statusMotive`
    - `invoiceTotalAmount`
    - `showPayButton`
    - `maturityDate` (date)
    - `invoiceIdentifier`
    - `billingComputedId`
    - `showLabel`
    - `consumptionPlaceIdIsu`
  - `dataPreparationBanner` (DataPreparationBannerDto)
    - `billingSourceSystem`
    - `billingAccountingDocumentType2`
    - `consumptionPlaceIdIsu`
    - `partnerIdCrm`
    - `agreementIdIsu`
    - `billingReceivablesAndPayablesAccountDocumentNumber`
    - `billingAccountingDocumentHeaderId`
    - `billingBalanceSnapshotId`
    - `billingSettlementPeriodTo` (date)
  - `existingInvoiceBanner` (ExistingInvoiceBannerDto)
    - `acquisitionDate` (date)
    - `currency`
    - `order`
    - `statusMotive`
    - `invoiceTotalAmount`
    - `showPayButton`
    - `maturityDate` (date)
    - `invoiceIdentifier`
    - `billingComputedId`
    - `showLabel`
    - `consumptionPlaceIdIsu`

### `POST /billings/banners-close/{supplyPointCode}/{prodExtOrderType}`

- Operation `closeBanner` (CPRCOLBILLINGApi; `9229.de5cae61.js`)
- Path params: `supplyPointCode`, `prodExtOrderType`
- Response: empty (HTTP 200/204)

### `POST /billings/banners-to-view`

- Operation `bannersToView` (CPRCOLBILLINGApi; `9229.de5cae61.js`)
- Body (JSON `BannersToViewRequestDto`):
  - `hasCsvDocument`
  - `commodityId`
  - `plbDdpdf`
  - `hasCezBezStarosti`
  - `cezBezStarostiCastka`
  - `billingSettlementPeriodTo` (date)
  - `billingSettlementPeriodFrom` (date)
  - `pdfProgress`
  - `billingDocumentDetails` (BillingDocumentDetailDto[])
    - `billingTransactionCurrency`
    - `billingBalanceSnapshotId`
    - `billingEColClearingAmount`
    - `billingMaturityDate` (date)
    - `zzinfo`
    - `billingVariableSymbol`
    - `billingReceivablesAndPayablesAccountDocumentNumber`
    - `billingSettlementDate` (date)
    - `paymentPayerName`
    - `billingAccountingDocumentHeaderId`
    - `partnerIdCrm`
    - `agreementIdIsu`
    - `paymentPrescriptionDocumentType` (CodebookEntryDto)
    - `paymentPrescriptionDocumentOriginKey`
  - `reminders` (ReminderDto[])
    - `billingAdvanceAmountNew`
    - `billingReceivablesAndPayablesAccountDocumentNumber`
    - `billingStateBenefitAmount`
    - `billingAdvanceAmountOld`
    - `billingTransactionCurrency`
    - `billingStateBenefitDate` (date)
    - `billingAdvancePaymentPlanRowNumber`
  - `bankAccounts` (BankAccountCEZDto[])
    - `bankAccountId`
    - `bankAccountIban`
    - `bankAccountBankCode` (CodebookEntryDto)
    - `bankAccountFullNumber`
  - `supplyPoints` (SupplyPointDto[])
    - `contractIdCrm`
    - `supplyPointCode`
    - `productInstanceTypeId`
    - `supplyPointId`
    - `supplyPointName`
    - `supplyPointNumber`
    - `supplyPointAddress`
  - `meterReadings` (MeterReadingDto[])
    - `meterReadingRegisterDate` (date)
    - `meterReadingTariff` (CodebookEntryDto)
    - `meterReadingValue`
    - `meterReadingUnit` (CodebookEntryDto)
    - `meterReadingDeviceNumber`
    - `meterReadingSupplyPointCode`
  - `notifications` (NotificationDto[])
    - `notificationType`
    - `notificationDate` (date)
    - `notificationRecipient`
  - `superiorBilling` (SuperiorBillingDto)
    - `contractIdCrm`
    - `supplyPointCode`
    - `productInstanceTypeId`
    - `supplyPointId`
    - `supplyPointName`
    - `supplyPointNumber`
    - `supplyPointAddress`
  - `paymentMethodsUser` (PaymentMethodsUserDto)
    - `overPaymentToAdvancePayment`
    - `actualAdvancePaymentMethod` (PaymentMethodWithBankIdDto)
    - `allowedAdditionalPaymentMethod` (PaymentMethodDto[])
    - `allowedOverpaymentMethod` (PaymentMethodDto[])
    - `PaymentMethodAllowedCombination` (PaymentMethodAllowedCombinationDto[])
    - `actualAdditionalPaymentMethod` (PaymentMethodWithBankIdDto)
    - `OverPaymentMethod` (OverPaymentMethodDto)
    - `actualOverpaymentMethod` (PaymentMethodWithBankIdDto)
    - `AdvancePaymentMethod` (AdvancePaymentMethodDto)
    - `AdditionalPaymentMethod` (AdditionalPaymentMethodDto)
    - `allowedAdvancePaymentMethod` (PaymentMethodDto[])
    - `partnerBankAccounts` (BankAccountDto[])
  - `distributorReadings` (DistributorReadingDto[])
    - `readingType`
    - `initialReading`
    - `meterNumber`
    - `dateFrom` (date)
    - `unit`
    - `dateTo` (date)
    - `invoicedQuantity`
    - `finalReading`
    - `volumeCoefficient`
    - `combustionHeat`
    - `differentialQuantity`
    - `differentialUnit`
    - `consumptionPlaceId`
    - `agreementIdIsu`
    - `contractIdIsu`
  - `billingStateBenefits` (StateBenefitDto[])
    - `billingAdvanceAmountNew`
    - `billingReceivablesAndPayablesAccountDocumentNumber`
    - `billingStateBenefitAmount`
    - `billingAdvanceAmountOld`
    - `billingTransactionCurrency`
    - `billingStateBenefitDate` (date)
    - `billingAdvancePaymentPlanRowNumber`
  - `billingStateBenefitsOpenAmount`
- Response: JSON array of `BannerDetailDto`:
  - `viewName`
  - `supplyPointUid`

### `GET /billings/basket`

- Operation `getBasket` (CPRCOLBILLINGApi; `9229.de5cae61.js`)
- Response: JSON array of `FicaDocumentDto`:
  - `billingTotalAmount`
  - `billingDocumentItemMainOperation`
  - `partnerIdCrm`
  - `billingActualPaymentType`
  - `billingClaimInvoiceNumber`
  - `billingAmountTransferedToNextBillingPeriod`
  - `billingSettlementDate` (date)
  - `billingSettlementReason`
  - `billingSubTotalAmount`
  - `consumptionPlaceInfo` (ConsumptionPlaceInfoDto)
    - `isHeat`
    - `consumptionPlaceIdIsu`
    - `consumptionPlaceName`
    - `address` (AddressPlaceInfoDto)
  - `billingEColPaidAmount`
  - `billingReceivablesAndPayablesAccountDocumentNumber`
  - `contractIdIsu`
  - `billingMainDocumentNumber`
  - `billingSettlementPeriodTo` (date)
  - `billingTransactionCurrency`
  - `billingMainDocumentType`
  - `billingAccountingDocumentHeaderId`
  - `contractCompanyCode` (CodebookEntryDto)
  - `billingSettlementPeriodFrom` (date)
  - `billingAdvancePaymentPlanNumber`
  - `billingPaymentOrder`
  - `billingVariableSymbol`
  - `agreementIdIsu`
  - `billingBalanceSnapshotId`
  - `billingBalance`
  - `billingClearingAmount2`
  - `billingSettlementRestriction`
  - `billingReminderFee`
  - `billingIsDocumentDebtFlag`
  - `billingIsReadFlag`
  - `billingAccountingDocumentType`
  - `billingAccountingDocumentExcludedType`
  - `billingAccountingDocumentDate` (date)
  - `billingAccountingDocumentType2`
  - `billingEColClearingAmount`
  - `billingSourceSystem`
  - `billingMaturityDate` (date)
  - `billingAccountingDocumentTypeText`
  - `billingDetailExistsFlag`
  - `billingAccountingDocumentAcquisitionDate` (date)
  - `billingAccountingDocumentNumber`
  - `billingAccountingDocumentStatus`
  - `productInstanceTypeId`

### `GET /billings/basket-card-widget-settings`

- Operation `getBasketCardWidgetSettings` (CPRCOLBILLINGApi; `9229.de5cae61.js`)
- Response: JSON `WidgetSettingsDto`:
  - `cvvUrl`
  - `sig`
  - `totalAmount`
  - `currencyCode`
  - `language`
  - `url`
  - `storeCard`
  - `email`
  - `posId`
  - `shopName`

### `DELETE /billings/basket-clear`

- Operation `clearBasket` (CPRCOLBILLINGApi; `9229.de5cae61.js`)
- Response: empty (HTTP 200/204)

### `GET /billings/basket-extended`

- Operation `getBasketExtended` (CPRCOLBILLINGApi; `9229.de5cae61.js`)
- Response: JSON array of `BillingModelDto`

### `POST /billings/basket-pay`

- Operation `createBasketPayment` (CPRCOLBILLINGApi; `9229.de5cae61.js`)
- Body (JSON `PayTypeDto`):
  - `paymentType`
- Response: text

### `POST /billings/basket-pay-rest`

- Operation `createBasketRestPayment` (CPRCOLBILLINGApi; `9229.de5cae61.js`)
- Query: `localUrl`, `forMobile`
- Body (JSON `PayTypeDto`):
  - `paymentType`
- Response: JSON `OrderCreateResponseHolderDto`:
  - `htmlType`
  - `rawHtmlResponse`
  - `orderCreateResponse` (OrderCreateResponseDto)
    - `extOrderId`
    - `redirectUri`
    - `widgetSettings` (WidgetSettingsDto)
    - `orderId`
    - `status` (StatusDto)
    - `payMethods` (PayMethodsWrapperDto)

### `POST /billings/basket-pay-single-token`

- Operation `createBasketSingleTokenPayment` (CPRCOLBILLINGApi; `9229.de5cae61.js`)
- Query: `localUrl`, `forMobile`
- Body (JSON `PayUTokenDto`):
  - `maskedCard`
  - `tokenType`
  - `type`
  - `value`
- Response: JSON `OrderCreateResponseHolderDto`:
  - `htmlType`
  - `rawHtmlResponse`
  - `orderCreateResponse` (OrderCreateResponseDto)
    - `extOrderId`
    - `redirectUri`
    - `widgetSettings` (WidgetSettingsDto)
    - `orderId`
    - `status` (StatusDto)
    - `payMethods` (PayMethodsWrapperDto)

### `GET /billings/basket-payment-types`

- Operation `getBasketPaymentTypes` (CPRCOLBILLINGApi; `9229.de5cae61.js`)
- Response: JSON array of `PaymentTypeDto`:
  - `type`
  - `min`
  - `max`
  - `name`
  - `img`
  - `enabled`
  - `overLimit`

### `GET /billings/basket-qr-payment-info`

- Operation `getBasketQRPaymentInfo` (CPRCOLBILLINGApi; `9229.de5cae61.js`)
- Response: JSON `QRPaymentInfoDto`:
  - `group`
  - `name`
  - `description`

### `POST /billings/basket-remove`

- Operation `removeFromBasket` (CPRCOLBILLINGApi; `9229.de5cae61.js`)
- Body (JSON `DetailRequestRestDto`):
  - `billingSourceSystem`
  - `billingAccountingDocumentType2`
  - `consumptionPlaceIdIsu`
  - `partnerIdCrm`
  - `agreementIdIsu`
  - `billingReceivablesAndPayablesAccountDocumentNumber`
  - `billingAccountingDocumentHeaderId`
  - `billingBalanceSnapshotId`
  - `billingSettlementPeriodTo` (date)
- Response: text

### `POST /billings/basket-saldo-add`

- Operation `addToBasketSaldo` (CPRCOLBILLINGApi; `9229.de5cae61.js`)
- Body (JSON `ListRequestRestDto`):
  - `DetailRequestRest` (DetailRequestRestDto[])
    - `billingSourceSystem`
    - `billingAccountingDocumentType2`
    - `consumptionPlaceIdIsu`
    - `partnerIdCrm`
    - `agreementIdIsu`
    - `billingReceivablesAndPayablesAccountDocumentNumber`
    - `billingAccountingDocumentHeaderId`
    - `billingBalanceSnapshotId`
    - `billingSettlementPeriodTo` (date)
- Response: text

### `GET /billings/basket-user-cards`

- Operation `getBasketUserCards` (CPRCOLBILLINGApi; `9229.de5cae61.js`)
- Response: JSON `PayMethodsDto`:
  - `cardTokens` (CardTokenDto[])
    - `cardExpirationYear`
    - `cardExpirationMonth`
    - `cardBrand`
    - `value`
    - `brandImageUrl`
    - `preferred`
    - `cardNumberMasked`
    - `status`
  - `payByLinks` (PayByLinkDto[])
    - `value`
    - `name`
    - `brandImageUrl`
    - `status`

### `POST /billings/can-store-card`

- Operation `canStoreCard` (CPRCOLBILLINGApi; `9229.de5cae61.js`)
- Response: JSON `CanStoreCardResponseDto`:
  - `canStoreCard`
  - `message`

### `GET /billings/check-state-benefits`

- Operation `checkStateBenefits` (CPRCOLBILLINGApi; `9229.de5cae61.js`)
- Response: JSON `CheckStateBenefitsResponseDto`:
  - `hasStateBenefits`

### `GET /billings/columns`

- Operation `getColumns` (CPRCOLBILLINGApi; `9229.de5cae61.js`)
- Response: JSON array of `ReadableColumnDto`:
  - `group`
  - `name`
  - `description`

### `GET /billings/create-snapshot`

- Operation `createSnapshot` (CPRCOLBILLINGApi; `9229.de5cae61.js`)
- Query: `force`
- Response: empty (HTTP 200/204)

### `GET /billings/default-columns`

- Operation `getDefaultColumns` (CPRCOLBILLINGApi; `9229.de5cae61.js`)
- Response: JSON object

### `POST /billings/detail`

- Operation `getBillingDetail` (CPRCOLBILLINGApi; `9229.de5cae61.js`)
- Body (JSON `DetailRequestRestDto`):
  - `billingSourceSystem`
  - `billingAccountingDocumentType2`
  - `consumptionPlaceIdIsu`
  - `partnerIdCrm`
  - `agreementIdIsu`
  - `billingReceivablesAndPayablesAccountDocumentNumber`
  - `billingAccountingDocumentHeaderId`
  - `billingBalanceSnapshotId`
  - `billingSettlementPeriodTo` (date)
- Response: JSON `BillingDetailDto`:
  - `hasCsvDocument`
  - `commodityId`
  - `plbDdpdf`
  - `hasCezBezStarosti`
  - `cezBezStarostiCastka`
  - `billingSettlementPeriodTo` (date)
  - `billingSettlementPeriodFrom` (date)
  - `pdfProgress`
  - `billingDocumentDetails` (BillingDocumentDetailDto[])
    - `billingTransactionCurrency`
    - `billingBalanceSnapshotId`
    - `billingEColClearingAmount`
    - `billingMaturityDate` (date)
    - `zzinfo`
    - `billingVariableSymbol`
    - `billingReceivablesAndPayablesAccountDocumentNumber`
    - `billingSettlementDate` (date)
    - `paymentPayerName`
    - `billingAccountingDocumentHeaderId`
    - `partnerIdCrm`
    - `agreementIdIsu`
    - `paymentPrescriptionDocumentType` (CodebookEntryDto)
    - `paymentPrescriptionDocumentOriginKey`
  - `reminders` (ReminderDto[])
    - `billingAdvanceAmountNew`
    - `billingReceivablesAndPayablesAccountDocumentNumber`
    - `billingStateBenefitAmount`
    - `billingAdvanceAmountOld`
    - `billingTransactionCurrency`
    - `billingStateBenefitDate` (date)
    - `billingAdvancePaymentPlanRowNumber`
  - `bankAccounts` (BankAccountCEZDto[])
    - `bankAccountId`
    - `bankAccountIban`
    - `bankAccountBankCode` (CodebookEntryDto)
    - `bankAccountFullNumber`
  - `supplyPoints` (SupplyPointDto[])
    - `contractIdCrm`
    - `supplyPointCode`
    - `productInstanceTypeId`
    - `supplyPointId`
    - `supplyPointName`
    - `supplyPointNumber`
    - `supplyPointAddress`
  - `meterReadings` (MeterReadingDto[])
    - `meterReadingRegisterDate` (date)
    - `meterReadingTariff` (CodebookEntryDto)
    - `meterReadingValue`
    - `meterReadingUnit` (CodebookEntryDto)
    - `meterReadingDeviceNumber`
    - `meterReadingSupplyPointCode`
  - `notifications` (NotificationDto[])
    - `notificationType`
    - `notificationDate` (date)
    - `notificationRecipient`
  - `superiorBilling` (SuperiorBillingDto)
    - `contractIdCrm`
    - `supplyPointCode`
    - `productInstanceTypeId`
    - `supplyPointId`
    - `supplyPointName`
    - `supplyPointNumber`
    - `supplyPointAddress`
  - `paymentMethodsUser` (PaymentMethodsUserDto)
    - `overPaymentToAdvancePayment`
    - `actualAdvancePaymentMethod` (PaymentMethodWithBankIdDto)
    - `allowedAdditionalPaymentMethod` (PaymentMethodDto[])
    - `allowedOverpaymentMethod` (PaymentMethodDto[])
    - `PaymentMethodAllowedCombination` (PaymentMethodAllowedCombinationDto[])
    - `actualAdditionalPaymentMethod` (PaymentMethodWithBankIdDto)
    - `OverPaymentMethod` (OverPaymentMethodDto)
    - `actualOverpaymentMethod` (PaymentMethodWithBankIdDto)
    - `AdvancePaymentMethod` (AdvancePaymentMethodDto)
    - `AdditionalPaymentMethod` (AdditionalPaymentMethodDto)
    - `allowedAdvancePaymentMethod` (PaymentMethodDto[])
    - `partnerBankAccounts` (BankAccountDto[])
  - `distributorReadings` (DistributorReadingDto[])
    - `readingType`
    - `initialReading`
    - `meterNumber`
    - `dateFrom` (date)
    - `unit`
    - `dateTo` (date)
    - `invoicedQuantity`
    - `finalReading`
    - `volumeCoefficient`
    - `combustionHeat`
    - `differentialQuantity`
    - `differentialUnit`
    - `consumptionPlaceId`
    - `agreementIdIsu`
    - `contractIdIsu`
  - `billingStateBenefits` (StateBenefitDto[])
    - `billingAdvanceAmountNew`
    - `billingReceivablesAndPayablesAccountDocumentNumber`
    - `billingStateBenefitAmount`
    - `billingAdvanceAmountOld`
    - `billingTransactionCurrency`
    - `billingStateBenefitDate` (date)
    - `billingAdvancePaymentPlanRowNumber`
  - `billingStateBenefitsOpenAmount`

### `GET /billings/extended`

- Operation `getAllMapped` (CPRCOLBILLINGApi; `9229.de5cae61.js`)
- **Used by integration**: `api.py` get_invoice_rows
- Query: `includeNotPayed`
- Response: JSON array of `BillingModelDto`
- Captured sample: probe_out: `billings_extended_includeNotPayed=true`

  Response shape (anonymized, values replaced by types):

```json
[
 {
  "billingAccountingDocumentTypeText": "string",
  "billingAccountingDocumentHeaderId": "number",
  "billingAccountingDocumentStatus": "string",
  "billingAccountingDocumentExcludedType": "",
  "billingDocumentItemMainOperation": "string",
  "billingAdvancePaymentPlanNumber": "string",
  "billingMaturityDate": "YYYY-MM-DD",
  "billingTotalAmount": "number",
  "billingAccountingDocumentNumber": "string",
  "billingAccountingDocumentAcquisitionDate": "YYYY-MM-DD",
  "billingDetailExistsFlag": "boolean",
  "billingEColPaidAmount": "number",
  "billingSubTotalAmount": "number",
  "billingSourceSystem": "string",
  "billingReminderFee": "number",
  "billingMainDocumentType": "3",
  "billingActualPaymentType": "I",
  "contractIdIsu": "string",
  "billingClearingAmount2": "number",
  "billingSettlementRestriction": "string",
  "billingEColClearingAmount": "number",
  "billingMainDocumentNumber": "string",
  "billingAccountingDocumentType": "BBP",
  "billingSettlementReason": "string",
  "billingTransactionCurrency": "CZK",
  "billingVariableSymbol": "string",
  "billingReceivablesAndPayablesAccountDocumentNumber": "string",
  "billingPaymentOrder": "string",
  "contractCompanyCode": {
   "entrySystemSpecificId": "3100",
   "systemId": "",
   "entryId": "",
   "longValue": "string",
   "language": "",
   "validTo": "string",
   "validFrom": "string",
   "codebookId": "",
   "value": "string"
  },
  "billingAccountingDocumentType2": "BBP",
  "billingAccountingDocumentDate": "YYYY-MM-DD",
  "billingBalance": "number",
  "partnerIdCrm": "string",
  "billingClaimInvoiceNumber": "string",
  "agreementIdIsu": "string",
  "billingBalanceSnapshotId": "string",
  "billingAmountTransferedToNextBillingPeriod": "number",
  "consumptionPlaceInfo": {
   "isHeat": "boolean",
   "consumptionPlaceIdIsu": "string",
   "consumptionPlaceName": "string",
   "address": {
    "addressStreet": {
     "value": "string"
    },
    "addressZipCode": "string",
    "addressLandRegistryNumber": "string",
    "addressHouseNumber": "string",
    "addressCity": {
     "value": "string"
    }
   }
  },
  "billingEColClearingSign": "string",
  "billingIsNegative": "boolean",
  "billingSourceDocumentType": "",
  "billingInvoiceType": "",
  "paymentPrescriptionDocumentOriginKey": "string",
  … (truncated)
```

### `GET /billings/latest-payment-types`

- Operation `getLatestPaymentTypes` (CPRCOLBILLINGApi; `9229.de5cae61.js`)
- Response: JSON array of `LatestPaymentTypeDto`:
  - `type`
  - `value`
  - `cardNumberMasked`
  - `name`
  - `imageUrl`

### `POST /billings/payment-success`

- Operation `paymentSuccess` (CPRCOLBILLINGApi; `9229.de5cae61.js`)
- Response: text

### `POST /billings/payu-order-status`

- Operation `payuOrderStatus` (CPRCOLBILLINGApi; `9229.de5cae61.js`)
- Response: JSON `PaymentStatRestDto`:
  - `orderStatus`
  - `respStatus`

### `POST /billings/remove-token`

- Operation `removeToken` (CPRCOLBILLINGApi; `9229.de5cae61.js`)
- Body (JSON `TokenDto`):
  - `token`
- Response: empty (HTTP 200/204)

### `PATCH /billings/save-columns`

- Operation `saveUserColumns` (CPRCOLBILLINGApi; `9229.de5cae61.js`)
- Body (JSON `UserColumnsFilterDto`):
  - `userColumnsFilter`
- Response: empty (HTTP 200/204)

### `GET /billings/sp-filter`

- Operation `getBillingSupplyPointFilter` (CPRCOLBILLINGApi; `9229.de5cae61.js`)
- Response: JSON array of `SupplyPointsBillingFilterDto`:
  - `agreementIdIsu`
  - `supplyPointCommodity` (CodebookEntryDto)
  - `productInstanceTypeId`
  - `partnerIdCrm`
  - `consumptionPlaceName`
  - `consumptionPlaceIdIsu`
  - `supplyPointCode`
  - `parentAgreementIdIsu`
  - `contractIdIsu`
  - `supplyPointUniqueId`
  - `addressParts` (AddressPartsDto)
    - `addressStreet` (CodebookEntryDto)
    - `addressZipCode`
    - `addressCity` (CodebookEntryDto)
    - `addressLandRegistryNumber`
    - `addressHouseNumber`
  - `supplyPointType` (CodebookEntryDto)
  - `supplyPointIdIsu`
- Captured sample: probe_out: `billings_sp-filter_supplyPointId=<supplyPointUid>`

  Response shape (anonymized, values replaced by types):

```json
[
 {
  "agreementIdIsu": "string",
  "supplyPointCommodity": {
   "entrySystemSpecificId": "",
   "systemId": "",
   "entryId": "",
   "longValue": "string",
   "language": "",
   "validTo": "string",
   "validFrom": "string",
   "codebookId": "",
   "value": "P1"
  },
  "productInstanceTypeId": "",
  "partnerIdCrm": "string",
  "consumptionPlaceName": "string",
  "consumptionPlaceIdIsu": "string",
  "supplyPointCode": "string",
  "parentAgreementIdIsu": "string",
  "contractIdIsu": "string",
  "supplyPointUniqueId": "string",
  "addressParts": {
   "addressZipCode": "string",
   "addressLandRegistryNumber": "string",
   "addressHouseNumber": "string"
  },
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
  "supplyPointIdIsu": "string"
 }
]
```

### `POST /billings/state-benefits`

- Operation `getStateBenefits` (CPRCOLBILLINGApi; `9229.de5cae61.js`)
- Body (JSON `StateBenefitsRequestDto`):
  - `supplyPointCode`
  - `agreementIdIsu`
- Response: JSON array of `StateBenefitDto`:
  - `billingAdvanceAmountNew`
  - `billingReceivablesAndPayablesAccountDocumentNumber`
  - `billingStateBenefitAmount`
  - `billingAdvanceAmountOld`
  - `billingTransactionCurrency`
  - `billingStateBenefitDate` (date)
  - `billingAdvancePaymentPlanRowNumber`

### `GET /billings/user-columns`

- Operation `getUserColumns` (CPRCOLBILLINGApi; `9229.de5cae61.js`)
- Response: JSON object

### `POST /documents`

- Operation `getDocuments` (CPRCOLDOCUMENTApi; `2773.a5efa002.js`, `5154.e5d93fe4.js`, `5503.50b79690.js`)
- **Used by integration**: `api.py` get_invoice_pdf, get_price_lists
- Body (JSON `DocumentFilterDto`):
  - `documentType`
  - `documentDomain`
  - `documentParams` (array)
- Response: JSON array of object

### `POST /documents/attachment`

- Operation `prepareDocumentAttachmentByFilter` (CPRCOLDOCUMENTApi; `2773.a5efa002.js`, `5154.e5d93fe4.js`)
- **Used by integration**: `api.py` get_invoice_csv
- Query: `withRetry`, `force`
- Body (JSON `DocumentFilterDto`):
  - `documentType`
  - `documentDomain`
  - `documentParams` (array)
- Response: JSON object:
  - `attachmentKey`

### `POST /documents/attachment/zip`

- Operation `prepareMultipleDocumentAttachments` (CPRCOLDOCUMENTApi; `2773.a5efa002.js`, `5154.e5d93fe4.js`)
- Body (JSON `PrepareMultipleDocumentAttachmentsInDto`):
  - `fileType`
  - `documentFilters` (array)
- Response: JSON object:
  - `attachmentKey`
  - `missingDocuments` (array)

### `POST /documents/check`

- Operation `checkDocument` (CPRCOLDOCUMENTApi; `2773.a5efa002.js`, `5154.e5d93fe4.js`)
- Body (JSON `DocumentFilterDto`):
  - `documentType`
  - `documentDomain`
  - `documentParams` (array)
- Response: JSON object:
  - `showDocument`

### `POST /documents/preparation`

- Operation `documentPreparation` (CPRCOLDOCUMENTApi; `2773.a5efa002.js`, `5154.e5d93fe4.js`)
- Body (JSON `DocumentFilterDto`):
  - `documentType`
  - `documentDomain`
  - `documentParams` (array)
- Response: JSON object:
  - `preparation`

### `GET /documents/{attachmentKey}/attachment`

- Operation `getDocumentAttachment` (CPRCOLDOCUMENTApi; `2773.a5efa002.js`, `5154.e5d93fe4.js`)
- **Used by integration**: `api.py` get_invoice_csv, get_document_pdf
- Path params: `attachmentKey`
- Response: binary file (blob)

### `POST /documents/{documentGuidCol}/attachment`

- Operation `prepareSingleDocumentAttachment` (CPRCOLDOCUMENTApi; `2773.a5efa002.js`, `5154.e5d93fe4.js`)
- **Used by integration**: `api.py` get_document_pdf
- Path params: `documentGuidCol`
- Response: JSON object:
  - `attachmentKey`

### `GET /interactive-invoicing/distribution-rate-banner`

- Operation `getRecommendedDistributionRateBanner` (CPRCOLINTERACTIVEINVOICINGApi; `7148.7659886f.js`)
- **Used by integration**: `api.py` get_contract_info
- Query: `supplyPointUid`, `supplyPointExpectedAnnualConsumption`
- Response: JSON object:
  - `recommendedSupplyPointDistributionRate` (CodebookEntryDto)
  - `currentSupplyPointDistributionRate` (CodebookEntryDto)
- Captured sample: probe_out: `interactive-invoicing_distribution-rate-banner_supplyPointUid=<supplyPointUid>&supplyPointExpect`; snapshot: `/interactive-invoicing/distribution-rate-banner?supplyPointExpectedAnnualConsumption=1163&supplyPointUid=<supplyPointUid>`; snapshot: `/interactive-invoicing/distribution-rate-banner?supplyPointExpectedAnnualConsumption=4770&supplyPointUid=<supplyPointUid>`

  Response shape (anonymized, values replaced by types):

```json
{
 "recommendedSupplyPointDistributionRate": {
  "entrySystemSpecificId": "STD_D02D",
  "systemId": "INT",
  "entryId": "STD_D02D",
  "longValue": "string",
  "entryOrder": "number",
  "language": "CZ",
  "validTo": "date-time",
  "validFrom": "date-time",
  "codebookId": "TP_DISTR_RX",
  "value": "string",
  "otherValues": [
   {
    "key": "DistributionRateType",
    "value": "string"
   }
  ]
 },
 "currentSupplyPointDistributionRate": {
  "entrySystemSpecificId": "STD_D02D",
  "systemId": "INT",
  "entryId": "STD_D02D",
  "longValue": "string",
  "entryOrder": "number",
  "language": "CZ",
  "validTo": "date-time",
  "validFrom": "date-time",
  "codebookId": "TP_DISTR_RX",
  "value": "string",
  "otherValues": [
   {
    "key": "DistributionRateType",
    "value": "string"
   }
  ]
 }
}
```

### `GET /interactive-invoicing/invoice-detail`

- Operation `getInteractiveInvoiceDetall` (CPRCOLINTERACTIVEINVOICINGApi; `7148.7659886f.js`)
- Query: `agreementIdIsu`, `billingReceivablesAndPayablesAccountDocumentNumber`
- Response: JSON object:
  - `showDynamicPriceInfo`
  - `interactiveInvoiceHeader` (object)
  - `overpaymentInformation` (object)
  - `paymentPrescriptionInformation` (object)
  - `consumptionHistory` (object)
  - `advancePayments` (object)
  - `consumptionSummary` (object)
  - `billingOverview` (object)
  - `productInformation` (object)
  - `paidPaymentPrescriptionInfo` (object)
  - `invoiceRuleBalance` (CodebookEntryDto)
  - `originalDocumentNumber`
  - `epaText`
  - `dynamicTariffData` (object)
- Captured sample: probe_out: `interactive-invoicing_invoice-detail_agreementIdIsu=<id>&billingReceivablesAndPayablesAccountDocumentNumber=1220`; probe_out: `interactive-invoicing_invoice-detail_agreementIdIsu=<id>&billingReceivablesAndPayablesAccountDocumentNumber=1250`; snapshot: `/interactive-invoicing/invoice-detail?agreementIdIsu=<id>&billingReceivablesAndPayablesAccountDocumentNumber=<id>`

  Response shape (anonymized, values replaced by types):

```json
{
 "showDynamicPriceInfo": "boolean",
 "interactiveInvoiceHeader": {
  "invoiceDocumentType": {
   "entrySystemSpecificId": "E_FAKT_SPOTR_PERIOD",
   "systemId": "ODS",
   "entryId": "E_FAKT_SPOTR_PERIOD",
   "longValue": "string",
   "entryOrder": "number",
   "language": "CZ",
   "validTo": "date-time",
   "validFrom": "date-time",
   "codebookId": "TP_INVC_DOC",
   "value": "string"
  },
  "supplyPointAddress": {
   "printInvoiceSupplyPointAdressCity": "string",
   "printInvoiceSupplyPointAdressDisctrict": "string",
   "printInvoiceSupplyPointAdressHouseNumber": "string",
   "printInvoiceSupplyPointAdressStreet": "string",
   "printInvoiceSupplyPointAdressZipCode": "string"
  },
  "videoGuide": {
   "linkType": "YOUTUBE",
   "value": "string",
   "linkText": "string"
  },
  "contractIdIsu": "string",
  "printInvoiceSupplyPointName": "string",
  "printInvoiceSupplyPointCode": "string",
  "printInvoiceSupplyPointNumber": "string",
  "printInvoiceMeterReadingCommodity": "E1",
  "supplyPointUid": "string",
  "activeOM": "boolean",
  "hasCsvDocument": "boolean"
 },
 "overpaymentInformation": {
  "overpaymentItems": [
   {
    "overpaymentRefundDueDate": "date-time",
    "overpaymentRefundType": {
     "entrySystemSpecificId": "PREPL_VRAC_UCET",
     "systemId": "INT",
     "entryId": "PREPL_VRAC_UCET",
     "longValue": "string",
     "entryOrder": "number",
     "language": "CZ",
     "validTo": "date-time",
     "validFrom": "date-time",
     "codebookId": "TP_PMT_PRESCR_BAL",
     "value": "string",
     "otherValues": [
      {
       "…": "…"
      }
     ]
    }
   }
  ]
 },
 "consumptionHistory": {
  "labelText": "string",
  "ConsumptionHistoryItem": [
   {
    "printInvoiceConsumptionHistoryFrom": "YYYY-MM-DD",
    "printInvoiceConsumptionHistoryTo": "YYYY-MM-DD",
    "printInvoiceConsumptionHistoryAmountWithTax": "number",
    "printInvoiceConsumptionHistoryQuantityTotal": "number"
   }
  ]
  … (truncated)
```

### `GET /interactive-invoicing/show-advance-payments`

- Operation `showAdvancePayments` (CPRCOLINTERACTIVEINVOICINGApi; `7148.7659886f.js`)
- Query: `selectedInvoiceIdIsu`, `invoiceIdsIsu`
- Response: JSON object:
  - `isCurrentAdvancePayment`

### `GET /interactive-invoicing/show-interactive-invoice`

- Operation `showInteractiveInvoice` (CPRCOLINTERACTIVEINVOICINGApi; `7148.7659886f.js`)
- Query: `agreementIdIsu`, `billingReceivablesAndPayablesAccountDocumentNumber`
- Response: JSON object:
  - `showInteractiveInvoice`

### `GET /interactive-invoicing/show-savings-link`

- Operation `showSavingsLink` (CPRCOLINTERACTIVEINVOICINGApi; `7148.7659886f.js`)
- Response: JSON object:
  - `showLink`

### `GET /interactive-invoicing/upcoming-invoice-banner`

- Operation `showUpcomingInvoiceBanner` (CPRCOLINTERACTIVEINVOICINGApi; `7148.7659886f.js`)
- Query: `supplyPointUid`
- Response: JSON object:
  - `showUpcomingInvoiceBanner`
- Captured sample: probe_out: `interactive-invoicing_upcoming-invoice-banner_supplyPointUid=<supplyPointUid>`; probe_out: `interactive-invoicing_upcoming-invoice-banner`

  Response shape (anonymized, values replaced by types):

```json
{
 "showUpcomingInvoiceBanner": "boolean"
}
```

### `GET /payment-methods/GetActualBankAccounts`

- Operation `getBanks` (CPRCOLPAYMENTMETHODApi; `1503.08073e29.js`)
- Query: `agreementIdIsu`, `supplyPointId`
- Response: JSON array of object:
  - `bankAccountPrefix`
  - `bankAccountNumber`
  - `bankAccountId`
  - `bankAccountBankCode` (CodebookEntryDto)
  - `hidden`
  - `isForeignAccount`
- Captured sample: probe_out: `payment-methods_GetActualBankAccounts_supplyPointId=<supplyPointUid>&agreementIdIsu=<id>`

  Response shape (anonymized, values replaced by types):

```json
[
 {
  "bankAccountNumber": "number",
  "bankAccountId": "string",
  "bankAccountBankCode": {
   "value": "string"
  },
  "isForeignAccount": "boolean",
  "bankAccountPrefix": "number"
 }
]
```

### `GET /payment-methods/bank-accounts`

- Operation `getBankAccounts` (CPRCOLPAYMENTMETHODApi; `1503.08073e29.js`)
- Response: JSON array of object:
  - `bankAccountPrefix`
  - `bankAccountNumber`
  - `bankAccountId`
  - `bankAccountBankCode` (CodebookEntryDto)
  - `hidden`
  - `isForeignAccount`

### `PUT /payment-methods/bank-accounts`

- Operation `updateBankAccounts` (CPRCOLPAYMENTMETHODApi; `1503.08073e29.js`)
- Body (JSON array of `BankAccountUpdateDto`):
  - `oldBankAccount` (object)
  - `newBankAccount` (object)
- Response: empty (HTTP 200/204)

### `POST /payment-methods/bank-accounts/hide`

- Operation `hideBankAccount` (CPRCOLPAYMENTMETHODApi; `1503.08073e29.js`)
- Body (JSON `HideBankAccountRequestBodyDto`):
  - `bankAccountId`
- Response: empty (HTTP 200/204)

### `POST /payment-methods/change-advance-possible`

- Operation `canChangeAdvancePayment` (CPRCOLPAYMENTMETHODApi; `1503.08073e29.js`)
- Body (JSON `CheckAdvancePaymentChangeAvailableRequestDto`):
  - `consumptionPlaceIdIsu`
  - `agreementIdIsu`
- Response: JSON array of object:
  - `consumptionPlaceIdIsuAgreementIdIsu`
  - `consumptionPlaceIdIsu`
  - `agreementIdIsu`
  - `canChangeAdvancePayments`
  - `advancePaymentChangeNotPossibleReason` (CodebookEntryDto)
  - `supplyPointIdIsu`

### `POST /payment-methods/get`

- Operation `getPaymentMethods` (CPRCOLPAYMENTMETHODApi; `1503.08073e29.js`)
- Body (JSON `PaymentLoadRequestDto`):
  - `items` (array)
- Response: JSON array of object:
  - `easyDirectDebit` (object)
  - `allowedAdvancePaymentMethod` (array)
  - `PaymentMethodAllowedCombination` (array)
  - `allowedAdditionalPaymentMethod` (array)
  - `actualAdvancePaymentMethod`
  - `actualAdditionalPaymentMethod`
  - `actualOverpaymentMethod`
  - `allowedOverpaymentMethod` (array)
  - `bankAccounts` (array)

### `POST /payment-methods/set`

- Operation `setPaymentMethods` (CPRCOLPAYMENTMETHODApi; `1503.08073e29.js`)
- Body (JSON `PaymentChangeRequestDto`):
  - `useOverPaymentAsAdvance`
  - `advancePayment` (object)
  - `overPayment` (object)
  - `items` (array)
  - `additionalPayment` (object)
- Response: JSON object:
  - `activityId`
  - `PaymentChangeResponse` (array)

### `GET /payment-methods/{supplyPointId}/GetActualPaymentMethod`

- Operation `getPaymentMethod` (CPRCOLPAYMENTMETHODApi; `1503.08073e29.js`)
- Path params: `supplyPointId`
- Response: JSON object:
  - `easyDirectDebit` (object)
  - `allowedAdvancePaymentMethod` (array)
  - `PaymentMethodAllowedCombination` (array)
  - `allowedAdditionalPaymentMethod` (array)
  - `actualAdvancePaymentMethod`
  - `actualAdditionalPaymentMethod`
  - `actualOverpaymentMethod`
  - `allowedOverpaymentMethod` (array)
  - `bankAccounts` (array)

### `POST /self-service/payment-gateway`

- Operation `fetchPayuUrl` (CPRCOLPAYUApi; `834.d1c5a47e.js`, `8453.2579ce3b.js`)
- Body (JSON `FetchPayuURLRequestBodyDto`):
  - `email`
  - `variableSymbol`
  - `amount`
  - `individualFirstName`
  - `individualSurname`
- Response: JSON object:
  - `payuUrl`

