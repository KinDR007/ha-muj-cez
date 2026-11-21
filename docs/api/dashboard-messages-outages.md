# Dashboard, messages, outages, common

Dashboard tiles, message box, planned outages (distribution) and portal outages, CMS texts, navigation.

Generated from the portal bundle (`tools/probe/index.js`, `tools/probe/chunks/*.js`, release col-fe@3.66.0). Field names are the JSON wire names; `(XxxDto)` marks a nested object, `CodebookEntryDto` is described in [README](README.md#codebook-entries). Types not shown are plain strings/numbers/booleans.

| Method | Path | Operation | Integration | Sample |
|---|---|---|---|---|
| POST | [`/common/action-audit`](#post-commonaction-audit) | auditAction |  |  |
| POST | [`/common/create-lead`](#post-commoncreate-lead) | createLead |  |  |
| GET | [`/common/customer-outages`](#get-commoncustomer-outages) | readAppOutagesAsCustomer |  | yes |
| GET | [`/common/downtime-display`](#get-commondowntime-display) | getDowntimeDisplay |  |  |
| GET | [`/common/image/cms`](#get-commonimagecms) | getCmsImage |  |  |
| POST | [`/common/onboarding-actions`](#post-commononboarding-actions) | getOnboardingActions |  |  |
| GET | [`/common/onboarding-cust`](#get-commononboarding-cust) | getOnboardingCust |  |  |
| GET | [`/common/onboarding-customization`](#get-commononboarding-customization) | getOnboardingCustomization |  |  |
| POST | [`/common/outage/decide-notification`](#post-commonoutagedecide-notification) | decideOutagePopup |  |  |
| POST | [`/common/outage/filter-active-outages`](#post-commonoutagefilter-active-outages) | getActiveOutagesByFilter |  |  |
| POST | [`/common/outage/filter-by-date`](#post-commonoutagefilter-by-date) | getOutagesByDateRange |  |  |
| POST | [`/common/outage/get-contacts`](#post-commonoutageget-contacts) | getOutageContactSettings |  |  |
| PUT | [`/common/outage/save-outage`](#put-commonoutagesave-outage) | saveOutageToDb |  |  |
| POST | [`/common/outage/set-contacts`](#post-commonoutageset-contacts) | setOutageContactSettings |  |  |
| GET | [`/common/performance-rfc`](#get-commonperformance-rfc) | callPerformanceRFC |  |  |
| POST | [`/common/set-onboarding-actions`](#post-commonset-onboarding-actions) | setOnboardingAction |  |  |
| GET | [`/common/text/cms`](#get-commontextcms) | getCmsText |  |  |
| GET | [`/common/text/sap/{textId}`](#get-commontextsaptextid) | getSapText |  |  |
| DELETE | [`/common/user-views`](#delete-commonuser-views) | deleteUserViews |  |  |
| GET | [`/common/user-views`](#get-commonuser-views) | getUserViews |  |  |
| POST | [`/common/user-views`](#post-commonuser-views) | updateUserViews |  |  |
| PUT | [`/common/user-views`](#put-commonuser-views) | createUserViews |  |  |
| GET | [`/dashboard/articles`](#get-dashboardarticles) | getArticles |  |  |
| POST | [`/dashboard/banner-data`](#post-dashboardbanner-data) | sendBannerData |  |  |
| GET | [`/dashboard/billings`](#get-dashboardbillings) | getBillings |  | yes |
| GET | [`/dashboard/customer-centers`](#get-dashboardcustomer-centers) | getCustomerCenters |  |  |
| PUT | [`/dashboard/messages/close`](#put-dashboardmessagesclose) | closeMessages |  |  |
| GET | [`/dashboard/messages/summary`](#get-dashboardmessagessummary) | getMessagesSummary | fetch_all | yes |
| GET | [`/dashboard/my-cases`](#get-dashboardmy-cases) | getCases |  |  |
| GET | [`/dashboard/operations`](#get-dashboardoperations) | getOperations |  | yes |
| GET | [`/dashboard/supply-point-outages`](#get-dashboardsupply-point-outages) | getActiveOutages | fetch_all | yes |
| GET | [`/messages`](#get-messages) | getMessages |  |  |
| GET | [`/messages/bill-shock`](#get-messagesbill-shock) | checkBillShock |  | yes |
| POST | [`/messages/deletes`](#post-messagesdeletes) | deleteMessages |  |  |
| GET | [`/messages/page-size`](#get-messagespage-size) | getPageSize |  |  |
| PATCH | [`/messages/returned-correspondence/{barcode}`](#patch-messagesreturned-correspondencebarcode) | updateReturnedCorrespondence |  |  |
| GET | [`/messages/{eventGuidIsu}`](#get-messageseventguidisu) | getMessageById |  |  |
| PATCH | [`/messages/{eventGuidIsu}`](#patch-messageseventguidisu) | updateMessage |  |  |
| GET | [`/navigation`](#get-navigation) | getNavigation |  |  |
| GET | [`/navigation-new`](#get-navigation-new) | getNavigationNew |  |  |
| GET | [`/navigation/cases`](#get-navigationcases) | getCasesNavigation |  |  |
| GET | [`/outage`](#get-outage) | getWebOutageActive |  | yes |
| POST | [`/public-common/action-audit`](#post-public-commonaction-audit) | auditAction |  |  |
| GET | [`/public-common/app-outages`](#get-public-commonapp-outages) | publicReadAppOutages |  |  |
| GET | [`/public-common/app/config`](#get-public-commonappconfig) | getAppConfig |  |  |
| POST | [`/set-clc`](#post-set-clc) | setClc |  |  |
| GET | [`/web-outage/check-F5`](#get-web-outagecheck-f5) | webOutageCheckF5 |  |  |
| POST | [`/web-outage/create`](#post-web-outagecreate) | createWebOutageRecord |  |  |
| DELETE | [`/web-outage/delete/{webOutageId}`](#delete-web-outagedeleteweboutageid) | deleteWebOutageRecord |  |  |
| GET | [`/web-outage/downtime-display`](#get-web-outagedowntime-display) | getDowntimeDisplay |  |  |
| GET | [`/web-outage/read`](#get-web-outageread) | readWebOutages |  |  |
| POST | [`/web-outage/update`](#post-web-outageupdate) | updateWebOutage |  |  |

### `POST /common/action-audit`

- Operation `auditAction` (CPRCOLCOMMONApi; `5269.4f44f6a3.js`)
- Body (JSON `AppActionInDto`):
  - `appId`
  - `subActionCode`
  - `valueId`
  - `actionCode`
  - `note`
- Response: JSON object:
  - `simulatedPartnerIdCol`
  - `partnerIdCrm`
  - `roles`
  - `subActionCode`
  - `actionCode`
  - `note`
  - `appId`
  - `valueId`
  - `partnerIdCol`

### `POST /common/create-lead`

- Operation `createLead` (CPRCOLCOMMONApi; `5269.4f44f6a3.js`)
- Body (JSON `LeadRequestDto`):
  - `description`
  - `leadId`
  - `actType`
  - `phoneNumber`
  - `phonenumber2`
  - `email`
  - `note`
  - `receivingChanel`
  - `commodity`
  - `leadType`
  - `campaignId`
  - `types` (array)
  - `resolverKpjm`
  - `ivPlanCall`
- Response: JSON object:
  - `leadGuid`
  - `leadObjectId`

### `GET /common/customer-outages`

- Operation `readAppOutagesAsCustomer` (CPRCOLCOMMONApi; `5269.4f44f6a3.js`)
- Response: JSON array of object
- Captured sample: probe_out: `common_customer-outages`
  (captured response: error `GENERIC` (ERROR))

### `GET /common/downtime-display`

- Operation `getDowntimeDisplay` (CPRCOLCOMMONApi; `5269.4f44f6a3.js`)
- Response: JSON array of object

### `GET /common/image/cms`

- Operation `getCmsImage` (CPRCOLCOMMONApi; `5269.4f44f6a3.js`)
- Query: `id`
- Response: binary file (blob)

### `POST /common/onboarding-actions`

- Operation `getOnboardingActions` (CPRCOLCOMMONApi; `5269.4f44f6a3.js`)
- Body (JSON `OnboardingGetActionsDto`):
  - `dateTo`
  - `dateFrom`
  - `stepNumber`
  - `action`
  - `appId`
- Response: JSON object:
  - `customerActionsData` (array)

### `GET /common/onboarding-cust`

- Operation `getOnboardingCust` (CPRCOLCOMMONApi; `5269.4f44f6a3.js`)
- Query: `application`
- Response: JSON object:
  - `appList` (array)
  - `displaySettings` (array)
  - `appSteps` (array)
  - `segmentSettings` (array)
  - `availableOnboardings` (array)

### `GET /common/onboarding-customization`

- Operation `getOnboardingCustomization` (CPRCOLCOMMONApi; `5269.4f44f6a3.js`)
- Query: `application`
- Response: JSON object:
  - `appList` (array)
  - `displaySettings` (array)
  - `appSteps` (array)
  - `segmentSettings` (array)
  - `availableOnboardings` (array)

### `POST /common/outage/decide-notification`

- Operation `decideOutagePopup` (CPRCOLCOMMONApi; `5269.4f44f6a3.js`)
- Body (JSON `DecideOutageNotificationSupplyPointCodesDto`):
  - `supplyPointCode`
- Response: text

### `POST /common/outage/filter-active-outages`

- Operation `getActiveOutagesByFilter` (CPRCOLCOMMONApi; `5269.4f44f6a3.js`)
- Body (JSON `OutagesFilterDto`):
  - `supplyPointCode`
- Response: JSON array of object

### `POST /common/outage/filter-by-date`

- Operation `getOutagesByDateRange` (CPRCOLCOMMONApi; `5269.4f44f6a3.js`)
- Query: `from`, `to`
- Response: JSON array of object

### `POST /common/outage/get-contacts`

- Operation `getOutageContactSettings` (CPRCOLCOMMONApi; `5269.4f44f6a3.js`)
- Body (JSON `OutageContactSettingsRequestBodyDto`):
  - `eanList`
- Response: JSON array of object

### `PUT /common/outage/save-outage`

- Operation `saveOutageToDb` (CPRCOLCOMMONApi; `5269.4f44f6a3.js`)
- Body (JSON array of `ActiveOutageDto`):
  - `addressCity` (CodebookEntryIdentifierDto)
  - `deviceReliefReason`
  - `addressCountry` (CodebookEntryIdentifierDto)
  - `addressDistrict` (CodebookEntryIdentifierDto)
  - `cancellationDate` (date)
  - `viewDate` (date)
  - `deviceLocation`
  - `activeSupplyPointIdIsu`
  - `addressParcelNumber`
  - `deviceReliefReasonText`
  - `supplyPointIdIsu`
  - `supplyPointCode`
  - `recordCreationDate` (date)
  - `recordCreationTime` (date)
  - `connectableObject`
  - `addressHouseNumber`
  - `addressLandRegistryNumber`
  - `legalEntityName`
  - `manipulationStep`
  - `partnerIdCrm`
  - `manipulationEndTime` (date)
  - `manipulationStartDate` (date)
  - `addressCadastralTerritory`
  - `addressRegion` (CodebookEntryIdentifierDto)
  - `addressZipCode`
  - `recordNumber`
  - `addressStreet` (CodebookEntryIdentifierDto)
  - `manipulationStartTime` (date)
  - `cancelled`
  - `deviceSerialNumber`
  - `addressPrecinct`
  - `contactLocality`
  - `dispatchingArea`
- Response: empty (HTTP 200/204)

### `POST /common/outage/set-contacts`

- Operation `setOutageContactSettings` (CPRCOLCOMMONApi; `5269.4f44f6a3.js`)
- Body (JSON array of `OutageContactSettingsDto`):
  - `contactValue`
  - `supplyPointCode`
  - `notifyDuringRegularWorkTime`
  - `contactType` (CodebookEntryDto)
- Response: text

### `GET /common/performance-rfc`

- Operation `callPerformanceRFC` (CPRCOLCOMMONApi; `5269.4f44f6a3.js`)
- Query: `type`, `parameter`
- Response: empty (HTTP 200/204)

### `POST /common/set-onboarding-actions`

- Operation `setOnboardingAction` (CPRCOLCOMMONApi; `5269.4f44f6a3.js`)
- Body (JSON `OnboardingSetActionDto`):
  - `stepNumber`
  - `appId`
  - `action`
- Response: empty (HTTP 200/204)

### `GET /common/text/cms`

- Operation `getCmsText` (CPRCOLCOMMONApi; `5269.4f44f6a3.js`)
- Query: `id`
- Response: JSON object:
  - `text`

### `GET /common/text/sap/{textId}`

- Operation `getSapText` (CPRCOLCOMMONApi; `5269.4f44f6a3.js`)
- Path params: `textId`
- Response: JSON object:
  - `text`

### `DELETE /common/user-views`

- Operation `deleteUserViews` (CPRCOLCOMMONApi; `5269.4f44f6a3.js`)
- Query: `id`
- Response: empty (HTTP 200/204)

### `GET /common/user-views`

- Operation `getUserViews` (CPRCOLCOMMONApi; `5269.4f44f6a3.js`)
- Response: JSON array of object

### `POST /common/user-views`

- Operation `updateUserViews` (CPRCOLCOMMONApi; `5269.4f44f6a3.js`)
- Body (JSON `UserFilterContainerDto`):
  - `id`
  - `listFilters` (array)
  - `periodFilters` (array)
  - `type`
  - `name`
  - `description`
- Response: JSON object

### `PUT /common/user-views`

- Operation `createUserViews` (CPRCOLCOMMONApi; `5269.4f44f6a3.js`)
- Body (JSON `UserFilterContainerDto`):
  - `id`
  - `listFilters` (array)
  - `periodFilters` (array)
  - `type`
  - `name`
  - `description`
- Response: JSON object

### `GET /dashboard/articles`

- Operation `getArticles` (CPRCOLDASHBOARDApi; `2100.03a79f61.js`)
- Query: `limit`
- Response: JSON `AcademyArticlesResponseDto`:
  - `articles` (AcademyArticleDto[])
    - `title`
    - `createdAt` (date)
    - `summary`
    - `imageUrl`
    - `articleUrl`
    - `videoUrl`

### `POST /dashboard/banner-data`

- Operation `sendBannerData` (CPRCOLDASHBOARDApi; `2100.03a79f61.js`)
- Body (JSON `SendBannerDataRequestDto`):
  - `viewUniqueId`
  - `banners` (BannerDataDto[])
    - `bannerCommand`
    - `bannerUniqueId`
    - `subws`
    - `ws`
  - `sessionId`
- Response: empty (HTTP 200/204)

### `GET /dashboard/billings`

- Operation `getBillings` (CPRCOLDASHBOARDApi; `2100.03a79f61.js`)
- Response: JSON `BillingsResponseDto`:
  - `paymentWarning` (PaymentWarningDto)
    - `currency`
    - `isPaid`
    - `actions` (PaymentWarningActionsDto)
    - `status` (DashboardTileStatusDto)
    - `amount`
    - `acquisitionDate` (date)
    - `billings` (BillingModelDto[])
    - `maturityDate` (date)
- Captured sample: probe_out: `dashboard_billings_limit=5`
  (captured response: empty `{}`)

### `GET /dashboard/customer-centers`

- Operation `getCustomerCenters` (CPRCOLDASHBOARDApi; `2100.03a79f61.js`)
- Query: `latitude`, `longitude`, `limit`
- Response: JSON `CustomerCentersResponseDto`:
  - `nearestCenters` (CustomerCenterDto[])
    - `longitude`
    - `name`
    - `addressCity`
    - `id`
    - `openingTimes` (OpeningTimesDto[])
    - `addressLine1`
    - `addressZip`
    - `latitude`
    - `category`
  - `bookedAppointments`
  - `canBookAppointment`

### `PUT /dashboard/messages/close`

- Operation `closeMessages` (CPRCOLDASHBOARDApi; `2100.03a79f61.js`)
- Body (JSON `CloseMessagesRequestDto`):
  - `guids`
  - `all`
- Response: empty (HTTP 200/204)

### `GET /dashboard/messages/summary`

- Operation `getMessagesSummary` (CPRCOLDASHBOARDApi; `2100.03a79f61.js`)
- **Used by integration**: `api.py` fetch_all
- Response: JSON `MessagesSummaryResponseDto`:
  - `unreadTotal`
  - `unreadUnclosedTotal`
  - `messages` (MessageMinimalDto[])
    - `messageClosed`
    - `eventGuidIsu`
- Captured sample: probe_out: `dashboard_messages_summary`; snapshot: `/dashboard/messages/summary`

  Response shape (anonymized, values replaced by types):

```json
{
 "unreadTotal": "number",
 "unreadUnclosedTotal": "number",
 "messages": [
  {
   "messageClosed": "boolean",
   "eventGuidIsu": "string"
  }
 ]
}
```

### `GET /dashboard/my-cases`

- Operation `getCases` (CPRCOLDASHBOARDApi; `2100.03a79f61.js`)
- Query: `only`, `page`, `limit`
- Response: JSON `CasesResponseDto`:
  - `pagination` (PaginationDto)
    - `pageSize`
    - `totalPages`
    - `currentPage`
    - `totalItems`
  - `cases` (CaseMinimalDto[])
    - `caseSubtitle`
    - `caseEntityTypes`
    - `caseTitle`
    - `caseUrl`
    - `caseStatus` (CaseMinimalStatusDto)
    - `caseCategory` (CodebookEntryDto)
    - `caseCreationDate` (date)
    - `caseId`

### `GET /dashboard/operations`

- Operation `getOperations` (CPRCOLDASHBOARDApi; `2100.03a79f61.js`)
- Response: JSON `OperationsResponseDto`:
  - `marketplace` (MenuItemNodeDto)
    - `nodeId`
    - `quickLink`
    - `directory`
    - `type`
    - `description`
    - `name`
    - `shortName`
    - `dynamicNavigation`
    - `children` (array)
    - `nodesMenuItem`
    - `quickLinkNew`
    - `icon`
    - `fullLink`
    - `activeProduct` (ActiveProductDto[])
    - `maxBonus`
  - `acquisitionLinks` (MenuItemNodeDto)
    - `nodeId`
    - `quickLink`
    - `directory`
    - `type`
    - `description`
    - `name`
    - `shortName`
    - `dynamicNavigation`
    - `children` (array)
    - `nodesMenuItem`
    - `quickLinkNew`
    - `icon`
    - `fullLink`
    - `activeProduct` (ActiveProductDto[])
    - `maxBonus`
  - `operations` (MenuItemNodeDto)
    - `nodeId`
    - `quickLink`
    - `directory`
    - `type`
    - `description`
    - `name`
    - `shortName`
    - `dynamicNavigation`
    - `children` (array)
    - `nodesMenuItem`
    - `quickLinkNew`
    - `icon`
    - `fullLink`
    - `activeProduct` (ActiveProductDto[])
    - `maxBonus`
- Captured sample: probe_out: `dashboard_operations_limit=5`

  Response shape (anonymized, values replaced by types):

```json
{
 "marketplace": {
  "nodeId": "string",
  "quickLink": "string",
  "directory": "string",
  "type": "string",
  "description": "string",
  "name": "string",
  "shortName": "string",
  "dynamicNavigation": "string",
  "children": [
   {
    "nodeId": "string",
    "quickLink": "string",
    "directory": "string",
    "type": "string",
    "description": "string",
    "name": "string",
    "shortName": "string",
    "dynamicNavigation": "string",
    "children": [
     {
      "nodeId": "string",
      "quickLink": "string",
      "directory": "string",
      "type": "string",
      "description": "string",
      "name": "string",
      "shortName": "string",
      "dynamicNavigation": "string",
      "children": [],
      "nodesMenuItem": "string",
      "quickLinkNew": "string",
      "icon": "string",
      "fullLink": "string",
      "activeProduct": []
     }
    ],
    "nodesMenuItem": "string",
    "quickLinkNew": "string",
    "icon": "string",
    "fullLink": "string",
    "activeProduct": []
   }
  ],
  "nodesMenuItem": "string",
  "quickLinkNew": "string",
  "icon": "string",
  "fullLink": "string",
  "activeProduct": []
 },
 "acquisitionLinks": {
  "nodeId": "string",
  "quickLink": "string",
  "directory": "string",
  "type": "string",
  "description": "string",
  "name": "string",
  "shortName": "string",
  "dynamicNavigation": "string",
  "children": [
   {
    "nodeId": "string",
    "quickLink": "string",
    "directory": "string",
    "type": "string",
    "description": "string",
    "name": "string",
    "shortName": "string",
    "dynamicNavigation": "string",
  … (truncated)
```

### `GET /dashboard/supply-point-outages`

- Operation `getActiveOutages` (CPRCOLDASHBOARDApi; `2100.03a79f61.js`)
- **Used by integration**: `api.py` fetch_all
- Response: JSON `ActiveOutagesResponseDto`:
  - `outages` (ActiveOutageDto[])
    - `partnerIdCrm`
    - `phoneNumber`
    - `consumptionPlaceName`
    - `contractIdCrm`
    - `supplyPointUniqueId`
    - `isZame`
    - `agreementIdIsu`
    - `consumptionPlaceIdIsu`
    - `address` (AddressPartsDto)
- Captured sample: probe_out: `dashboard_supply-point-outages`; snapshot: `/dashboard/supply-point-outages`

  Response shape (anonymized, values replaced by types):

```json
{
 "outages": []
}
```

### `GET /messages`

- Operation `getMessages` (CPRCOLMESSAGEApi; `1893.527cb106.js`, `4274.e12947cc.js`)
- Response: JSON array of object

### `GET /messages/bill-shock`

- Operation `checkBillShock` (CPRCOLMESSAGEApi; `1893.527cb106.js`, `4274.e12947cc.js`)
- Response: JSON object:
  - `limit`
  - `unreadTotal`
  - `messages` (array)
- Captured sample: probe_out: `messages_bill-shock`

  Response shape (anonymized, values replaced by types):

```json
{
 "limit": "number",
 "unreadTotal": "number",
 "messages": [
  {
   "eventCode": {
    "entryId": "MSG_SEGM_PER"
   },
   "eventCommunicationContent": "string",
   "messagesType": "P",
   "messagesSourceSystem": "string",
   "eventCreateDate": "date-time",
   "eventGuidIsu": "string",
   "webButtonUrl": "string",
   "webButtonText": "string",
   "eventCommunicationTitle": "string",
   "eventCommunicationImportanceId": "string",
   "eventCommunicationStatusDetailId": "string",
   "taskGuidCrm": "string",
   "eventCommunicationValidFrom": "date-time",
   "consumptionPlaceIdIsu": "string",
   "messagesBodyAsTitle": "string",
   "noteGuidCrm": "string",
   "eventCommunicationValidTo": "date-time",
   "messagesFlagClosed": "boolean",
   "messagesCritical": "string",
   "mobileButtonText": "string",
   "mobileButtonUrl": "string"
  }
 ]
}
```

### `POST /messages/deletes`

- Operation `deleteMessages` (CPRCOLMESSAGEApi; `1893.527cb106.js`, `4274.e12947cc.js`)
- Body (JSON `MessageIdListDto`):
  - `messageIds`
- Response: empty (HTTP 200/204)

### `GET /messages/page-size`

- Operation `getPageSize` (CPRCOLMESSAGEApi; `1893.527cb106.js`, `4274.e12947cc.js`)
- Response: JSON object:
  - `pageSize`

### `PATCH /messages/returned-correspondence/{barcode}`

- Operation `updateReturnedCorrespondence` (CPRCOLMESSAGEApi; `1893.527cb106.js`, `4274.e12947cc.js`)
- Path params: `barcode`
- Body (JSON `UpdateReturnedCorrespondenceInDto`):
  - `addressChanged`
  - `closed`
- Response: empty (HTTP 200/204)

### `GET /messages/{eventGuidIsu}`

- Operation `getMessageById` (CPRCOLMESSAGEApi; `1893.527cb106.js`, `4274.e12947cc.js`)
- Path params: `eventGuidIsu`
- Response: JSON object

### `PATCH /messages/{eventGuidIsu}`

- Operation `updateMessage` (CPRCOLMESSAGEApi; `1893.527cb106.js`, `4274.e12947cc.js`)
- Path params: `eventGuidIsu`
- Body (JSON `UpdateMessageInputDto`):
  - `messagesFlagClosed`
  - `eventCommunicationStatusDetailId`
- Response: empty (HTTP 200/204)

### `GET /navigation`

- Operation `getNavigation` (CPRCOLNAVIGATIONApi; `2172.4367e47e.js`, `9791.b61c67af.js`)
- Response: JSON object

### `GET /navigation-new`

- Operation `getNavigationNew` (CPRCOLNAVIGATIONApi; `2172.4367e47e.js`, `9791.b61c67af.js`)
- Query: `linkType`, `navMode`
- Response: JSON object

### `GET /navigation/cases`

- Operation `getCasesNavigation` (CPRCOLNAVIGATIONApi; `2172.4367e47e.js`, `9791.b61c67af.js`)
- Response: JSON object

### `GET /outage`

- Operation `getWebOutageActive` (CPRCOLCOMMONApi; `5269.4f44f6a3.js`)
- Response: JSON object:
  - `outage`
- Captured sample: probe_out: `outage`

  Response shape (anonymized, values replaced by types):

```json
{
 "outage": "boolean"
}
```

### `POST /public-common/action-audit`

- Operation `auditAction` (CPRCOLCOMMONPUBLICApi; `4487.a2ca4261.js`, `6868.df02448f.js`)
- Body (JSON `AppActionInDto`):
  - `appId`
  - `subActionCode`
  - `valueId`
  - `actionCode`
  - `note`
- Response: JSON object:
  - `simulatedPartnerIdCol`
  - `partnerIdCrm`
  - `roles`
  - `subActionCode`
  - `actionCode`
  - `note`
  - `appId`
  - `valueId`
  - `partnerIdCol`

### `GET /public-common/app-outages`

- Operation `publicReadAppOutages` (CPRCOLCOMMONPUBLICApi; `4487.a2ca4261.js`, `6868.df02448f.js`)
- Response: JSON array of object

### `GET /public-common/app/config`

- Operation `getAppConfig` (CPRCOLCOMMONPUBLICApi; `4487.a2ca4261.js`, `6868.df02448f.js`)
- Query: `version`, `platform`
- Response: JSON object:
  - `config` (object)

### `POST /set-clc`

- Operation `setClc` (CPRCOLCOMMONApi; `5269.4f44f6a3.js`)
- Body (JSON `ClcRequestBodyDto`):
  - `clc`
- Response: JSON object:
  - `colOnlinePlatformLoginCookie`

### `GET /web-outage/check-F5`

- Operation `webOutageCheckF5` (CPRCOLWEBOUTAGEApi; `1183.a4863c65.js`, `3564.4306132d.js`)
- Response: text

### `POST /web-outage/create`

- Operation `createWebOutageRecord` (CPRCOLWEBOUTAGEApi; `1183.a4863c65.js`, `3564.4306132d.js`)
- Body (JSON `WebOutageInternalDto`):
  - `webOutageId`
  - `internalNote`
  - `name`
  - `displayFrom` (date)
  - `text`
  - `displayTo` (date)
  - `type`
  - `textDashboard`
  - `downTimeFrom` (date)
  - `downTimeTo` (date)
  - `status`
  - `updatedBy`
  - `createdBy`
  - `regex`
  - `setOn`
  - `downTimePNText`
  - `downTimeSendPNTime` (date)
  - `sendingPNText`
  - `sentPN`
- Response: empty (HTTP 200/204)

### `DELETE /web-outage/delete/{webOutageId}`

- Operation `deleteWebOutageRecord` (CPRCOLWEBOUTAGEApi; `1183.a4863c65.js`, `3564.4306132d.js`)
- Path params: `webOutageId`
- Response: empty (HTTP 200/204)

### `GET /web-outage/downtime-display`

- Operation `getDowntimeDisplay` (CPRCOLWEBOUTAGEApi; `1183.a4863c65.js`, `3564.4306132d.js`)
- Response: JSON array of object

### `GET /web-outage/read`

- Operation `readWebOutages` (CPRCOLWEBOUTAGEApi; `1183.a4863c65.js`, `3564.4306132d.js`)
- Query: `webOutageId`
- Response: JSON array of object

### `POST /web-outage/update`

- Operation `updateWebOutage` (CPRCOLWEBOUTAGEApi; `1183.a4863c65.js`, `3564.4306132d.js`)
- Body (JSON `WebOutageInternalDto`):
  - `webOutageId`
  - `internalNote`
  - `name`
  - `displayFrom` (date)
  - `text`
  - `displayTo` (date)
  - `type`
  - `textDashboard`
  - `downTimeFrom` (date)
  - `downTimeTo` (date)
  - `status`
  - `updatedBy`
  - `createdBy`
  - `regex`
  - `setOn`
  - `downTimePNText`
  - `downTimeSendPNTime` (date)
  - `sendingPNText`
  - `sentPN`
- Response: empty (HTTP 200/204)

