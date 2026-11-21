# User, partners (accounts), agreements, registration

Logged-in user, business partners (customer accounts selectable via `X-COL-PARTNER`), contacts, agreements (e-invoice, mailing address), registration and MFA.

The integration reads the account list from `GET /user/token-data` (`parse_accounts` in `api.py`).

Generated from the portal bundle (`tools/probe/index.js`, `tools/probe/chunks/*.js`, release col-fe@3.66.0). Field names are the JSON wire names; `(XxxDto)` marks a nested object, `CodebookEntryDto` is described in [README](README.md#codebook-entries). Types not shown are plain strings/numbers/booleans.

| Method | Path | Operation | Integration | Sample |
|---|---|---|---|---|
| PUT | [`/actions/accept/{caseGuidCrm}`](#put-actionsacceptcaseguidcrm) | accept |  |  |
| GET | [`/actions/check-guid/{caseGuidCrm}`](#get-actionscheck-guidcaseguidcrm) | checkGuid |  |  |
| PUT | [`/actions/refuse/{caseGuidCrm}`](#put-actionsrefusecaseguidcrm) | refuse |  |  |
| POST | [`/addresses/do-address-check`](#post-addressesdo-address-check) | doAddressCheck |  |  |
| GET | [`/addresses/jdz`](#get-addressesjdz) | getAddresses |  |  |
| GET | [`/addresses/sap`](#get-addressessap) | readAddressesSap |  |  |
| GET | [`/agreement/address`](#get-agreementaddress) | getMailingAddress |  |  |
| POST | [`/agreement/address`](#post-agreementaddress) | setMailingAddress |  |  |
| GET | [`/agreement/contacts`](#get-agreementcontacts) | getElInvoicingMailsAndAddresses |  |  |
| GET | [`/agreement/elfa`](#get-agreementelfa) | getElInvoicing |  |  |
| POST | [`/agreement/elfa`](#post-agreementelfa) | setElInvoicing |  |  |
| GET | [`/email-actions/check-guid/{caseGuidCrm}`](#get-email-actionscheck-guidcaseguidcrm) | check |  |  |
| PUT | [`/email-actions/confirm/{caseGuidCrm}`](#put-email-actionsconfirmcaseguidcrm) | confirm |  |  |
| POST | [`/favorite/create/{favoriteKey}`](#post-favoritecreatefavoritekey) | create |  |  |
| GET | [`/favorite/delete/{favoriteKey}`](#get-favoritedeletefavoritekey) | _delete |  |  |
| GET | [`/favorite/keys`](#get-favoritekeys) | getKeys |  |  |
| GET | [`/favorite/read/{favoriteKey}`](#get-favoritereadfavoritekey) | read |  |  |
| POST | [`/favorite/update/{favoriteKey}`](#post-favoriteupdatefavoritekey) | update |  |  |
| PUT | [`/partners`](#put-partners) | updatePartnerData |  |  |
| GET | [`/partners/acconts-with-access`](#get-partnersacconts-with-access) | accountWithAccess |  |  |
| POST | [`/partners/agreements`](#post-partnersagreements) | confirmConsents |  |  |
| GET | [`/partners/agreements/gdpr`](#get-partnersagreementsgdpr) | getAgreement |  |  |
| POST | [`/partners/agreements/gdpr`](#post-partnersagreementsgdpr) | saveGdprAgreement |  |  |
| POST | [`/partners/contact`](#post-partnerscontact) | updateContact |  |  |
| GET | [`/partners/contacts`](#get-partnerscontacts) | getContacts |  |  |
| POST | [`/partners/contacts`](#post-partnerscontacts) | updateContacts |  |  |
| POST | [`/partners/contacts/mainContact`](#post-partnerscontactsmaincontact) | updateMainContact |  |  |
| POST | [`/partners/contacts/set-sms-for-invoice`](#post-partnerscontactsset-sms-for-invoice) | setSendSmsForInvoice |  |  |
| GET | [`/partners/contacts/sms-for-invoice`](#get-partnerscontactssms-for-invoice) | getSendSmsForInvoice |  |  |
| GET | [`/partners/contract-state`](#get-partnerscontract-state) | contractState |  |  |
| GET | [`/partners/execution`](#get-partnersexecution) | checkPartnerExecution |  |  |
| GET | [`/partners/last-customers`](#get-partnerslast-customers) | getLastCustomers |  |  |
| GET | [`/partners/legalEntity`](#get-partnerslegalentity) | getLegalEntity |  |  |
| POST | [`/partners/search`](#post-partnerssearch) | searchPartner |  |  |
| POST | [`/partners/set-partner/{partnerIdCol}`](#post-partnersset-partnerpartneridcol) | setPartner |  |  |
| GET | [`/partners/users-partners`](#get-partnersusers-partners) | getMultiAccount |  |  |
| GET | [`/partners/{partnerIdCrm}`](#get-partnerspartneridcrm) | getById |  |  |
| GET | [`/partners/{partnerIdCrm}/access-cases`](#get-partnerspartneridcrmaccess-cases) | getPartnerAccessCases |  |  |
| GET | [`/partners/{partnerIdCrm}/gdpr-alert`](#get-partnerspartneridcrmgdpr-alert) | getGdprAlert |  |  |
| POST | [`/partners/{partnerIdCrm}/permanent-address`](#post-partnerspartneridcrmpermanent-address) | updatePermanentAddress |  |  |
| PUT | [`/partners/{partnerIdCrm}/permanent-address`](#put-partnerspartneridcrmpermanent-address) | createPermanentAddress |  |  |
| GET | [`/registration/email-uniqueness`](#get-registrationemail-uniqueness) | verifyEmailUniqueness |  |  |
| GET | [`/registration/legal-entity`](#get-registrationlegal-entity) | checkLegalEntity |  |  |
| POST | [`/registration/mlt`](#post-registrationmlt) | registerWithMLT |  |  |
| POST | [`/registration/pre-registration`](#post-registrationpre-registration) | preRegistration |  |  |
| GET | [`/registration/providers`](#get-registrationproviders) | getExternalIdMappings |  |  |
| DELETE | [`/registration/providers/{externalIdProvider}`](#delete-registrationprovidersexternalidprovider) | removeExternalIdProvider |  |  |
| POST | [`/registration/providers/{externalIdProvider}/token`](#post-registrationprovidersexternalidprovidertoken) | createExternalIdProviderToken |  |  |
| POST | [`/registration/register`](#post-registrationregister) | registerFull |  |  |
| POST | [`/registration/resend-sms`](#post-registrationresend-sms) | resendRegistrationSMS |  |  |
| POST | [`/registration/search-and-sms`](#post-registrationsearch-and-sms) | searchPartnerByProductAndSendSMS |  |  |
| POST | [`/registration/search-partner-by-mail`](#post-registrationsearch-partner-by-mail) | searchPartnerInformation |  |  |
| GET | [`/registration/site-key`](#get-registrationsite-key) | siteKey |  |  |
| POST | [`/registration/verify-email-change`](#post-registrationverify-email-change) | verifyEmailChange |  |  |
| POST | [`/registration/verify-sms-code`](#post-registrationverify-sms-code) | verifySMSCode |  |  |
| GET | [`/registration/verify/{guid}`](#get-registrationverifyguid) | verifyRegistrationGuid |  |  |
| GET | [`/supply-points/{supplyPointId}/GetContract`](#get-supply-pointssupplypointidgetcontract) | getContracts |  |  |
| GET | [`/supply-points/{supplyPointId}/GetPaymentMethods`](#get-supply-pointssupplypointidgetpaymentmethods) | getPaymentMethods |  |  |
| GET | [`/user`](#get-user) | getDetail |  | yes |
| GET | [`/user/access-cases`](#get-useraccess-cases) | getUserAccessCases |  |  |
| DELETE | [`/user/access-cases/{caseGuidIsu}`](#delete-useraccess-casescaseguidisu) | removeAccessCase |  |  |
| POST | [`/user/access-cases/{caseGuidIsu}`](#post-useraccess-casescaseguidisu) | updateAccessCase |  |  |
| POST | [`/user/cancel`](#post-usercancel) | cancelUser |  |  |
| POST | [`/user/cancel-email-change`](#post-usercancel-email-change) | cancelEmailChangeRequest |  |  |
| GET | [`/user/check-phone`](#get-usercheck-phone) | checkUniquePhoneNumber |  |  |
| POST | [`/user/contract-agreement`](#post-usercontract-agreement) | saveContractAgreement |  |  |
| POST | [`/user/dcp/set-email`](#post-userdcpset-email) | assignDcpEmail |  |  |
| GET | [`/user/login-history`](#get-userlogin-history) | getUserLoginHistory |  |  |
| DELETE | [`/user/mfa/sms`](#delete-usermfasms) | disableMfaSms |  |  |
| GET | [`/user/mfa/sms`](#get-usermfasms) | checkMfaSms |  |  |
| POST | [`/user/mfa/sms`](#post-usermfasms) | enableMfaSms |  |  |
| POST | [`/user/mfa/sms-code`](#post-usermfasms-code) | sendMfaSmsCode |  |  |
| GET | [`/user/mfa/sms-code-check`](#get-usermfasms-code-check) | checkNewSmsCode |  |  |
| DELETE | [`/user/partner-relation/{partnerIdCrm}`](#delete-userpartner-relationpartneridcrm) | removePartnerRelation |  |  |
| POST | [`/user/partner-relation/{partnerIdCrm}`](#post-userpartner-relationpartneridcrm) | createPartnerRelation |  |  |
| POST | [`/user/partner/{partnerIdCrm}/save-selection`](#post-userpartnerpartneridcrmsave-selection) | savePartnerSelection |  |  |
| POST | [`/user/partners/supply-points/evaluate-notifications`](#post-userpartnerssupply-pointsevaluate-notifications) | evaluateNotifications |  |  |
| PUT | [`/user/partners/{partnerIdCrm}/standard`](#put-userpartnerspartneridcrmstandard) | setUserStandardPartner |  |  |
| POST | [`/user/refresh`](#post-userrefresh) | refreshUser |  |  |
| GET | [`/user/token-data`](#get-usertoken-data) | getTokenData | get_accounts |  |
| GET | [`/user/users-to-merge`](#get-userusers-to-merge) | getUsersToMerge |  |  |
| POST | [`/user/users-to-merge`](#post-userusers-to-merge) | unmergeUsers |  |  |
| GET | [`/user/users-to-simulate`](#get-userusers-to-simulate) | getUsersToSimulate |  |  |
| POST | [`/user/verify-email`](#post-userverify-email) | verifyUserEmail |  |  |
| POST | [`/user/verifyPartnerRelation`](#post-userverifypartnerrelation) | verifyPartnerRelation |  |  |
| POST | [`/user/verifyPartnerRelation/date`](#post-userverifypartnerrelationdate) | verifyPartnerRelationBirthDate |  |  |
| PUT | [`/users`](#put-users) | updateUserData |  |  |
| GET | [`/users/{partnerIdCol}/partners`](#get-userspartneridcolpartners) | getUserPartners |  |  |

### `PUT /actions/accept/{caseGuidCrm}`

- Operation `accept` (CPRCOLACTIONApi; `1152.ed6784ed.js`, `8771.4db6c17a.js`)
- Path params: `caseGuidCrm`
- Response: empty (HTTP 200/204)

### `GET /actions/check-guid/{caseGuidCrm}`

- Operation `checkGuid` (CPRCOLACTIONApi; `1152.ed6784ed.js`, `8771.4db6c17a.js`)
- Path params: `caseGuidCrm`
- Response: JSON object:
  - `actionType` (CodebookEntryDto)
  - `actionDeclainButtonVisible`
  - `actionText`
  - `actionOkButtonVisibility`
  - `actionGuid`

### `PUT /actions/refuse/{caseGuidCrm}`

- Operation `refuse` (CPRCOLACTIONApi; `1152.ed6784ed.js`, `8771.4db6c17a.js`)
- Path params: `caseGuidCrm`
- Response: empty (HTTP 200/204)

### `POST /addresses/do-address-check`

- Operation `doAddressCheck` (CPRCOLADDRESSApi; `1660.d82b41b0.js`, `9279.8ec3577d.js`)
- Body (JSON `DoAddressCheckRequestDto`):
  - `addressHouseNumber`
  - `addressStreet` (CodebookEntryIdentifierDto)
  - `addressLandRegistryNumber`
  - `addressZipCode`
  - `addressCity` (CodebookEntryIdentifierDto)
- Response: JSON object:
  - `isNewAddressValid`

### `GET /addresses/jdz`

- Operation `getAddresses` (CPRCOLADDRESSApi; `1660.d82b41b0.js`, `9279.8ec3577d.js`)
- Response: JSON array of object

### `GET /addresses/sap`

- Operation `readAddressesSap` (CPRCOLADDRESSApi; `1660.d82b41b0.js`, `9279.8ec3577d.js`)
- Response: JSON array of object

### `GET /agreement/address`

- Operation `getMailingAddress` (CPRCOLAGREEMENTApi; `3040.106c42c1.js`, `659.9c729cf6.js`)
- Query: `agreementIdIsu`, `supplyPointIdIsu`, `appId`
- Response: JSON object:
  - `addressCity` (CodebookEntryDto)
  - `addressZipCode`
  - `addressStandardAddress`
  - `addressStreet` (CodebookEntryDto)
  - `addressName`
  - `addressGuidCrm`
  - `addressLandRegistryNumber`
  - `addressHouseNumber`
  - `permanentAddress`

### `POST /agreement/address`

- Operation `setMailingAddress` (CPRCOLAGREEMENTApi; `3040.106c42c1.js`, `659.9c729cf6.js`)
- Query: `appId`
- Body (JSON `SetAddressBodyDto`):
  - `Address` (object)
  - `agreementIdIsu`
- Response: JSON object:
  - `ActivityIds`

### `GET /agreement/contacts`

- Operation `getElInvoicingMailsAndAddresses` (CPRCOLAGREEMENTApi; `3040.106c42c1.js`, `659.9c729cf6.js`)
- Query: `appId`
- Response: JSON array of object

### `GET /agreement/elfa`

- Operation `getElInvoicing` (CPRCOLAGREEMENTApi; `3040.106c42c1.js`, `659.9c729cf6.js`)
- Query: `contractGuid`, `contractIdCrm`, `partnerIdCrm`, `appId`
- Response: JSON object:
  - `status`
  - `agreementId`
  - `contact` (object)

### `POST /agreement/elfa`

- Operation `setElInvoicing` (CPRCOLAGREEMENTApi; `3040.106c42c1.js`, `659.9c729cf6.js`)
- Body (JSON `ActivationParamsDto`):
  - `AgreementInfo` (array)
  - `contactValue`
  - `partnerIdCrm`
  - `appId`
- Response: JSON object:
  - `ActivityIds`

### `GET /email-actions/check-guid/{caseGuidCrm}`

- Operation `check` (CPRCOLACTIONEMAILApi; `5987.b45d8699.js`, `8368.b10c27c4.js`)
- Path params: `caseGuidCrm`
- Response: JSON object:
  - `userAccountName`

### `PUT /email-actions/confirm/{caseGuidCrm}`

- Operation `confirm` (CPRCOLACTIONEMAILApi; `5987.b45d8699.js`, `8368.b10c27c4.js`)
- Path params: `caseGuidCrm`
- Response: empty (HTTP 200/204)

### `POST /favorite/create/{favoriteKey}`

- Operation `create` (CPRCOLFAVORITEApi; `4289.82fdc89c.js`, `6670.5c21f9f2.js`)
- Path params: `favoriteKey`
- Query: `scope`
- Body (JSON `RequestCreateBodyDto`):
  - `favoriteValue`
- Response: empty (HTTP 200/204)

### `GET /favorite/delete/{favoriteKey}`

- Operation `_delete` (CPRCOLFAVORITEApi; `4289.82fdc89c.js`, `6670.5c21f9f2.js`)
- Path params: `favoriteKey`
- Query: `scope`
- Response: empty (HTTP 200/204)

### `GET /favorite/keys`

- Operation `getKeys` (CPRCOLFAVORITEApi; `4289.82fdc89c.js`, `6670.5c21f9f2.js`)
- Query: `scope`
- Response: JSON object:
  - `favoriteKey`

### `GET /favorite/read/{favoriteKey}`

- Operation `read` (CPRCOLFAVORITEApi; `4289.82fdc89c.js`, `6670.5c21f9f2.js`)
- Path params: `favoriteKey`
- Query: `scope`
- Response: JSON object:
  - `favoriteValue`

### `POST /favorite/update/{favoriteKey}`

- Operation `update` (CPRCOLFAVORITEApi; `4289.82fdc89c.js`, `6670.5c21f9f2.js`)
- Path params: `favoriteKey`
- Query: `scope`
- Body (JSON `UpdateRequestBodyDto`):
  - `favoriteValue`
- Response: empty (HTTP 200/204)

### `PUT /partners`

- Operation `updatePartnerData` (CPRCOLPARTNERApi; `4290.d40500b4.js`)
- Body: `multipart/form-data` parts `files`, `updatePartnerParams`
- Response: JSON object:
  - `currentResponseStatus`

### `GET /partners/acconts-with-access`

- Operation `accountWithAccess` (CPRCOLPARTNERApi; `4290.d40500b4.js`)
- Response: JSON array of object

### `POST /partners/agreements`

- Operation `confirmConsents` (CPRCOLPARTNERApi; `4290.d40500b4.js`)
- Body (JSON `ConsentsDto`):
  - `consentType` (CodebookEntryIdentifierDto[])
- Response: empty (HTTP 200/204)

### `GET /partners/agreements/gdpr`

- Operation `getAgreement` (CPRCOLPARTNERApi; `4290.d40500b4.js`)
- Response: JSON object:
  - `consentValidToDate` (date)
  - `valid`
  - `relevant`
  - `postponed`
  - `consentValidFromDate` (date)
  - `category`
  - `consentStatus` (CodebookEntryDto)
  - `consentType` (CodebookEntryDto)

### `POST /partners/agreements/gdpr`

- Operation `saveGdprAgreement` (CPRCOLPARTNERApi; `4290.d40500b4.js`)
- Body (JSON `GdprAgreementInputDto`):
  - `postponed`
  - `consentStatus` (CodebookEntryIdentifierDto)
- Response: empty (HTTP 200/204)

### `POST /partners/contact`

- Operation `updateContact` (CPRCOLPARTNERApi; `4290.d40500b4.js`)
- Body (JSON `UpdateContactRequestBodyDto`):
  - `oldContact` (object)
  - `newContact` (object)
- Response: JSON object:
  - `activityId`

### `GET /partners/contacts`

- Operation `getContacts` (CPRCOLPARTNERApi; `4290.d40500b4.js`)
- Response: JSON array of object

### `POST /partners/contacts`

- Operation `updateContacts` (CPRCOLPARTNERApi; `4290.d40500b4.js`)
- Body (JSON array of `ContactDto`):
  - `contactValue`
  - `contactType` (CodebookEntryDto)
  - `contactFlagDefault`
- Response: JSON object:
  - `activityId`

### `POST /partners/contacts/mainContact`

- Operation `updateMainContact` (CPRCOLPARTNERApi; `4290.d40500b4.js`)
- Query: `createNew`
- Body (JSON `ContactDto`):
  - `contactValue`
  - `contactType` (CodebookEntryDto)
  - `contactFlagDefault`
- Response: JSON object:
  - `activityId`

### `POST /partners/contacts/set-sms-for-invoice`

- Operation `setSendSmsForInvoice` (CPRCOLPARTNERApi; `4290.d40500b4.js`)
- Body (JSON `InlineObjectDto`):
  - `sendSmsForInvoice`
- Response: empty (HTTP 200/204)

### `GET /partners/contacts/sms-for-invoice`

- Operation `getSendSmsForInvoice` (CPRCOLPARTNERApi; `4290.d40500b4.js`)
- Response: text

### `GET /partners/contract-state`

- Operation `contractState` (CPRCOLPARTNERApi; `4290.d40500b4.js`)
- Response: JSON object:
  - `valid`

### `GET /partners/execution`

- Operation `checkPartnerExecution` (CPRCOLPARTNERApi; `4290.d40500b4.js`)
- Response: text

### `GET /partners/last-customers`

- Operation `getLastCustomers` (CPRCOLPARTNERApi; `4290.d40500b4.js`)
- Response: JSON array of object

### `GET /partners/legalEntity`

- Operation `getLegalEntity` (CPRCOLPARTNERApi; `4290.d40500b4.js`)
- Response: JSON object:
  - `legalEntity`

### `POST /partners/search`

- Operation `searchPartner` (CPRCOLPARTNERApi; `4290.d40500b4.js`)
- Body (JSON `SearchPartnerRequestBodyDto`):
  - `phoneNumber`
  - `consumptionPlaceIdIsu`
  - `partnerIdCrm`
- Response: JSON array of object

### `POST /partners/set-partner/{partnerIdCol}`

- Operation `setPartner` (CPRCOLPARTNERApi; `4290.d40500b4.js`)
- Path params: `partnerIdCol`
- Response: empty (HTTP 200/204)

### `GET /partners/users-partners`

- Operation `getMultiAccount` (CPRCOLPARTNERApi; `4290.d40500b4.js`)
- Response: JSON array of object

### `GET /partners/{partnerIdCrm}`

- Operation `getById` (CPRCOLPARTNERApi; `4290.d40500b4.js`)
- Path params: `partnerIdCrm`
- Response: JSON object:
  - `Address` (object)
  - `individualSurname`
  - `Contact` (array)
  - `individualFirstName`
  - `legalEntityName`
  - `legalEntityNumber`
  - `legalEntityTaxIdentificationNumber`
  - `individualPersonalIdentificationNumber`
  - `partnerIdCrm`
  - `partnerType` (CodebookEntryDto)
  - `isOwnPartner`
  - `individualBirthDate` (date)
  - `isProspect`
  - `colLastContactInfoConfirmationDate` (date)
  - `colLastMergeAccountConfirmationDate` (date)
  - `colHasNonCommodity`
  - `partnerKindId`

### `GET /partners/{partnerIdCrm}/access-cases`

- Operation `getPartnerAccessCases` (CPRCOLPARTNERApi; `4290.d40500b4.js`)
- Path params: `partnerIdCrm`
- Response: JSON array of object

### `GET /partners/{partnerIdCrm}/gdpr-alert`

- Operation `getGdprAlert` (CPRCOLPARTNERApi; `4290.d40500b4.js`)
- Path params: `partnerIdCrm`
- Response: JSON object:
  - `gdprEnabled`

### `POST /partners/{partnerIdCrm}/permanent-address`

- Operation `updatePermanentAddress` (CPRCOLPARTNERApi; `4290.d40500b4.js`)
- Path params: `partnerIdCrm`
- Query: `changeAddressesOfSupplyPoints`
- Body: `multipart/form-data` parts `attachment`, `addressGuidCrm`
- Response: JSON object:
  - `activityIds`

### `PUT /partners/{partnerIdCrm}/permanent-address`

- Operation `createPermanentAddress` (CPRCOLPARTNERApi; `4290.d40500b4.js`)
- Path params: `partnerIdCrm`
- Query: `changeAddressesOfSupplyPoints`
- Body: `multipart/form-data` parts `Address`, `attachment`
- Response: JSON object:
  - `activityIds`

### `GET /registration/email-uniqueness`

- Operation `verifyEmailUniqueness` (CPRCOLUSERREGISTRATIONApi; `5417.ddf90310.js`, `7798.2dc2c9b7.js`)
- Query: `email`
- Response: JSON object:
  - `isUnique`

### `GET /registration/legal-entity`

- Operation `checkLegalEntity` (CPRCOLUSERREGISTRATIONApi; `5417.ddf90310.js`, `7798.2dc2c9b7.js`)
- Response: JSON object:
  - `isLegalEntity`

### `POST /registration/mlt`

- Operation `registerWithMLT` (CPRCOLUSERREGISTRATIONApi; `5417.ddf90310.js`, `7798.2dc2c9b7.js`)
- Body (JSON `RegisterWithMLTRequestBodyDto`):
  - `password`
  - `externalIdProvider`
  - `individualBirthDate`
  - `legalEntityNumber`
- Response: JSON object:
  - `tokenId`
  - `tokenValue`

### `POST /registration/pre-registration`

- Operation `preRegistration` (CPRCOLUSERREGISTRATIONApi; `5417.ddf90310.js`, `7798.2dc2c9b7.js`)
- Body (JSON `PreRegistrationRequestDto`):
  - `customer`
  - `referral`
  - `captcha`
  - `name`
  - `email`
  - `surname`
  - `isStandardRegistration`
- Response: JSON object:
  - `target`
  - `sendEmail`

### `GET /registration/providers`

- Operation `getExternalIdMappings` (CPRCOLUSERREGISTRATIONApi; `5417.ddf90310.js`, `7798.2dc2c9b7.js`)
- Response: JSON object:
  - `externalIdProvider`

### `DELETE /registration/providers/{externalIdProvider}`

- Operation `removeExternalIdProvider` (CPRCOLUSERREGISTRATIONApi; `5417.ddf90310.js`, `7798.2dc2c9b7.js`)
- Path params: `externalIdProvider`
- Response: empty (HTTP 200/204)

### `POST /registration/providers/{externalIdProvider}/token`

- Operation `createExternalIdProviderToken` (CPRCOLUSERREGISTRATIONApi; `5417.ddf90310.js`, `7798.2dc2c9b7.js`)
- Path params: `externalIdProvider`
- Response: JSON object:
  - `tokenId`
  - `tokenValue`

### `POST /registration/register`

- Operation `registerFull` (CPRCOLUSERREGISTRATIONApi; `5417.ddf90310.js`, `7798.2dc2c9b7.js`)
- Body (JSON `RegistrationRequestDto`):
  - `birthDate`
  - `legalEntityId`
  - `password2`
  - `password`
  - `guid`
  - `name`
  - `surname`
  - `heat`
  - `externalIdProvider`
  - `registrationType`
- Response: JSON object:
  - `username`
  - `createTokenOutput` (object)

### `POST /registration/resend-sms`

- Operation `resendRegistrationSMS` (CPRCOLUSERREGISTRATIONApi; `5417.ddf90310.js`, `7798.2dc2c9b7.js`)
- Body (JSON `ResendRegistrationSmsRequestDto`):
  - `token`
- Response: empty (HTTP 200/204)

### `POST /registration/search-and-sms`

- Operation `searchPartnerByProductAndSendSMS` (CPRCOLUSERREGISTRATIONApi; `5417.ddf90310.js`, `7798.2dc2c9b7.js`)
- Body (JSON `SearchByProductRequestDto`):
  - `target`
  - `customerNumber`
  - `commodity`
  - `email`
  - `phoneNumber`
- Response: JSON object:
  - `token`

### `POST /registration/search-partner-by-mail`

- Operation `searchPartnerInformation` (CPRCOLUSERREGISTRATIONApi; `5417.ddf90310.js`, `7798.2dc2c9b7.js`)
- Body (JSON `SearchByEmailRequestDto`):
  - `captcha`
  - `email`
- Response: JSON object:
  - `target`
  - `sendEmail`

### `GET /registration/site-key`

- Operation `siteKey` (CPRCOLUSERREGISTRATIONApi; `5417.ddf90310.js`, `7798.2dc2c9b7.js`)
- Response: JSON object:
  - `siteKey`

### `POST /registration/verify-email-change`

- Operation `verifyEmailChange` (CPRCOLUSERREGISTRATIONApi; `5417.ddf90310.js`, `7798.2dc2c9b7.js`)
- Body (JSON `VerifyEmailChangeBodyDto`):
  - `guid`
- Response: empty (HTTP 200/204)

### `POST /registration/verify-sms-code`

- Operation `verifySMSCode` (CPRCOLUSERREGISTRATIONApi; `5417.ddf90310.js`, `7798.2dc2c9b7.js`)
- Body (JSON `VerifiSmsCodeRequestDto`):
  - `smsCode`
  - `token`
- Response: JSON object:
  - `target`
  - `sendEmail`

### `GET /registration/verify/{guid}`

- Operation `verifyRegistrationGuid` (CPRCOLUSERREGISTRATIONApi; `5417.ddf90310.js`, `7798.2dc2c9b7.js`)
- Path params: `guid`
- Query: `heat`, `registrationType`
- Response: JSON object:
  - `prospect`
  - `registrationType`
  - `contractChecked`
  - `organization`
  - `email`

### `GET /supply-points/{supplyPointId}/GetContract`

- Operation `getContracts` (CPRCOLCONTRACTApi; `3209.3573e7cf.js`)
- Path params: `supplyPointId`
- Response: JSON object:
  - `Product` (array)
  - `ProductConfiguration` (array)

### `GET /supply-points/{supplyPointId}/GetPaymentMethods`

- Operation `getPaymentMethods` (CPRCOLCONTRACTApi; `3209.3573e7cf.js`)
- Path params: `supplyPointId`
- Response: JSON object:
  - `actualAdvancePaymentMethod` (object)
  - `actualAdditionalPaymentMethod` (object)
  - `actualPaymentConfiguration` (array)
  - `actualOverpaymentMethod` (object)

### `GET /user`

- Operation `getDetail` (CPRCOLUSERApi; `6539.705b0bce.js`)
- Response: JSON `UserDto`:
  - `LoginEntry` (LoginEntryDto[])
    - `userColLastLoginIpAddress`
    - `userColLastLoginDate` (date)
    - `userColLastLoginSuccess`
  - `partnerIdCol`
  - `Person` (PersonDto)
    - `individualFirstName`
    - `individualFirstTitle` (CodebookEntryDto)
    - `individualSecondTitle` (CodebookEntryDto)
    - `individualSurname`
    - `individualAfterTitle` (CodebookEntryDto)
    - `individualPersonalIdentificationNumber`
    - `individualBirthDate` (date)
    - `individualSalutationVocative`
  - `Contact` (ContactDto[])
    - `contactValue`
    - `contactType` (CodebookEntryDto)
    - `contactFlagDefault`
  - `pendingEmailChangeFlag`
  - `partnerPrefferredLanguage`
- Captured sample: probe_out: `user`

  Response shape (anonymized, values replaced by types):

```json
{
 "LoginEntry": [
  {
   "userColLastLoginIpAddress": "string",
   "userColLastLoginDate": "YYYY-MM-DD",
   "userColLastLoginSuccess": "boolean"
  }
 ],
 "partnerIdCol": "string",
 "Person": {
  "individualFirstName": "string",
  "individualFirstTitle": {
   "value": "string"
  },
  "individualSurname": "string",
  "individualAfterTitle": {},
  "individualPersonalIdentificationNumber": "string",
  "individualBirthDate": "YYYY-MM-DD",
  "individualSalutationVocative": "string"
 },
 "Contact": [
  {
   "contactValue": "string",
   "contactType": {
    "entrySystemSpecificId": "EML",
    "systemId": "INT",
    "entryId": "EML",
    "longValue": "string",
    "entryOrder": "number",
    "language": "CZ",
    "validTo": "date-time",
    "validFrom": "date-time",
    "codebookId": "TP_CONT",
    "value": "string"
   }
  }
 ],
 "pendingEmailChangeFlag": "boolean"
}
```

### `GET /user/access-cases`

- Operation `getUserAccessCases` (CPRCOLUSERApi; `6539.705b0bce.js`)
- Response: JSON array of `AccessCaseDto`:
  - `partnerIdCrm`
  - `caseCategory` (CodebookEntryDto)
  - `Sender` (SenderDto)
    - `individualFirstName`
    - `individualBirthDate` (date)
    - `Contact` (ContactDto)
    - `partnerIdCol`
    - `individualSurname`
  - `Receiver` (ReceiverDto)
    - `individualSurname`
    - `Contact` (ContactDto)
    - `individualFirstName`
    - `partnerIdCol`
    - `individualBirthDate` (date)
  - `caseStatus` (CodebookEntryDto)
  - `caseGuidIsu`
  - `caseCreationDate` (date)
  - `caseExpired`

### `DELETE /user/access-cases/{caseGuidIsu}`

- Operation `removeAccessCase` (CPRCOLUSERApi; `6539.705b0bce.js`)
- Path params: `caseGuidIsu`
- Response: empty (HTTP 200/204)

### `POST /user/access-cases/{caseGuidIsu}`

- Operation `updateAccessCase` (CPRCOLUSERApi; `6539.705b0bce.js`)
- Path params: `caseGuidIsu`
- Query: `state`
- Response: empty (HTTP 200/204)

### `POST /user/cancel`

- Operation `cancelUser` (CPRCOLUSERApi; `6539.705b0bce.js`)
- Response: empty (HTTP 200/204)

### `POST /user/cancel-email-change`

- Operation `cancelEmailChangeRequest` (CPRCOLUSERApi; `6539.705b0bce.js`)
- Response: empty (HTTP 200/204)

### `GET /user/check-phone`

- Operation `checkUniquePhoneNumber` (CPRCOLUSERApi; `6539.705b0bce.js`)
- Response: JSON `BodyDto`:
  - `enabled`
  - `isUniquePhoneNumber`

### `POST /user/contract-agreement`

- Operation `saveContractAgreement` (CPRCOLUSERApi; `6539.705b0bce.js`)
- Response: empty (HTTP 200/204)

### `POST /user/dcp/set-email`

- Operation `assignDcpEmail` (CPRCOLUSERApi; `6539.705b0bce.js`)
- Body (JSON `AssignDcpEmailRequestBodyDto`):
  - `emailAssigned`
- Response: JSON `AssignDcpEmailResponseBodyDto`:
  - `isUniquePhoneNumber`

### `GET /user/login-history`

- Operation `getUserLoginHistory` (CPRCOLUSERApi; `6539.705b0bce.js`)
- Response: JSON array of `LoginEntryDto`:
  - `userColLastLoginIpAddress`
  - `userColLastLoginDate` (date)
  - `userColLastLoginSuccess`

### `DELETE /user/mfa/sms`

- Operation `disableMfaSms` (CPRCOLUSERApi; `6539.705b0bce.js`)
- Response: empty (HTTP 200/204)

### `GET /user/mfa/sms`

- Operation `checkMfaSms` (CPRCOLUSERApi; `6539.705b0bce.js`)
- Response: JSON `CheckMfaSmsResponseDto`:
  - `enabled`
  - `isUniquePhoneNumber`

### `POST /user/mfa/sms`

- Operation `enableMfaSms` (CPRCOLUSERApi; `6539.705b0bce.js`)
- Body (JSON `RequestBodyDto`):
  - `resend`
- Response: empty (HTTP 200/204)

### `POST /user/mfa/sms-code`

- Operation `sendMfaSmsCode` (CPRCOLUSERApi; `6539.705b0bce.js`)
- Body (JSON `SendMfaSmsRequestBodyDto`):
  - `resend`
- Response: empty (HTTP 200/204)

### `GET /user/mfa/sms-code-check`

- Operation `checkNewSmsCode` (CPRCOLUSERApi; `6539.705b0bce.js`)
- Response: JSON `CheckSmsCodeResponseBodyDto`:
  - `supplyPoints` (SupplyPointsDto[])
    - `supplyPointNotificationType`
    - `supplyPointIdIsu`
    - `commodityName`
    - `partnerIdCol`
    - `supplyPointAddress` (SupplyPointAddressDto)
    - `contractName`
    - `partnerIdCrm`

### `DELETE /user/partner-relation/{partnerIdCrm}`

- Operation `removePartnerRelation` (CPRCOLUSERApi; `6539.705b0bce.js`)
- Path params: `partnerIdCrm`
- Response: empty (HTTP 200/204)

### `POST /user/partner-relation/{partnerIdCrm}`

- Operation `createPartnerRelation` (CPRCOLUSERApi; `6539.705b0bce.js`)
- Path params: `partnerIdCrm`
- Response: empty (HTTP 200/204)

### `POST /user/partner/{partnerIdCrm}/save-selection`

- Operation `savePartnerSelection` (CPRCOLUSERApi; `6539.705b0bce.js`)
- Path params: `partnerIdCrm`
- Response: empty (HTTP 200/204)

### `POST /user/partners/supply-points/evaluate-notifications`

- Operation `evaluateNotifications` (CPRCOLUSERApi; `6539.705b0bce.js`)
- Body (JSON `UserRequestDto`):
  - `partnerIdCol`
- Response: JSON `UserResponseDto`:
  - `dynamicTariff` (DynamicTariffDto)
    - `userColLastLoginIpAddress`
    - `userColLastLoginDate` (date)
    - `userColLastLoginSuccess`
  - `consumption` (ConsumptionDto)
    - `supplyPoints` (SupplyPointsDto[])

### `PUT /user/partners/{partnerIdCrm}/standard`

- Operation `setUserStandardPartner` (CPRCOLUSERApi; `6539.705b0bce.js`)
- Path params: `partnerIdCrm`
- Response: empty (HTTP 200/204)

### `POST /user/refresh`

- Operation `refreshUser` (CPRCOLUSERApi; `6539.705b0bce.js`)
- Response: JSON `RefreshUserOutDto`:
  - `tokenData` (TokenDataDto)
    - `ppjmFull`
    - `individualFirstName`
    - `individualSurname`
    - `partners`
    - `defaultPartner`
    - `partnerIdCol`
    - `partnerIdColHash`
    - `email`
    - `roleName`
  - `firstLogin`

### `GET /user/token-data`

- Operation `getTokenData` (CPRCOLUSERApi; `6539.705b0bce.js`)
- **Used by integration**: `api.py` get_accounts
- Response: JSON `TokenDataDto`:
  - `ppjmFull`
  - `individualFirstName`
  - `individualSurname`
  - `partners`
  - `defaultPartner`
  - `partnerIdCol`
  - `partnerIdColHash`
  - `email`
  - `roleName`

### `GET /user/users-to-merge`

- Operation `getUsersToMerge` (CPRCOLUSERApi; `6539.705b0bce.js`)
- Response: JSON array of `UserWithAccessDto`:
  - `individualFirstName`
  - `individualSurname`
  - `mergingTo`
  - `hasSameEmail`
  - `hasNoEmail`
  - `username`
  - `isRequested`
  - `partners` (UserMergeDto[])
    - `partnerIdCol`
    - `hasEmail`
    - `isDirectMerge`
    - `isOwnPartner`
    - `hasSameEmail`
    - `isRequested`
    - `contacts` (ContactDto[])
  - `isDirectMerge`
  - `directMerge`
  - `email`

### `POST /user/users-to-merge`

- Operation `unmergeUsers` (CPRCOLUSERApi; `6539.705b0bce.js`)
- Body (JSON `UnmergeUsersInDto`):
  - `partnerIdColList`
- Response: JSON array of `UserMergeStatusDto`:
  - `statusMessage`
  - `status`
  - `partnerIdCol`

### `GET /user/users-to-simulate`

- Operation `getUsersToSimulate` (CPRCOLUSERApi; `6539.705b0bce.js`)
- Response: JSON array of `UserToSimulateDto`:
  - `individualFirstName`
  - `partnerIdCol`
  - `userColLastLoginDate` (date)
  - `individualSurname`
  - `email`

### `POST /user/verify-email`

- Operation `verifyUserEmail` (CPRCOLUSERApi; `6539.705b0bce.js`)
- Body (JSON `DummyObjectDto`):
  - `$virtualProperty`
- Response: empty (HTTP 200/204)

### `POST /user/verifyPartnerRelation`

- Operation `verifyPartnerRelation` (CPRCOLUSERApi; `6539.705b0bce.js`)
- Body (JSON `VerifyRelationBodyDto`):
  - `partnerIdCrm`
- Response: JSON `PartnerTypeDto`:
  - `person`
  - `organisation`
  - `group`
  - `token`
  - `partnerType` (CodebookEntryDto)

### `POST /user/verifyPartnerRelation/date`

- Operation `verifyPartnerRelationBirthDate` (CPRCOLUSERApi; `6539.705b0bce.js`)
- Query: `legalEntityNumber`
- Body (JSON `VerifyRelationBirthdayBodyDto`):
  - `partnerIdCrm`
- Response: JSON `UserMergeDto`:
  - `partnerIdCol`
  - `hasEmail`
  - `isDirectMerge`
  - `isOwnPartner`
  - `hasSameEmail`
  - `isRequested`
  - `contacts` (ContactDto[])
    - `contactValue`
    - `contactType` (CodebookEntryDto)
    - `contactFlagDefault`

### `PUT /users`

- Operation `updateUserData` (CPRCOLUSERApi; `6539.705b0bce.js`)
- Body (JSON `UpdateUserParamsDto`):
  - `individualFirstName`
  - `individualBirthDate` (date)
  - `individualSurname`
  - `phoneNumber`
  - `email`
- Response: empty (HTTP 200/204)

### `GET /users/{partnerIdCol}/partners`

- Operation `getUserPartners` (CPRCOLUSERApi; `6539.705b0bce.js`)
- Path params: `partnerIdCol`
- Query: `detail`
- Response: JSON array of `PartnerDto`:
  - `individualFullName`
  - `partnerType` (CodebookEntryDto)
  - `Address` (AddressDto)
    - `addressZipCode`
    - `addressHouseNumber`
    - `addressCity` (CodebookEntryDto)
    - `addressStreet` (CodebookEntryDto)
    - `addressLandRegistryNumber`
  - `individualBirthDate` (date)
  - `individualPersonalIdentificationNumber`
  - `legalEntityName`
  - `legalEntityTaxIdentificationNumber`
  - `partnerIdCrm`
  - `individualFirstName`
  - `individualSurname`
  - `legalEntityNumber`
  - `Contact` (ContactDto[])
    - `contactValue`
    - `contactType` (CodebookEntryDto)
    - `contactFlagDefault`

