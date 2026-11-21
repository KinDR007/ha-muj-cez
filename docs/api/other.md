# Other COL API groups

Endpoints of the COL API not covered by the other files (cases/tickets, complaints, appointments, customer centers, feedback, forms, heating service, leads, mobile (MVNO/O2), NS services, CMS redaction, reporting, AI assistant, codebooks), followed by APIs on **other base URLs** that the customer portal bundle also contains. Those are listed for completeness; they are not reachable via `col-api/prod/1.0`.

Generated from the portal bundle (`tools/probe/index.js`, `tools/probe/chunks/*.js`, release col-fe@3.66.0). Field names are the JSON wire names; `(XxxDto)` marks a nested object, `CodebookEntryDto` is described in [README](README.md#codebook-entries). Types not shown are plain strings/numbers/booleans.

| Method | Path | Operation | Integration | Sample |
|---|---|---|---|---|
| PUT | [`/ai-assistant/api/v1/keep-session/{sessionId}`](#put-ai-assistantapiv1keep-sessionsessionid) | keepSession |  |  |
| POST | [`/ai-assistant/api/v1/message`](#post-ai-assistantapiv1message) | sendMessage |  |  |
| POST | [`/ai-assistant/api/v1/rating`](#post-ai-assistantapiv1rating) | sendRating |  |  |
| POST | [`/ai-assistant/api/v1/session`](#post-ai-assistantapiv1session) | createSession |  |  |
| GET | [`/ai-assistant/as/api/v1/webchat/{projectId}/{clientId}`](#get-ai-assistantasapiv1webchatprojectidclientid) | getSettings |  |  |
| GET | [`/ai-assistant/availability`](#get-ai-assistantavailability) | getAvailability |  |  |
| GET | [`/appointments`](#get-appointments) | getCustomerAppointments |  |  |
| GET | [`/appointments/search`](#get-appointmentssearch) | getAppointmentsByTimeSlots |  |  |
| DELETE | [`/appointments/{appointmentId}`](#delete-appointmentsappointmentid) | deleteAppointment |  |  |
| GET | [`/branches`](#get-branches) | getBranches |  |  |
| GET | [`/branches/{branchId}/capacity`](#get-branchesbranchidcapacity) | getGeneralCapacityForBranch |  |  |
| GET | [`/branches/{branchId}/services`](#get-branchesbranchidservices) | getBranchServices |  |  |
| GET | [`/branches/{branchId}/services/{serviceId}/dates`](#get-branchesbranchidservicesserviceiddates) | getBranchDatesForServices |  |  |
| GET | [`/branches/{branchId}/services/{serviceId}/dates/{date}/slots`](#get-branchesbranchidservicesserviceiddatesdateslots) | getTheoreticalTimeSlots |  |  |
| GET | [`/branches/{branchId}/services/{serviceId}/dates/{date}/times`](#get-branchesbranchidservicesserviceiddatesdatetimes) | getBranchTimeSlots |  |  |
| POST | [`/branches/{branchId}/services/{serviceId}/dates/{date}/times/{time}`](#post-branchesbranchidservicesserviceiddatesdatetimestime) | bookAppointment |  |  |
| PUT | [`/branches/{branchId}/services/{serviceId}/dates/{date}/times/{time}/{appointmentId}`](#put-branchesbranchidservicesserviceiddatesdatetimestimeappointmentid) | updateAppointment |  |  |
| POST | [`/cases`](#post-cases) | getAllCases |  |  |
| GET | [`/cases/receive/channels`](#get-casesreceivechannels) | getListReceiveChannels |  |  |
| GET | [`/cases/settings/{caseCategory}`](#get-casessettingscasecategory) | getCaseSettings |  |  |
| GET | [`/cases/tasks/{taskId}`](#get-casestaskstaskid) | getCaseTaskById |  |  |
| POST | [`/cases/tasks/{taskId}`](#post-casestaskstaskid) | updateCaseTask |  |  |
| POST | [`/cases/{caseCategory}`](#post-casescasecategory) | createCase |  |  |
| GET | [`/cases/{caseId}`](#get-casescaseid) | getCaseById |  |  |
| GET | [`/cases/{caseId}/axis`](#get-casescaseidaxis) | getCaseAxis |  |  |
| POST | [`/cases/{caseId}/tasks`](#post-casescaseidtasks) | getAllCaseTasks |  |  |
| GET | [`/cases/{caseId}/tasks/{taskId}`](#get-casescaseidtaskstaskid) | getCaseTaskByIdAndCaseId |  |  |
| GET | [`/cases/{caseId}/tasks/{taskId}/events`](#get-casescaseidtaskstaskidevents) | getAllCaseTaskEvents |  |  |
| GET | [`/codebooks/{codebookId}`](#get-codebookscodebookid) | getCodebook |  |  |
| POST | [`/complaints`](#post-complaints) | createComplaint |  |  |
| GET | [`/complaints/customization`](#get-complaintscustomization) | getComplaintFormCustomization |  |  |
| GET | [`/complaints/step/{categoryIds}`](#get-complaintsstepcategoryids) | getNextComplaintStep |  |  |
| GET | [`/customer-centers/allV2`](#get-customer-centersallv2) | getAllCustomerCentersV2 |  |  |
| GET | [`/reporting/op`](#get-reportingop) | getOpActivityLog |  |  |
| GET | [`/reporting/simu-user`](#get-reportingsimu-user) | getSimuUserActivityLog |  |  |
| GET | [`/reporting/user`](#get-reportinguser) | getUserActivityLog |  |  |
| POST | [`/feedback`](#post-feedback) | setFeedback |  |  |
| POST | [`/feedback/app-check`](#post-feedbackapp-check) | getFeedbackAppCheck |  |  |
| GET | [`/feedback/check`](#get-feedbackcheck) | getFeedbackCheck |  |  |
| GET | [`/feedback/configuration/{questionnaireId}`](#get-feedbackconfigurationquestionnaireid) | getFeedbackConfiguration |  |  |
| POST | [`/forms/ais-code`](#post-formsais-code) | setAisCode |  |  |
| GET | [`/forms/bank-accounts`](#get-formsbank-accounts) | getBankAccounts |  |  |
| POST | [`/forms/payment-complaint`](#post-formspayment-complaint) | createPaymentComplaint |  |  |
| POST | [`/heating-service/all`](#post-heating-serviceall) | getHeatingServiceContracts |  |  |
| POST | [`/heating-service/request/confirm`](#post-heating-servicerequestconfirm) | confirmHeatingServiceRequirement |  |  |
| POST | [`/heating-service/request/confirm-callback`](#post-heating-servicerequestconfirm-callback) | confirmServiceRequestCallback |  |  |
| GET | [`/heating-service/request/free-terms`](#get-heating-servicerequestfree-terms) | getFreeTerms |  |  |
| POST | [`/heating-service/request/reject`](#post-heating-servicerequestreject) | rejectHeatingServiceRequirement |  |  |
| POST | [`/save-app-evaluation`](#post-save-app-evaluation) | saveAppEvaluation |  |  |
| POST | [`/leads`](#post-leads) | createLead |  |  |
| POST | [`/logistics-partner/history`](#post-logistics-partnerhistory) | getHistory |  |  |
| DELETE | [`/logistics-partner/lock`](#delete-logistics-partnerlock) | releaseLock |  |  |
| POST | [`/logistics-partner/lock`](#post-logistics-partnerlock) | createLock |  |  |
| PUT | [`/logistics-partner/lock`](#put-logistics-partnerlock) | prolongateLock |  |  |
| POST | [`/logistics-partner/sim`](#post-logistics-partnersim) | setSIM |  |  |
| GET | [`/logistics-partner/unprocessed`](#get-logistics-partnerunprocessed) | getAllUnprocessed |  |  |
| POST | [`/mvno-activations/activate-sim`](#post-mvno-activationsactivate-sim) | activateSim |  |  |
| GET | [`/mvno-activations/activation-data/{orderGuid}`](#get-mvno-activationsactivation-dataorderguid) | getActivationData |  |  |
| GET | [`/mvno-activations/portin-data/{orderGuid}`](#get-mvno-activationsportin-dataorderguid) | getPortinData |  |  |
| GET | [`/mvno-activations/portin-dates`](#get-mvno-activationsportin-dates) | getAvailablePortInDates |  |  |
| POST | [`/mvno-activations/portin-sim`](#post-mvno-activationsportin-sim) | portinSim |  |  |
| GET | [`/mvno/add-benefited-phone-number`](#get-mvnoadd-benefited-phone-number) | addBenefitedPhoneNumber |  |  |
| GET | [`/mvno/benefited-phone-numbers`](#get-mvnobenefited-phone-numbers) | getBenefitedPhoneNumbers |  |  |
| POST | [`/mvno/block-sim`](#post-mvnoblock-sim) | blockSimCard |  |  |
| GET | [`/mvno/cache`](#get-mvnocache) | createMvnoCache |  |  |
| GET | [`/mvno/check-mobile-device`](#get-mvnocheck-mobile-device) | checkMobileDevice |  |  |
| GET | [`/mvno/contract`](#get-mvnocontract) | getMobileContractsFileId |  |  |
| GET | [`/mvno/current-usage`](#get-mvnocurrent-usage) | getCurrentUsage |  |  |
| GET | [`/mvno/customer-cookie`](#get-mvnocustomer-cookie) | getCustomerCookie |  |  |
| GET | [`/mvno/employee-tokens`](#get-mvnoemployee-tokens) | getEmployeeTokens |  |  |
| GET | [`/mvno/get-title`](#get-mvnoget-title) | getTitle |  |  |
| GET | [`/mvno/history-usage`](#get-mvnohistory-usage) | getHistoryUsage |  |  |
| GET | [`/mvno/history-usage-csv`](#get-mvnohistory-usage-csv) | getHistoryUsageCsv |  |  |
| GET | [`/mvno/history/{phoneNumber}/{pageNr}`](#get-mvnohistoryphonenumberpagenr) | getHistory |  |  |
| GET | [`/mvno/list`](#get-mvnolist) | readMobileContracts |  |  |
| POST | [`/mvno/modify-package/{phoneNumber}`](#post-mvnomodify-packagephonenumber) | modifyMvnoPackage |  |  |
| GET | [`/mvno/oku`](#get-mvnooku) | getOkuSecurityCode |  |  |
| GET | [`/mvno/payment-history`](#get-mvnopayment-history) | getPaymentHistory |  |  |
| GET | [`/mvno/payment-progress`](#get-mvnopayment-progress) | getPaymentProgress |  |  |
| GET | [`/mvno/products/{phoneNumber}`](#get-mvnoproductsphonenumber) | getRelatedProducts |  |  |
| GET | [`/mvno/puk`](#get-mvnopuk) | getPukSecurityCode |  |  |
| GET | [`/mvno/remove-benfited-phone-number`](#get-mvnoremove-benfited-phone-number) | removeBenefitedPhoneNumber |  |  |
| POST | [`/mvno/send-employee-token`](#post-mvnosend-employee-token) | sendEmployeeToken |  |  |
| POST | [`/mvno/service-activate`](#post-mvnoservice-activate) | activatePackage |  |  |
| POST | [`/mvno/service-deactivate`](#post-mvnoservice-deactivate) | deactivatePackage |  |  |
| GET | [`/mvno/service-settings`](#get-mvnoservice-settings) | getServicesSettings |  |  |
| POST | [`/mvno/service-settings-change`](#post-mvnoservice-settings-change) | changePackage |  |  |
| POST | [`/mvno/set-title`](#post-mvnoset-title) | setTitle |  |  |
| POST | [`/mvno/set-token-description`](#post-mvnoset-token-description) | setTokenDescription |  |  |
| GET | [`/mvno/tariff-settings/{phoneNumber}`](#get-mvnotariff-settingsphonenumber) | getMvnoTariffSettings |  |  |
| GET | [`/mvno/units-history/{phoneNumber}`](#get-mvnounits-historyphonenumber) | getMvnoUnitsHistory |  |  |
| GET | [`/mvno/{phoneNumber}`](#get-mvnophonenumber) | getDetail |  |  |
| GET | [`/ns-services`](#get-ns-services) | getNsServices |  |  |
| GET | [`/ns-services/{idOpLeo}/documents/{idLeo7Documents}`](#get-ns-servicesidopleodocumentsidleo7documents) | getNsDocument |  |  |
| GET | [`/ns-services/{id}`](#get-ns-servicesid) | getNsDetail |  |  |
| GET | [`/o2/calls`](#get-o2calls) | getCalls |  |  |
| PUT | [`/o2/order`](#put-o2order) | putOrder |  |  |
| POST | [`/o2/postStatus`](#post-o2poststatus) | postStatus |  |  |
| GET | [`/o2/sim`](#get-o2sim) | getSim |  |  |
| GET | [`/o2/spent`](#get-o2spent) | getSpent |  |  |
| GET | [`/o2/statement`](#get-o2statement) | getCurrentStatement |  |  |
| GET | [`/o2/subscription`](#get-o2subscription) | getSubscription |  |  |
| GET | [`/o2/units-history/{phoneNumber}`](#get-o2units-historyphonenumber) | getUnitsHistory |  |  |
| GET | [`/o2/usages`](#get-o2usages) | getUsages |  |  |
| POST | [`/redaction/attachment/{itemId}`](#post-redactionattachmentitemid) | attachFile |  |  |
| GET | [`/redaction/categories`](#get-redactioncategories) | getCategories |  |  |
| POST | [`/redaction/categories/hierarchy`](#post-redactioncategorieshierarchy) | createHierarchy |  |  |
| POST | [`/redaction/categories/hierarchy/text`](#post-redactioncategorieshierarchytext) | getText |  |  |
| POST | [`/redaction/categories/hierarchy/texts`](#post-redactioncategorieshierarchytexts) | createText |  |  |
| PUT | [`/redaction/categories/hierarchy/texts/{textId}`](#put-redactioncategorieshierarchytextstextid) | updateText |  |  |
| DELETE | [`/redaction/categories/hierarchy/texts/{textItemId}`](#delete-redactioncategorieshierarchytextstextitemid) | deleteText |  |  |
| DELETE | [`/redaction/categories/hierarchy/{itemId}`](#delete-redactioncategorieshierarchyitemid) | deleteHierarchy |  |  |
| PUT | [`/redaction/categories/hierarchy/{itemId}`](#put-redactioncategorieshierarchyitemid) | updateHierarchy |  |  |
| GET | [`/redaction/categories/{categoryId}/hierarchy`](#get-redactioncategoriescategoryidhierarchy) | getHierarchyByCategory |  |  |
| GET | [`/redaction/file`](#get-redactionfile) | getHierarchyFile |  |  |
| GET | [`/redaction/file-info`](#get-redactionfile-info) | getHierarchyFilesGuidParam |  |  |
| DELETE | [`/redaction/{guid}`](#delete-redactionguid) | deleteFile |  |  |
| POST | [`/bpm/start-process`](#post-bpmstart-process) | startProcess |  |  |
| POST | [`/bpm/{caseIdCm}/cancel`](#post-bpmcaseidcmcancel) | cancelCase |  |  |
| POST | [`/bpm/{caseIdCm}/close`](#post-bpmcaseidcmclose) | closeProcess |  |  |
| POST | [`/bpm/{caseIdCm}/complete-current-step`](#post-bpmcaseidcmcomplete-current-step) | completeCurrentStep |  |  |
| POST | [`/bpm/{caseIdCm}/create-process-event`](#post-bpmcaseidcmcreate-process-event) | createProcessEvent |  |  |
| GET | [`/bpm/{caseIdCm}/current-step-detail`](#get-bpmcaseidcmcurrent-step-detail) | getCurrentStepDetail |  |  |
| POST | [`/bpm/{caseIdCm}/partial-save`](#post-bpmcaseidcmpartial-save) | partialSave |  |  |
| POST | [`/bpm/{caseIdCm}/step-back`](#post-bpmcaseidcmstep-back) | stepBack |  |  |
| POST | [`/bpm/{caseIdCm}/take-over-step`](#post-bpmcaseidcmtake-over-step) | takeOverStep |  |  |
| GET | [`/cases/documents/{caseKey}`](#get-casesdocumentscasekey) | getCaseDocuments |  |  |
| GET | [`/cases/permissions`](#get-casespermissions) | getPermissions |  |  |
| GET | [`/cases/statusFlow/{processIdCm}`](#get-casesstatusflowprocessidcm) | getStatusFlow |  |  |
| POST | [`/cases/task/{taskKey}/solve`](#post-casestasktaskkeysolve) | solveTask |  |  |
| GET | [`/cases/tasks/{caseKey}`](#get-casestaskscasekey) | getCaseTasks |  |  |
| PATCH | [`/cases/tasks/{taskKey}`](#patch-casestaskstaskkey) | updateTask |  |  |
| POST | [`/cases/tasks/{taskKey}/documents/content`](#post-casestaskstaskkeydocumentscontent) | uploadTaskDocument |  |  |
| PUT | [`/cases/tasks/{taskKey}/documents/prepare`](#put-casestaskstaskkeydocumentsprepare) | prepareTaskDocument |  |  |
| GET | [`/cases/tasks/{taskKey}/documents/{documentId}/content`](#get-casestaskstaskkeydocumentsdocumentidcontent) | downloadTaskDocument |  |  |
| POST | [`/cases/tasks/{taskKey}/documents/{documentId}/merge`](#post-casestaskstaskkeydocumentsdocumentidmerge) | mergeTaskDocument |  |  |
| GET | [`/cases/tasks/{taskKey}/history/customer`](#get-casestaskstaskkeyhistorycustomer) | getTaskHistoryCustomer |  |  |
| GET | [`/cases/tasks/{taskKey}/history/servicer`](#get-casestaskstaskkeyhistoryservicer) | getTaskHistoryServicer |  |  |
| GET | [`/cases/translate-id`](#get-casestranslate-id) | translateCaseId |  |  |
| GET | [`/cases/{caseKey}`](#get-casescasekey) | getCaseDetail |  |  |
| PATCH | [`/cases/{caseKey}/attrs`](#patch-casescasekeyattrs) | patchHeaderAttributes |  |  |
| POST | [`/cases/{caseKey}/documents/content`](#post-casescasekeydocumentscontent) | uploadDocument |  |  |
| POST | [`/cases/{caseKey}/documents/{documentId}/merge`](#post-casescasekeydocumentsdocumentidmerge) | mergeDocument |  |  |
| GET | [`/cases/{caseKey}/history`](#get-casescasekeyhistory) | getCaseHistory |  |  |
| GET | [`/cases/{caseKey}/history/filters`](#get-casescasekeyhistoryfilters) | getCaseHistoryFiltres |  |  |
| GET | [`/cases/{caseKey}/notes`](#get-casescasekeynotes) | getCaseNotes |  |  |
| GET | [`/cases/{caseKey}/objectLinks`](#get-casescasekeyobjectlinks) | getObjectLinks |  |  |
| POST | [`/cases/{caseKey}/objectLinks`](#post-casescasekeyobjectlinks) | addObjectLink |  |  |
| DELETE | [`/cases/{caseKey}/objectLinks/{objectTypeId}/{objectKey}`](#delete-casescasekeyobjectlinksobjecttypeidobjectkey) | deleteObjectLink |  |  |
| POST | [`/cases/{caseKey}/tasks`](#post-casescasekeytasks) | createTask |  |  |
| POST | [`/cases/{caseKey}/updateFlags`](#post-casescasekeyupdateflags) | updateFlags |  |  |
| GET | [`/employees/suggest`](#get-employeessuggest) | suggestEmployee |  |  |
| GET | [`/tasks/translate-id`](#get-taskstranslate-id) | translateTaskId |  |  |
| GET | [`/tasks/{taskKey}`](#get-taskstaskkey) | getTaskDetail |  |  |
| POST | [`/documents/cancel`](#post-documentscancel) | cancelDocument |  |  |
| POST | [`/documents/convert`](#post-documentsconvert) | convertDocument |  |  |
| POST | [`/documents/create`](#post-documentscreate) | createDocumentWithoutBinary |  |  |
| POST | [`/documents/links/create`](#post-documentslinkscreate) | createLinks |  |  |
| GET | [`/documents/links/{linkToken}`](#get-documentslinkslinktoken) | getLinkedDocument |  |  |
| POST | [`/documents/previews/download`](#post-documentspreviewsdownload) | downloadMergeDocuments |  |  |
| POST | [`/documents/previews/merge`](#post-documentspreviewsmerge) | mergeDocuments |  |  |
| GET | [`/documents/previews/{previewId}`](#get-documentspreviewspreviewid) | getDocumentPagePreview |  |  |
| POST | [`/documents/register`](#post-documentsregister) | registerDocument |  |  |
| POST | [`/documents/restore`](#post-documentsrestore) | restoreDocumentVersion |  |  |
| GET | [`/documents/search`](#get-documentssearch) | searchDocuments |  |  |
| POST | [`/documents/search`](#post-documentssearch) | advanceSearchDocuments |  |  |
| GET | [`/documents/{documentId}`](#get-documentsdocumentid) | getDocumentMetadata |  |  |
| PATCH | [`/documents/{documentId}`](#patch-documentsdocumentid) | patchDocument |  |  |
| PUT | [`/documents/{documentId}`](#put-documentsdocumentid) | updateDocument |  |  |
| GET | [`/documents/{documentId}/content`](#get-documentsdocumentidcontent) | getDocumentContent |  |  |
| DELETE | [`/documents/{documentId}/delete`](#delete-documentsdocumentiddelete) | deleteDocument |  |  |
| POST | [`/documents/{documentId}/merge`](#post-documentsdocumentidmerge) | mergeToDocument |  |  |
| GET | [`/documents/{documentId}/previews/list`](#get-documentsdocumentidpreviewslist) | getPreviewList |  |  |
| PUT | [`/documents/{documentId}/register`](#put-documentsdocumentidregister) | putRegisterDocument |  |  |
| POST | [`/documents/{documentId}/subscribe`](#post-documentsdocumentidsubscribe) | postSubscribeApplication |  |  |
| POST | [`/documents/{documentId}/unsubscribe`](#post-documentsdocumentidunsubscribe) | postUnsubscribeAppliaction |  |  |
| POST | [`/agreement/marketing-consent`](#post-agreementmarketing-consent) | setAgreementMarketingConsent |  |  |
| DELETE | [`/agreements`](#delete-agreements) | deleteAgreement |  |  |
| GET | [`/agreements`](#get-agreements) | getAgreement |  |  |
| POST | [`/agreements`](#post-agreements) | createAgreement |  |  |
| PUT | [`/agreements`](#put-agreements) | updateAgreement |  |  |
| POST | [`/agreements/contract`](#post-agreementscontract) | uploadSignedContract |  |  |
| GET | [`/agreements/detail`](#get-agreementsdetail) | getAgreementDetail |  |  |
| POST | [`/agreements/document`](#post-agreementsdocument) | generateAgreementDocument |  |  |
| GET | [`/agreements/documents/content`](#get-agreementsdocumentscontent) | getDocumentContent |  |  |
| PATCH | [`/agreements/name`](#patch-agreementsname) | updateAgreementName |  |  |
| POST | [`/agreements/retry-creation`](#post-agreementsretry-creation) | retryAgreementCreation |  |  |
| GET | [`/agreements/validate-create`](#get-agreementsvalidate-create) | validateAndOptionallyCreateAgreement |  |  |
| POST | [`/agreements/verification-sms`](#post-agreementsverification-sms) | sendVerificationSms |  |  |
| GET | [`/contracts`](#get-contracts) | getFeeContracts |  |  |
| GET | [`/partners`](#get-partners) | getPartner |  |  |
| PATCH | [`/partners`](#patch-partners) | patchPartner |  |  |
| POST | [`/partners`](#post-partners) | savePartner |  |  |
| GET | [`/partners/consent`](#get-partnersconsent) | getGDPRConsent |  |  |
| POST | [`/partners/consent`](#post-partnersconsent) | saveGDPRConsent |  |  |
| DELETE | [`/partners/{partnerIdClientComponent}`](#delete-partnerspartneridclientcomponent) | rollbackPartner |  |  |
| PUT | [`/partners/{partnerIdClientComponent}/commit`](#put-partnerspartneridclientcomponentcommit) | commitPartner |  |  |
| GET | [`/users/token-data`](#get-userstoken-data) | getTokenData |  |  |
| POST | [`/check-duplicates-bank-account-ibans`](#post-check-duplicates-bank-account-ibans) | ibanDuplicityCheck |  |  |
| POST | [`/check-duplicates-bank-accounts`](#post-check-duplicates-bank-accounts) | bankAccountDuplicityCheck |  |  |
| POST | [`/check-duplicates-birth-numbers`](#post-check-duplicates-birth-numbers) | birthNumberDuplicityCheck |  |  |
| POST | [`/check-duplicates-contacts`](#post-check-duplicates-contacts) | contactDuplicityCheck |  |  |
| POST | [`/check-duplicates-identity-documents`](#post-check-duplicates-identity-documents) | documentIdentificationDuplicityCheck |  |  |
| POST | [`/check-duplicates-legal-entity-numbers`](#post-check-duplicates-legal-entity-numbers) | legalEntityNumberDuplicityCheck |  |  |
| POST | [`/check-duplicates-partners`](#post-check-duplicates-partners) | validatePartnerDuplicity |  |  |
| POST | [`/check-duplicates-tax-identification-numbers`](#post-check-duplicates-tax-identification-numbers) | dicIdentifierDuplicityCheck |  |  |
| POST | [`/validate-bank-account-ibans`](#post-validate-bank-account-ibans) | validateIbanIdentifier |  |  |
| POST | [`/validate-bank-accounts`](#post-validate-bank-accounts) | validateBankAccount |  |  |
| POST | [`/validate-birth-numbers`](#post-validate-birth-numbers) | validateBirthNumber |  |  |
| POST | [`/validate-contacts`](#post-validate-contacts) | validateContact |  |  |
| POST | [`/validate-ean-eics`](#post-validate-ean-eics) | validateEanEicIdentifier |  |  |
| POST | [`/validate-identity-documents`](#post-validate-identity-documents) | validateIdentityDocument |  |  |
| POST | [`/validate-legal-entity-numbers`](#post-validate-legal-entity-numbers) | validateLegalEntityNumber |  |  |
| POST | [`/validate-tax-identification-numbers`](#post-validate-tax-identification-numbers) | validateDicIdentifier |  |  |
| GET | [`/whisper-address`](#get-whisper-address) | whisperAddress |  |  |
| GET | [`/whisper-cadastral-territory`](#get-whisper-cadastral-territory) | whisperCadastralTerritory |  |  |
| GET | [`/whisper-city`](#get-whisper-city) | whisperCity |  |  |
| GET | [`/whisper-parcel-number`](#get-whisper-parcel-number) | whisperParcelNumber |  |  |
| GET | [`/whisper-partner-detail`](#get-whisper-partner-detail) | whisperPartnerDetail |  |  |
| GET | [`/whisper-street`](#get-whisper-street) | whisperStreet |  |  |
| GET | [`/whisper-zip-code`](#get-whisper-zip-code) | whisperZipCode |  |  |

## CPRCOLAIASSISTANTApi

### `PUT /ai-assistant/api/v1/keep-session/{sessionId}`

- Operation `keepSession` (CPRCOLAIASSISTANTApi; `3318.a53a48cb.js`)
- Path params: `sessionId`
- Response: empty (HTTP 200/204)

### `POST /ai-assistant/api/v1/message`

- Operation `sendMessage` (CPRCOLAIASSISTANTApi; `3318.a53a48cb.js`)
- Body (JSON `MessageRequestDto`):
  - `sessionId`
  - `context` (array)
  - `text`
  - `inputType`
- Response: JSON object:
  - `intents` (array)
  - `sessionId`
  - `audioText` (object)
  - `parrotAuthCode`
  - `messages` (array)
  - `actions` (array)
  - `node` (object)
  - `timeStamp`
  - `context` (array)
  - `elephantAuthCode`

### `POST /ai-assistant/api/v1/rating`

- Operation `sendRating` (CPRCOLAIASSISTANTApi; `3318.a53a48cb.js`)
- Body (JSON `RatingRequestDto`):
  - `text`
  - `stars`
  - `sessionId`
- Response: empty (HTTP 200/204)

### `POST /ai-assistant/api/v1/session`

- Operation `createSession` (CPRCOLAIASSISTANTApi; `3318.a53a48cb.js`)
- Body (JSON `CreateSessionRequestDto`):
  - `context` (array)
  - `type`
- Response: JSON object:
  - `intents` (array)
  - `sessionId`
  - `audioText` (object)
  - `parrotAuthCode`
  - `messages` (array)
  - `actions` (array)
  - `node` (object)
  - `timeStamp`
  - `context` (array)
  - `elephantAuthCode`

### `GET /ai-assistant/as/api/v1/webchat/{projectId}/{clientId}`

- Operation `getSettings` (CPRCOLAIASSISTANTApi; `3318.a53a48cb.js`)
- Path params: `projectId`, `clientId`
- Response: JSON object:
  - `mainColor`
  - `width`
  - `clientId`
  - `apiKey`
  - `avatar`
  - `muleUrl`
  - `secondColor`
  - `headerFontColor`
  - `height`
  - `projectId`
  - `keepSessionCount`
  - `fontColor`
  - `firstLoadingMessage`
  - `secondLoadingMessage`
  - `messageChars`
  - `smallAvatar`
  - `loadingImage`
  - `aiText`
  - `headerDescription`
  - `headerTitle`
  - `footerText`
  - `headerBackgroundImage`
  - `bubbleMessageTimer`
  - `bubbleMessageText`

### `GET /ai-assistant/availability`

- Operation `getAvailability` (CPRCOLAIASSISTANTApi; `3318.a53a48cb.js`)
- Response: JSON object:
  - `isAssistantAvailable`
  - `reason`

## CPRCOLAPPOINTMENTApi

### `GET /appointments`

- Operation `getCustomerAppointments` (CPRCOLAPPOINTMENTApi; `1568.4a0622a7.js`, `9187.f633fc06.js`)
- Response: JSON array of object

### `GET /appointments/search`

- Operation `getAppointmentsByTimeSlots` (CPRCOLAPPOINTMENTApi; `1568.4a0622a7.js`, `9187.f633fc06.js`)
- Query: `dateFrom`, `dateTo`
- Response: JSON array of object

### `DELETE /appointments/{appointmentId}`

- Operation `deleteAppointment` (CPRCOLAPPOINTMENTApi; `1568.4a0622a7.js`, `9187.f633fc06.js`)
- Path params: `appointmentId`
- Response: empty (HTTP 200/204)

### `GET /branches`

- Operation `getBranches` (CPRCOLAPPOINTMENTApi; `1568.4a0622a7.js`, `9187.f633fc06.js`)
- Response: JSON array of object

### `GET /branches/{branchId}/capacity`

- Operation `getGeneralCapacityForBranch` (CPRCOLAPPOINTMENTApi; `1568.4a0622a7.js`, `9187.f633fc06.js`)
- Path params: `branchId`
- Response: JSON array of object

### `GET /branches/{branchId}/services`

- Operation `getBranchServices` (CPRCOLAPPOINTMENTApi; `1568.4a0622a7.js`, `9187.f633fc06.js`)
- Path params: `branchId`
- Response: JSON array of object

### `GET /branches/{branchId}/services/{serviceId}/dates`

- Operation `getBranchDatesForServices` (CPRCOLAPPOINTMENTApi; `1568.4a0622a7.js`, `9187.f633fc06.js`)
- Path params: `branchId`, `serviceId`
- Response: JSON object

### `GET /branches/{branchId}/services/{serviceId}/dates/{date}/slots`

- Operation `getTheoreticalTimeSlots` (CPRCOLAPPOINTMENTApi; `1568.4a0622a7.js`, `9187.f633fc06.js`)
- Path params: `branchId`, `serviceId`, `date`
- Response: JSON object

### `GET /branches/{branchId}/services/{serviceId}/dates/{date}/times`

- Operation `getBranchTimeSlots` (CPRCOLAPPOINTMENTApi; `1568.4a0622a7.js`, `9187.f633fc06.js`)
- Path params: `branchId`, `serviceId`, `date`
- Response: JSON object

### `POST /branches/{branchId}/services/{serviceId}/dates/{date}/times/{time}`

- Operation `bookAppointment` (CPRCOLAPPOINTMENTApi; `1568.4a0622a7.js`, `9187.f633fc06.js`)
- Path params: `branchId`, `serviceId`, `date`, `time`
- Body (JSON `AppointmentDto`):
  - `custom`
  - `title`
  - `customers` (array)
  - `notes`
  - `ics`
- Response: JSON object

### `PUT /branches/{branchId}/services/{serviceId}/dates/{date}/times/{time}/{appointmentId}`

- Operation `updateAppointment` (CPRCOLAPPOINTMENTApi; `1568.4a0622a7.js`, `9187.f633fc06.js`)
- Path params: `branchId`, `serviceId`, `date`, `time`, `appointmentId`
- Response: JSON object

## CPRCOLCASEApi

### `POST /cases`

- Operation `getAllCases` (CPRCOLCASEApi; `5762.dc51a694.js`)
- Body (JSON `CaseFilterDto`):
  - `caseStatus`
  - `caseCreationDateFrom`
  - `caseCategories`
  - `caseCreationDateTo`
  - `caseClosureDateTo`
  - `caseClosureDateFrom`
  - `supplyPointCodes`
  - `colCaseServiceCategories`
  - `caseIdsCm`
- Response: JSON array of object

### `GET /cases/receive/channels`

- Operation `getListReceiveChannels` (CPRCOLCASEApi; `5762.dc51a694.js`)
- Response: JSON array of object

### `GET /cases/settings/{caseCategory}`

- Operation `getCaseSettings` (CPRCOLCASEApi; `5762.dc51a694.js`)
- Path params: `caseCategory`
- Response: JSON object:
  - `commodity`
  - `forCsv`
  - `hint`
  - `name`
  - `description`
  - `category`
  - `hideSupplyPoint`
  - `forSupplyPoint`
  - `forMobile`
  - `fileCount`
  - `id`
  - `contactType`
  - `attachmentRequired`
  - `fileTypes`
  - `maxFileSize`
  - `typeNumber`
  - `complaintCategories` (array)

### `GET /cases/tasks/{taskId}`

- Operation `getCaseTaskById` (CPRCOLCASEApi; `5762.dc51a694.js`)
- Path params: `taskId`
- Response: JSON object

### `POST /cases/tasks/{taskId}`

- Operation `updateCaseTask` (CPRCOLCASEApi; `5762.dc51a694.js`)
- Path params: `taskId`
- Body: `multipart/form-data` parts `updateCaseTaskData`, `files`
- Response: empty (HTTP 200/204)

### `POST /cases/{caseCategory}`

- Operation `createCase` (CPRCOLCASEApi; `5762.dc51a694.js`)
- Path params: `caseCategory`
- Body: `multipart/form-data` parts `files`, `createCaseData`
- Response: JSON object:
  - `id`
  - `guid`

### `GET /cases/{caseId}`

- Operation `getCaseById` (CPRCOLCASEApi; `5762.dc51a694.js`)
- Path params: `caseId`
- Response: JSON object

### `GET /cases/{caseId}/axis`

- Operation `getCaseAxis` (CPRCOLCASEApi; `5762.dc51a694.js`)
- Path params: `caseId`
- Response: JSON array of object

### `POST /cases/{caseId}/tasks`

- Operation `getAllCaseTasks` (CPRCOLCASEApi; `5762.dc51a694.js`)
- Path params: `caseId`
- Body (JSON `CaseTaskFilterDto`):
  - `taskCreateDateFrom` (date)
  - `taskClosureDateFrom` (date)
  - `taskCreateDateTo` (date)
  - `taskClosureDateTo` (date)
  - `taskCategory` (CodebookEntryIdentifierDto)
  - `taskCode` (CodebookEntryIdentifierDto)
  - `taskType` (CodebookEntryIdentifierDto)
  - `taskStatus` (CodebookEntryIdentifierDto)
  - `taskStatusDetail` (CodebookEntryIdentifierDto)
- Response: JSON array of object

### `GET /cases/{caseId}/tasks/{taskId}`

- Operation `getCaseTaskByIdAndCaseId` (CPRCOLCASEApi; `5762.dc51a694.js`)
- Path params: `caseId`, `taskId`
- Response: JSON object

### `GET /cases/{caseId}/tasks/{taskId}/events`

- Operation `getAllCaseTaskEvents` (CPRCOLCASEApi; `5762.dc51a694.js`)
- Path params: `caseId`, `taskId`
- Response: JSON array of object

## CPRCOLCODEBOOKApi

### `GET /codebooks/{codebookId}`

- Operation `getCodebook` (CPRCOLCODEBOOKApi; `7204.150f0da0.js`, `8794.01f0afd3.js`)
- Path params: `codebookId`
- Query: `systemId`
- Response: JSON object:
  - `codebookId`
  - `entries` (CodebookEntryDto[])

## CPRCOLCOMPLAINTApi

### `POST /complaints`

- Operation `createComplaint` (CPRCOLCOMPLAINTApi; `32.9db2876c.js`, `7651.a316dd93.js`)
- Body: `multipart/form-data` parts `file`, `createComplaintRequest`
- Response: JSON object:
  - `caseGuidCrm`
  - `caseIdCrm`

### `GET /complaints/customization`

- Operation `getComplaintFormCustomization` (CPRCOLCOMPLAINTApi; `32.9db2876c.js`, `7651.a316dd93.js`)
- Response: JSON object:
  - `serviceOptions` (array)
  - `supplyPointFilters` (array)
  - `complaintItems` (array)
  - `complaintDomains` (array)
  - `commodityFilters` (array)

### `GET /complaints/step/{categoryIds}`

- Operation `getNextComplaintStep` (CPRCOLCOMPLAINTApi; `32.9db2876c.js`, `7651.a316dd93.js`)
- Path params: `categoryIds`
- Query: `isSupplyPointSelected`, `showServicePage`
- Response: JSON object:
  - `receivingChannels` (array)
  - `pageTitle`
  - `pageId`
  - `categories` (array)
  - `commodity`
  - `complaintProductCategories` (array)
  - `complaintCrmType`
  - `caseReason` (CodebookEntryDto[])

## CPRCOLCUSTOMERCENTERApi (anonymous API, `REACT_APP_ANONYMOUS_API_URL`)

### `GET /customer-centers/allV2`

- Operation `getAllCustomerCentersV2` (CPRCOLCUSTOMERCENTERApi; `1942.b7c52211.js`, `9561.0db23c53.js`)
- Response: JSON array of object

## CPRCOLDWHREPORTINGApi

### `GET /reporting/op`

- Operation `getOpActivityLog` (CPRCOLDWHREPORTINGApi; `1783.eee9362b.js`, `4164.fb7290f1.js`)
- Query: `from`, `to`, `op`
- Response: JSON object:
  - `data` (array)

### `GET /reporting/simu-user`

- Operation `getSimuUserActivityLog` (CPRCOLDWHREPORTINGApi; `1783.eee9362b.js`, `4164.fb7290f1.js`)
- Query: `from`, `to`, `simu-user`
- Response: JSON object:
  - `data` (array)

### `GET /reporting/user`

- Operation `getUserActivityLog` (CPRCOLDWHREPORTINGApi; `1783.eee9362b.js`, `4164.fb7290f1.js`)
- Query: `to`, `from`, `user`
- Response: JSON object:
  - `data` (array)

## CPRCOLFEEDBACKApi

### `POST /feedback`

- Operation `setFeedback` (CPRCOLFEEDBACKApi; `3339.8a516150.js`, `5720.83cf6cc8.js`)
- Body (JSON `SetFeedbackRequestDto`):
  - `Evaluation` (object)
- Response: empty (HTTP 200/204)

### `POST /feedback/app-check`

- Operation `getFeedbackAppCheck` (CPRCOLFEEDBACKApi; `3339.8a516150.js`, `5720.83cf6cc8.js`)
- Body (JSON `ShowCheckRequestDto`):
  - `activityId`
  - `appId`
- Response: JSON object:
  - `showFeedback`

### `GET /feedback/check`

- Operation `getFeedbackCheck` (CPRCOLFEEDBACKApi; `3339.8a516150.js`, `5720.83cf6cc8.js`)
- Response: JSON object:
  - `cxResearch`
  - `gdpr`
  - `alert`

### `GET /feedback/configuration/{questionnaireId}`

- Operation `getFeedbackConfiguration` (CPRCOLFEEDBACKApi; `3339.8a516150.js`, `5720.83cf6cc8.js`)
- Path params: `questionnaireId`
- Response: JSON object:
  - `questionnaireFinalText`
  - `questions` (array)
  - `questionnaireId`
  - `questionnaireName`
  - `questionnaireDescription`

## CPRCOLFORMSApi

### `POST /forms/ais-code`

- Operation `setAisCode` (CPRCOLFORMSApi; `2165.d6fd4614.js`, `4546.0373d963.js`)
- Body (JSON `SetAisCodeRequestBodyDto`):
  - `aisCode`
  - `businessCaseId`
- Response: JSON object:
  - `caseIdCrm`
  - `caseGuidCrm`

### `GET /forms/bank-accounts`

- Operation `getBankAccounts` (CPRCOLFORMSApi; `2165.d6fd4614.js`, `4546.0373d963.js`)
- Response: JSON object:
  - `bankAccounts`

### `POST /forms/payment-complaint`

- Operation `createPaymentComplaint` (CPRCOLFORMSApi; `2165.d6fd4614.js`, `4546.0373d963.js`)
- Body: `multipart/form-data` parts `createPaymentComplaintRequestBody`, `attachments`
- Response: JSON object:
  - `activityId`

## CPRCOLHEATINGSERVICEApi

### `POST /heating-service/all`

- Operation `getHeatingServiceContracts` (CPRCOLHEATINGSERVICEApi; `9292.734438f6.js`)
- Query: `includeAllHeatingServices`, `contractIdCrm`
- Body (JSON `HeatingServiceRequestTypesDto`):
  - `types`
- Response: JSON object:
  - `heatingServiceItem` (array)
  - `heatingServiceAddressGroup` (array)

### `POST /heating-service/request/confirm`

- Operation `confirmHeatingServiceRequirement` (CPRCOLHEATINGSERVICEApi; `9292.734438f6.js`)
- Body (JSON `ConfirmHeatingServiceReqestBodyDto`):
  - `serviceHeatingRequestOrderGuid`
  - `contractIdCrm`
  - `note`
- Response: empty (HTTP 200/204)

### `POST /heating-service/request/confirm-callback`

- Operation `confirmServiceRequestCallback` (CPRCOLHEATINGSERVICEApi; `9292.734438f6.js`)
- Query: `authorizationId`, `authorizationCode`
- Response: empty (HTTP 200/204)

### `GET /heating-service/request/free-terms`

- Operation `getFreeTerms` (CPRCOLHEATINGSERVICEApi; `9292.734438f6.js`)
- Query: `contractIdCrm`
- Response: JSON array of object

### `POST /heating-service/request/reject`

- Operation `rejectHeatingServiceRequirement` (CPRCOLHEATINGSERVICEApi; `9292.734438f6.js`)
- Body (JSON `RejectHeatingServiceRequestBodyDto`):
  - `serviceHeatingRequestOrderGuid`
  - `contractIdCrm`
  - `postponedDate` (date (YYYY-MM-DD))
- Response: empty (HTTP 200/204)

## CPRCOLINAPPEVALUATIONApi

### `POST /save-app-evaluation`

- Operation `saveAppEvaluation` (CPRCOLINAPPEVALUATIONApi; `1953.2ae88055.js`, `4334.c010f615.js`)
- Body (JSON `InAppEvaluationRequestBodyDto`):
  - `InAppEvaluationId`
  - `InAppEvaluationFeedback`
  - `InAppEvaluationVersion`
  - `InAppEvaluationPlatform`
  - `InAppEvaluationPage`
- Response: empty (HTTP 200/204)

## CPRCOLLEADApi

### `POST /leads`

- Operation `createLead` (CPRCOLLEADApi; `3408.152c76ee.js`, `8646.7f4433a1.js`)
- Body (JSON `CreateLeadRequestDto`):
  - `opportunityStatus` (CodebookEntryIdentifierDto)
  - `attributes` (array)
  - `noteContent`
  - `opportunityDescription`
  - `opportunityPhone1`
  - `opportunityProduct` (CodebookEntryIdentifierDto)
  - `opportunityActionType` (CodebookEntryIdentifierDto)
- Response: JSON object:
  - `opportunityGuidCrm`
  - `opportunityIdCrm`

## CPRCOLLOGISTICSPARTNERApi

### `POST /logistics-partner/history`

- Operation `getHistory` (CPRCOLLOGISTICSPARTNERApi; `6739.7218f48d.js`, `9120.134d5ce5.js`)
- Body (JSON `LogisticsPartnerHistoryFilterDto`):
  - `simSerialNumber`
  - `from` (date (YYYY-MM-DD))
  - `to` (date (YYYY-MM-DD))
  - `offerIdCrm`
- Response: JSON array of object:
  - `offerGuidCrm`
  - `offerIdCrm`
  - `offerCreatedDate` (date)
  - `offerMvnoDelivery` (CodebookEntryDto)

### `DELETE /logistics-partner/lock`

- Operation `releaseLock` (CPRCOLLOGISTICSPARTNERApi; `6739.7218f48d.js`, `9120.134d5ce5.js`)
- Query: `offerGuidCrm`
- Response: empty (HTTP 200/204)

### `POST /logistics-partner/lock`

- Operation `createLock` (CPRCOLLOGISTICSPARTNERApi; `6739.7218f48d.js`, `9120.134d5ce5.js`)
- Query: `offerGuidCrm`
- Response: empty (HTTP 200/204)

### `PUT /logistics-partner/lock`

- Operation `prolongateLock` (CPRCOLLOGISTICSPARTNERApi; `6739.7218f48d.js`, `9120.134d5ce5.js`)
- Query: `offerGuidCrm`
- Response: empty (HTTP 200/204)

### `POST /logistics-partner/sim`

- Operation `setSIM` (CPRCOLLOGISTICSPARTNERApi; `6739.7218f48d.js`, `9120.134d5ce5.js`)
- Body (JSON `SimInputDataDto`):
  - `offerGuidCrm`
  - `groupPartnerId`
  - `simSerialNumber`
  - `imei`
  - `sn`
- Response: empty (HTTP 200/204)

### `GET /logistics-partner/unprocessed`

- Operation `getAllUnprocessed` (CPRCOLLOGISTICSPARTNERApi; `6739.7218f48d.js`, `9120.134d5ce5.js`)
- Response: JSON array of object:
  - `offerCreatedDate` (date)
  - `offerGuidCrm`
  - `offerIdCrm`
  - `offerMvnoDelivery` (CodebookEntryDto)
  - `groupPartnerId`
  - `offerMvnoAcquisitionReason` (CodebookEntryDto)
  - `gift`
  - `locked`
  - `group`
  - `typeOfHw`
  - `esim`

## CPRCOLMVNOACTIVATIONSApi

### `POST /mvno-activations/activate-sim`

- Operation `activateSim` (CPRCOLMVNOACTIVATIONSApi; `7457.79eecaf4.js`, `9838.e70bb0fe.js`)
- Response: empty (HTTP 200/204)

### `GET /mvno-activations/activation-data/{orderGuid}`

- Operation `getActivationData` (CPRCOLMVNOACTIVATIONSApi; `7457.79eecaf4.js`, `9838.e70bb0fe.js`)
- Path params: `orderGuid`
- Response: JSON object

### `GET /mvno-activations/portin-data/{orderGuid}`

- Operation `getPortinData` (CPRCOLMVNOACTIVATIONSApi; `7457.79eecaf4.js`, `9838.e70bb0fe.js`)
- Path params: `orderGuid`
- Response: JSON object

### `GET /mvno-activations/portin-dates`

- Operation `getAvailablePortInDates` (CPRCOLMVNOACTIVATIONSApi; `7457.79eecaf4.js`, `9838.e70bb0fe.js`)
- Query: `phoneNumber`, `portInCode`
- Response: JSON object

### `POST /mvno-activations/portin-sim`

- Operation `portinSim` (CPRCOLMVNOACTIVATIONSApi; `7457.79eecaf4.js`, `9838.e70bb0fe.js`)
- Response: empty (HTTP 200/204)

## CPRCOLMVNOApi

### `GET /mvno/add-benefited-phone-number`

- Operation `addBenefitedPhoneNumber` (CPRCOLMVNOApi; `5023.33abdeb2.js`)
- Query: `phoneNumber`
- Response: JSON object

### `GET /mvno/benefited-phone-numbers`

- Operation `getBenefitedPhoneNumbers` (CPRCOLMVNOApi; `5023.33abdeb2.js`)
- Response: JSON array of object:
  - `phoneNumber`
  - `benefitValidFrom` (date)

### `POST /mvno/block-sim`

- Operation `blockSimCard` (CPRCOLMVNOApi; `5023.33abdeb2.js`)
- Query: `phoneNumber`
- Response: empty (HTTP 200/204)

### `GET /mvno/cache`

- Operation `createMvnoCache` (CPRCOLMVNOApi; `5023.33abdeb2.js`)
- Response: empty (HTTP 200/204)

### `GET /mvno/check-mobile-device`

- Operation `checkMobileDevice` (CPRCOLMVNOApi; `5023.33abdeb2.js`)
- Query: `phoneNumber`
- Response: JSON object:
  - `benefitedFrom` (date)
  - `selected`
  - `statusText`
  - `canBeDeleted`
  - `firstName`
  - `lastName`
  - `simNumber`
  - `status`
  - `contractNumber`
  - `hwInfo` (object)
  - `header`
  - `currency`
  - `lastAmountSpent`
  - `note`
  - `benefited`
  - `phone`
  - `guid`

### `GET /mvno/contract`

- Operation `getMobileContractsFileId` (CPRCOLMVNOApi; `5023.33abdeb2.js`)
- Query: `phoneNumber`
- Response: JSON object:
  - `fileId`

### `GET /mvno/current-usage`

- Operation `getCurrentUsage` (CPRCOLMVNOApi; `5023.33abdeb2.js`)
- Query: `phoneNumber`
- Response: JSON object:
  - `spent`
  - `usage` (array)

### `GET /mvno/customer-cookie`

- Operation `getCustomerCookie` (CPRCOLMVNOApi; `5023.33abdeb2.js`)
- Query: `phoneNumber`
- Response: empty (HTTP 200/204)

### `GET /mvno/employee-tokens`

- Operation `getEmployeeTokens` (CPRCOLMVNOApi; `5023.33abdeb2.js`)
- Response: JSON array of object:
  - `zameTokenToken`
  - `zameTokenStatus`
  - `zameTokenType`
  - `zameTokenNumber`
  - `zameTokenValidTo` (date)
  - `zameTokenExtId`
  - `zameTokenDescription`

### `GET /mvno/get-title`

- Operation `getTitle` (CPRCOLMVNOApi; `5023.33abdeb2.js`)
- Query: `phoneNumber`
- Response: JSON object:
  - `title`

### `GET /mvno/history-usage`

- Operation `getHistoryUsage` (CPRCOLMVNOApi; `5023.33abdeb2.js`)
- Query: `phoneNumber`, `pageNumber`
- Response: JSON object:
  - `count`
  - `callDetails` (array)

### `GET /mvno/history-usage-csv`

- Operation `getHistoryUsageCsv` (CPRCOLMVNOApi; `5023.33abdeb2.js`)
- Query: `phoneNumber`, `count`
- Response: JSON object:
  - `fileId`

### `GET /mvno/history/{phoneNumber}/{pageNr}`

- Operation `getHistory` (CPRCOLMVNOApi; `5023.33abdeb2.js`)
- Path params: `phoneNumber`, `pageNr`
- Response: JSON object:
  - `mvnoHistoryDay` (array)
  - `resultAmount`

### `GET /mvno/list`

- Operation `readMobileContracts` (CPRCOLMVNOApi; `5023.33abdeb2.js`)
- Query: `isZame`
- Response: JSON array of object:
  - `lastSpent`
  - `telcoOverviewNextBillingPeriodTo` (date)
  - `mobileContractName`
  - `mobileContractPhoneNumber`
  - `telcoContractState`
  - `agreementIdIsu`
  - `supplyPointCommodity` (CodebookEntryDto)

### `POST /mvno/modify-package/{phoneNumber}`

- Operation `modifyMvnoPackage` (CPRCOLMVNOApi; `5023.33abdeb2.js`)
- Path params: `phoneNumber`
- Body (JSON `ModifyPackageRequestBodyDto`):
  - `productId`
  - `productCode`
  - `value1`
  - `email`
  - `value2`
  - `receivingChannel`
- Response: JSON object:
  - `activityId`

### `GET /mvno/oku`

- Operation `getOkuSecurityCode` (CPRCOLMVNOApi; `5023.33abdeb2.js`)
- Query: `phoneNumber`
- Response: JSON object:
  - `okuSecurityCode`
  - `activityRecordId`

### `GET /mvno/payment-history`

- Operation `getPaymentHistory` (CPRCOLMVNOApi; `5023.33abdeb2.js`)
- Query: `dateTo`, `dateFrom`, `phoneNumber`
- Response: JSON array of object:
  - `dateFrom` (date)
  - `dateTo` (date)
  - `phoneNumber`
  - `accountingDocumentNumber`
  - `numbersOrder`
  - `amount`
  - `amountTotal`

### `GET /mvno/payment-progress`

- Operation `getPaymentProgress` (CPRCOLMVNOApi; `5023.33abdeb2.js`)
- Query: `dateTo`, `phoneNumber`, `dateFrom`
- Response: JSON array of object:
  - `dateFrom` (date)
  - `callsAmount`
  - `dateTo` (date)
  - `accountingDocumentNumber`
  - `phoneNumber`
  - `callsCount`
  - `smsCount`
  - `internetDataCount`
  - `smsAmount`
  - `internetDataAmount`
  - `phoneNumberAmount`
  - `invoiceAmount`

### `GET /mvno/products/{phoneNumber}`

- Operation `getRelatedProducts` (CPRCOLMVNOApi; `5023.33abdeb2.js`)
- Path params: `phoneNumber`
- Query: `o2GroupId`, `isMultiStep`
- Response: JSON object:
  - `categoryId`
  - `caption` (object)
  - `relatedCategories` (array)
  - `name`
  - `groups` (array)
  - `steps` (array)
  - `submitLabel`

### `GET /mvno/puk`

- Operation `getPukSecurityCode` (CPRCOLMVNOApi; `5023.33abdeb2.js`)
- Query: `phoneNumber`
- Response: JSON object:
  - `puk1`

### `GET /mvno/remove-benfited-phone-number`

- Operation `removeBenefitedPhoneNumber` (CPRCOLMVNOApi; `5023.33abdeb2.js`)
- Query: `phoneNumber`
- Response: JSON object

### `POST /mvno/send-employee-token`

- Operation `sendEmployeeToken` (CPRCOLMVNOApi; `5023.33abdeb2.js`)
- Body (JSON `SendEmployeeTokenRequestDto`):
  - `email`
  - `extId`
  - `description`
  - `phoneNumber`
- Response: JSON object

### `POST /mvno/service-activate`

- Operation `activatePackage` (CPRCOLMVNOApi; `5023.33abdeb2.js`)
- Query: `phoneNumber`
- Body (JSON `O2PackageDto`):
  - `actionView`
  - `productCategory`
  - `productGroup`
  - `productId`
  - `previousProductId`
  - `sequenceNumber`
  - `productCode`
  - `actionModify`
  - `actionActivation`
  - `actionDeactivation`
  - `productIndependent`
  - `linkedProductId`
  - `amount`
  - `productPackName`
  - `productPackDescription`
  - `tooltipActivation`
  - `tooltipDeactivation`
  - `currency`
- Response: empty (HTTP 200/204)

### `POST /mvno/service-deactivate`

- Operation `deactivatePackage` (CPRCOLMVNOApi; `5023.33abdeb2.js`)
- Query: `phoneNumber`
- Body (JSON `O2PackageDto`):
  - `actionView`
  - `productCategory`
  - `productGroup`
  - `productId`
  - `previousProductId`
  - `sequenceNumber`
  - `productCode`
  - `actionModify`
  - `actionActivation`
  - `actionDeactivation`
  - `productIndependent`
  - `linkedProductId`
  - `amount`
  - `productPackName`
  - `productPackDescription`
  - `tooltipActivation`
  - `tooltipDeactivation`
  - `currency`
- Response: empty (HTTP 200/204)

### `GET /mvno/service-settings`

- Operation `getServicesSettings` (CPRCOLMVNOApi; `5023.33abdeb2.js`)
- Query: `phoneNumber`
- Response: JSON object:
  - `packages` (array)
  - `categories` (array)
  - `groups` (array)
  - `subscription` (object)

### `POST /mvno/service-settings-change`

- Operation `changePackage` (CPRCOLMVNOApi; `5023.33abdeb2.js`)
- Query: `phoneNumber`, `value1`, `value2`
- Body (JSON `O2PackageDto`):
  - `actionView`
  - `productCategory`
  - `productGroup`
  - `productId`
  - `previousProductId`
  - `sequenceNumber`
  - `productCode`
  - `actionModify`
  - `actionActivation`
  - `actionDeactivation`
  - `productIndependent`
  - `linkedProductId`
  - `amount`
  - `productPackName`
  - `productPackDescription`
  - `tooltipActivation`
  - `tooltipDeactivation`
  - `currency`
- Response: empty (HTTP 200/204)

### `POST /mvno/set-title`

- Operation `setTitle` (CPRCOLMVNOApi; `5023.33abdeb2.js`)
- Query: `note`, `phoneNumber`
- Response: JSON object:
  - `activityId`

### `POST /mvno/set-token-description`

- Operation `setTokenDescription` (CPRCOLMVNOApi; `5023.33abdeb2.js`)
- Body (JSON `SetTokenDescriptionRequestDto`):
  - `extId`
  - `text`
- Response: empty (HTTP 200/204)

### `GET /mvno/tariff-settings/{phoneNumber}`

- Operation `getMvnoTariffSettings` (CPRCOLMVNOApi; `5023.33abdeb2.js`)
- Path params: `phoneNumber`
- Response: JSON object:
  - `audioText` (object)
  - `infoLimit` (object)
  - `roaming` (object)
  - `premiumSmsDms` (object)
  - `dataAccess` (object)
  - `roamingDataBlockWorld` (object)
  - `roamingDataBlockEu` (object)

### `GET /mvno/units-history/{phoneNumber}`

- Operation `getMvnoUnitsHistory` (CPRCOLMVNOApi; `5023.33abdeb2.js`)
- Path params: `phoneNumber`
- Response: JSON object:
  - `mvnoPrevious` (object)
  - `mvnoCurrent` (object)

### `GET /mvno/{phoneNumber}`

- Operation `getDetail` (CPRCOLMVNOApi; `5023.33abdeb2.js`)
- Path params: `phoneNumber`
- Response: JSON object:
  - `isTariff`
  - `o2GroupId`
  - `phoneTitle`
  - `isActive`
  - `actualTotalSpend`
  - `tariffTotalPrice`
  - `tariffTypes` (array)
  - `isZame`
  - `isVpnCallFree`
  - `phoneDevice` (object)
  - `tariffStatement` (object)
  - `lastUpdate` (date)
  - `currentServiceStatus`
  - `agreementIdIsu`
  - `extraTariffTypes` (array)
  - `isEsim`

## CPRCOLNSSERVICESApi

### `GET /ns-services`

- Operation `getNsServices` (CPRCOLNSSERVICESApi; `2194.4d7762cf.js`, `9813.fcd26608.js`)
- Response: JSON array of object

### `GET /ns-services/{idOpLeo}/documents/{idLeo7Documents}`

- Operation `getNsDocument` (CPRCOLNSSERVICESApi; `2194.4d7762cf.js`, `9813.fcd26608.js`)
- Path params: `idOpLeo`, `idLeo7Documents`
- Response: binary file (blob)

### `GET /ns-services/{id}`

- Operation `getNsDetail` (CPRCOLNSSERVICESApi; `2194.4d7762cf.js`, `9813.fcd26608.js`)
- Path params: `id`
- Response: JSON object:
  - `documents` (array)
  - `categories` (array)
  - `infos` (array)
  - `processes` (array)

## CPRCOLO2Api

### `GET /o2/calls`

- Operation `getCalls` (CPRCOLO2Api; `2114.67566b2e.js`, `9733.96b5b8df.js`)
- Query: `phoneNumber`, `pageNr`, `count`
- Response: JSON object:
  - `count`
  - `callDetails` (array)

### `PUT /o2/order`

- Operation `putOrder` (CPRCOLO2Api; `2114.67566b2e.js`, `9733.96b5b8df.js`)
- Query: `phoneNumber`
- Body (JSON `PutOrderRequestBodyDto`):
  - `jsonRequestBody`
- Response: empty (HTTP 200/204)

### `POST /o2/postStatus`

- Operation `postStatus` (CPRCOLO2Api; `2114.67566b2e.js`, `9733.96b5b8df.js`)
- Query: `phoneNumber`, `suspend`
- Response: empty (HTTP 200/204)

### `GET /o2/sim`

- Operation `getSim` (CPRCOLO2Api; `2114.67566b2e.js`, `9733.96b5b8df.js`)
- Query: `phoneNumber`
- Response: JSON object:
  - `msisdn`
  - `puk1`
  - `imsi`
  - `icc`

### `GET /o2/spent`

- Operation `getSpent` (CPRCOLO2Api; `2114.67566b2e.js`, `9733.96b5b8df.js`)
- Query: `phoneNumber`
- Response: text

### `GET /o2/statement`

- Operation `getCurrentStatement` (CPRCOLO2Api; `2114.67566b2e.js`, `9733.96b5b8df.js`)
- Query: `phoneNumber`
- Response: JSON object:
  - `totalSum`
  - `dueDate` (date)
  - `ProductInfo` (array)

### `GET /o2/subscription`

- Operation `getSubscription` (CPRCOLO2Api; `2114.67566b2e.js`, `9733.96b5b8df.js`)
- Query: `phoneNumber`
- Response: JSON object:
  - `paymentTypeId`
  - `mobileContractNumber`
  - `telcoOverviewBillingPeriodFrom` (date)
  - `externId`
  - `msisdn`
  - `telcoOverviewBillingPeriodTo` (date)
  - `mobileContractState`
  - `language`
  - `products` (array)
  - `parameters` (array)

### `GET /o2/units-history/{phoneNumber}`

- Operation `getUnitsHistory` (CPRCOLO2Api; `2114.67566b2e.js`, `9733.96b5b8df.js`)
- Path params: `phoneNumber`
- Response: JSON object:
  - `previous` (object)
  - `current` (object)

### `GET /o2/usages`

- Operation `getUsages` (CPRCOLO2Api; `2114.67566b2e.js`, `9733.96b5b8df.js`)
- Query: `phoneNumber`
- Response: JSON array of object

## CPRCOLREDACTIONApi

### `POST /redaction/attachment/{itemId}`

- Operation `attachFile` (CPRCOLREDACTIONApi; `1479.4b3b9e76.js`, `3860.b2cbbed4.js`)
- Path params: `itemId`
- Body: `multipart/form-data` parts `content`
- Response: empty (HTTP 200/204)

### `GET /redaction/categories`

- Operation `getCategories` (CPRCOLREDACTIONApi; `1479.4b3b9e76.js`, `3860.b2cbbed4.js`)
- Response: JSON array of object

### `POST /redaction/categories/hierarchy`

- Operation `createHierarchy` (CPRCOLREDACTIONApi; `1479.4b3b9e76.js`, `3860.b2cbbed4.js`)
- Body (JSON `CreateHierarchyDataDto`):
  - `prioritized`
  - `state`
  - `itemParentId`
  - `itemCategoryId`
  - `itemPath`
  - `onMobile`
  - `application`
  - `variant`
  - `buttonVisible`
  - `buttonUrl`
  - `buttonText`
- Response: text

### `POST /redaction/categories/hierarchy/text`

- Operation `getText` (CPRCOLREDACTIONApi; `1479.4b3b9e76.js`, `3860.b2cbbed4.js`)
- Body (JSON `TextFilterDto`):
  - `textId`
  - `textItemId`
  - `application`
- Response: JSON array of object

### `POST /redaction/categories/hierarchy/texts`

- Operation `createText` (CPRCOLREDACTIONApi; `1479.4b3b9e76.js`, `3860.b2cbbed4.js`)
- Body (JSON `CreateTextDataDto`):
  - `textItemId`
  - `textContent`
  - `textTitle`
- Response: empty (HTTP 200/204)

### `PUT /redaction/categories/hierarchy/texts/{textId}`

- Operation `updateText` (CPRCOLREDACTIONApi; `1479.4b3b9e76.js`, `3860.b2cbbed4.js`)
- Path params: `textId`
- Body (JSON `UpdateTextInputDto`):
  - `textItemId`
  - `textContent`
  - `textTitle`
- Response: empty (HTTP 200/204)

### `DELETE /redaction/categories/hierarchy/texts/{textItemId}`

- Operation `deleteText` (CPRCOLREDACTIONApi; `1479.4b3b9e76.js`, `3860.b2cbbed4.js`)
- Path params: `textItemId`
- Response: empty (HTTP 200/204)

### `DELETE /redaction/categories/hierarchy/{itemId}`

- Operation `deleteHierarchy` (CPRCOLREDACTIONApi; `1479.4b3b9e76.js`, `3860.b2cbbed4.js`)
- Path params: `itemId`
- Response: empty (HTTP 200/204)

### `PUT /redaction/categories/hierarchy/{itemId}`

- Operation `updateHierarchy` (CPRCOLREDACTIONApi; `1479.4b3b9e76.js`, `3860.b2cbbed4.js`)
- Path params: `itemId`
- Body (JSON `UpdateHierarchyInputDto`):
  - `prioritized`
  - `state`
  - `itemParentId`
  - `itemPath`
  - `itemCategoryId`
  - `onMobile`
  - `application`
  - `buttonUrl`
  - `variant`
  - `buttonText`
  - `buttonVisible`
- Response: empty (HTTP 200/204)

### `GET /redaction/categories/{categoryId}/hierarchy`

- Operation `getHierarchyByCategory` (CPRCOLREDACTIONApi; `1479.4b3b9e76.js`, `3860.b2cbbed4.js`)
- Path params: `categoryId`
- Response: JSON array of object

### `GET /redaction/file`

- Operation `getHierarchyFile` (CPRCOLREDACTIONApi; `1479.4b3b9e76.js`, `3860.b2cbbed4.js`)
- Query: `guid`
- Response: binary file (blob)

### `GET /redaction/file-info`

- Operation `getHierarchyFilesGuidParam` (CPRCOLREDACTIONApi; `1479.4b3b9e76.js`, `3860.b2cbbed4.js`)
- Query: `itemId`, `application`
- Response: JSON array of object

### `DELETE /redaction/{guid}`

- Operation `deleteFile` (CPRCOLREDACTIONApi; `1479.4b3b9e76.js`, `3860.b2cbbed4.js`)
- Path params: `guid`
- Response: empty (HTTP 200/204)

## CPRDAFBPMApi (base URL `REACT_APP_CAMUNDA_API_URL`)

### `POST /bpm/start-process`

- Operation `startProcess` (CPRDAFBPMApi; `4681.e9aadb03.js`)
- Body (JSON `ProcessStartRequestDto`):
  - `processKind` (CodebookEntryIdentifierDto)
  - `technicalProcessData` (array)
  - `processType` (CodebookEntryIdentifierDto)
  - `processServiceCategory` (CodebookEntryIdentifierDto)
- Response: JSON object:
  - `caseIdCm`
  - `targetUrl`

### `POST /bpm/{caseIdCm}/cancel`

- Operation `cancelCase` (CPRDAFBPMApi; `4681.e9aadb03.js`)
- Path params: `caseIdCm`
- Body (JSON `CancelCaseRequestDto`):
  - `processCancellationReason` (CodebookEntryIdentifierDto)
- Response: empty (HTTP 200/204)

### `POST /bpm/{caseIdCm}/close`

- Operation `closeProcess` (CPRDAFBPMApi; `4681.e9aadb03.js`)
- Path params: `caseIdCm`
- Response: empty (HTTP 200/204)

### `POST /bpm/{caseIdCm}/complete-current-step`

- Operation `completeCurrentStep` (CPRDAFBPMApi; `4681.e9aadb03.js`)
- Path params: `caseIdCm`
- Body (JSON `CompleteCurrentStepRequestDto`):
  - `processServiceCategory` (CodebookEntryIdentifierDto)
  - `technicalProcessData` (array)
  - `processType` (CodebookEntryIdentifierDto)
  - `processKind` (CodebookEntryIdentifierDto)
  - `processActualProcessStepKind` (CodebookEntryIdentifierDto)
- Response: JSON object:
  - `virtualProperty`

### `POST /bpm/{caseIdCm}/create-process-event`

- Operation `createProcessEvent` (CPRDAFBPMApi; `4681.e9aadb03.js`)
- Path params: `caseIdCm`
- Body (JSON `CreateProcessEventRequestDto`):
  - `eventType` (CodebookEntryIdentifierDto)
  - `processData` (array)
- Response: empty (HTTP 200/204)

### `GET /bpm/{caseIdCm}/current-step-detail`

- Operation `getCurrentStepDetail` (CPRDAFBPMApi; `4681.e9aadb03.js`)
- Path params: `caseIdCm`
- Response: JSON object:
  - `canStepBack`
  - `processKind` (CodebookEntryDto)
  - `processServiceCategory` (CodebookEntryDto)
  - `temporaryData`
  - `technicalProcessData` (array)
  - `canStepForward`
  - `fieldRules` (array)
  - `processType` (CodebookEntryDto)
  - `processStatus` (CodebookEntryDto)
  - `processActualProcessStepKind` (CodebookEntryDto)
  - `processErrors` (array)
  - `assignee` (object)

### `POST /bpm/{caseIdCm}/partial-save`

- Operation `partialSave` (CPRDAFBPMApi; `4681.e9aadb03.js`)
- Path params: `caseIdCm`
- Body (JSON `PartialDataSaveRequestDto`):
  - `temporaryData`
  - `variables` (array)
- Response: empty (HTTP 200/204)

### `POST /bpm/{caseIdCm}/step-back`

- Operation `stepBack` (CPRDAFBPMApi; `4681.e9aadb03.js`)
- Path params: `caseIdCm`
- Body (JSON `StepBackRequestDto`):
  - `processActualProcessStepKind` (CodebookEntryIdentifierDto)
  - `technicalProcessData` (array)
- Response: empty (HTTP 200/204)

### `POST /bpm/{caseIdCm}/take-over-step`

- Operation `takeOverStep` (CPRDAFBPMApi; `4681.e9aadb03.js`)
- Path params: `caseIdCm`
- Body (JSON `TakeOverStepRequestDto`):
  - `processActualProcessStepKind` (CodebookEntryIdentifierDto)
- Response: empty (HTTP 200/204)

## CPRDETAILCASEApi (base URL `REACT_APP_DOC_CASE_API_URL`)

### `GET /cases/documents/{caseKey}`

- Operation `getCaseDocuments` (CPRDETAILCASEApi; `7794.5a468305.js`)
- Path params: `caseKey`
- Response: JSON object:
  - `documents` (array)

### `GET /cases/permissions`

- Operation `getPermissions` (CPRDETAILCASEApi; `7794.5a468305.js`)
- Response: JSON array of object

### `GET /cases/statusFlow/{processIdCm}`

- Operation `getStatusFlow` (CPRDETAILCASEApi; `7794.5a468305.js`)
- Path params: `processIdCm`
- Query: `assistMode`
- Response: JSON object:
  - `processStatusAxisLabel`
  - `processStatusAxis` (object)
  - `showReturnedMessage`

### `POST /cases/task/{taskKey}/solve`

- Operation `solveTask` (CPRDETAILCASEApi; `7794.5a468305.js`)
- Path params: `taskKey`
- Body (JSON `SolveTaskRequestDto`):
  - `noteContent`
  - `taskDocuments` (array)
- Response: empty (HTTP 200/204)

### `GET /cases/tasks/{caseKey}`

- Operation `getCaseTasks` (CPRDETAILCASEApi; `7794.5a468305.js`)
- Path params: `caseKey`
- Query: `assistMode`
- Response: JSON object:
  - `sections` (array)

### `PATCH /cases/tasks/{taskKey}`

- Operation `updateTask` (CPRDETAILCASEApi; `7794.5a468305.js`)
- Path params: `taskKey`
- Body (JSON `UpdateTaskRequestDto`):
  - `taskValidTo` (date)
  - `taskImportance` (CodebookEntryIdentifierDto)
  - `taskMandatoryFlag`
  - `taskStatus` (CodebookEntryIdentifierDto)
  - `taskDescription`
  - `noteContent`
  - `taskDocuments` (array)
  - `solver` (object)
- Response: empty (HTTP 200/204)

### `POST /cases/tasks/{taskKey}/documents/content`

- Operation `uploadTaskDocument` (CPRDETAILCASEApi; `7794.5a468305.js`)
- Path params: `taskKey`
- Body: `multipart/form-data` parts `documentVersionContent`
- Response: JSON object:
  - `documentId`

### `PUT /cases/tasks/{taskKey}/documents/prepare`

- Operation `prepareTaskDocument` (CPRDETAILCASEApi; `7794.5a468305.js`)
- Path params: `taskKey`
- Response: JSON object:
  - `documentId`

### `GET /cases/tasks/{taskKey}/documents/{documentId}/content`

- Operation `downloadTaskDocument` (CPRDETAILCASEApi; `7794.5a468305.js`)
- Path params: `taskKey`, `documentId`
- Response: binary file (blob)

### `POST /cases/tasks/{taskKey}/documents/{documentId}/merge`

- Operation `mergeTaskDocument` (CPRDETAILCASEApi; `7794.5a468305.js`)
- Path params: `taskKey`, `documentId`
- Body: `multipart/form-data` parts `documentVersionContent`
- Response: empty (HTTP 200/204)

### `GET /cases/tasks/{taskKey}/history/customer`

- Operation `getTaskHistoryCustomer` (CPRDETAILCASEApi; `7794.5a468305.js`)
- Path params: `taskKey`
- Query: `size`, `page`
- Response: JSON object

### `GET /cases/tasks/{taskKey}/history/servicer`

- Operation `getTaskHistoryServicer` (CPRDETAILCASEApi; `7794.5a468305.js`)
- Path params: `taskKey`
- Query: `fullTextFilter`, `size`, `page`
- Response: JSON object

### `GET /cases/translate-id`

- Operation `translateCaseId` (CPRDETAILCASEApi; `7794.5a468305.js`)
- Query: `caseIdCm`, `caseGuidCrm`, `caseIdCrm`
- Response: JSON object:
  - `caseKey`

### `GET /cases/{caseKey}`

- Operation `getCaseDetail` (CPRDETAILCASEApi; `7794.5a468305.js`)
- Path params: `caseKey`
- Query: `assistMode`
- Response: JSON object:
  - `customer` (object)
  - `noTaskWidgetCustomerDescFlag`
  - `processUrl`
  - `returnToProcessWidgetConfiguration` (object)
  - `caseExpandHeaders` (array)
  - `caseHeaders` (array)
  - `caseEnableClientNotification`
  - `caseCanReturnToProcessFlag`
  - `caseFlagPublishOnline`
  - `caseIdCm`
  - `partnerEnableCaseNotificationFlag`
  - `notesWidgetVisibleFlag`
  - `caseServiceCategory` (CodebookEntryDto)
  - `caseCategory` (CodebookEntryDto)
  - `caseStatus` (CodebookEntryDto)
  - `processIdCm`

### `PATCH /cases/{caseKey}/attrs`

- Operation `patchHeaderAttributes` (CPRDETAILCASEApi; `7794.5a468305.js`)
- Path params: `caseKey`
- Body (JSON `UpdateHeaderAttrsDto`):
  - `caseDescription`
- Response: empty (HTTP 200/204)

### `POST /cases/{caseKey}/documents/content`

- Operation `uploadDocument` (CPRDETAILCASEApi; `7794.5a468305.js`)
- Path params: `caseKey`
- Query: `taskTypeId`
- Body: `multipart/form-data` parts `documentVersionContent`
- Response: JSON object:
  - `documentId`

### `POST /cases/{caseKey}/documents/{documentId}/merge`

- Operation `mergeDocument` (CPRDETAILCASEApi; `7794.5a468305.js`)
- Path params: `caseKey`, `documentId`
- Body: `multipart/form-data` parts `documentVersionContent`
- Response: empty (HTTP 200/204)

### `GET /cases/{caseKey}/history`

- Operation `getCaseHistory` (CPRDETAILCASEApi; `7794.5a468305.js`)
- Path params: `caseKey`
- Query: `changeDateFrom`, `changeDateTo`, `fullTextFilter`, `oldValue`, `newValue`, `size`, `page`
- Response: JSON object

### `GET /cases/{caseKey}/history/filters`

- Operation `getCaseHistoryFiltres` (CPRDETAILCASEApi; `7794.5a468305.js`)
- Path params: `caseKey`
- Response: JSON object:
  - `caseHistoryAttributesFilters` (array)

### `GET /cases/{caseKey}/notes`

- Operation `getCaseNotes` (CPRDETAILCASEApi; `7794.5a468305.js`)
- Path params: `caseKey`
- Query: `assistMode`, `size`, `page`
- Response: JSON object

### `GET /cases/{caseKey}/objectLinks`

- Operation `getObjectLinks` (CPRDETAILCASEApi; `7794.5a468305.js`)
- Path params: `caseKey`
- Query: `size`, `page`
- Response: JSON object

### `POST /cases/{caseKey}/objectLinks`

- Operation `addObjectLink` (CPRDETAILCASEApi; `7794.5a468305.js`)
- Path params: `caseKey`
- Body (JSON `AddObjectLinkRequestDto`):
  - `objectType` (CodebookEntryIdentifierDto)
  - `objectKey`
- Response: empty (HTTP 200/204)

### `DELETE /cases/{caseKey}/objectLinks/{objectTypeId}/{objectKey}`

- Operation `deleteObjectLink` (CPRDETAILCASEApi; `7794.5a468305.js`)
- Path params: `caseKey`, `objectTypeId`, `objectKey`
- Response: empty (HTTP 200/204)

### `POST /cases/{caseKey}/tasks`

- Operation `createTask` (CPRDETAILCASEApi; `7794.5a468305.js`)
- Path params: `caseKey`
- Body (JSON `CreateTaskRequestDto`):
  - `solver` (object)
  - `taskImportance` (CodebookEntryIdentifierDto)
  - `taskDescription`
  - `taskStatus` (CodebookEntryIdentifierDto)
  - `taskType` (CodebookEntryIdentifierDto)
  - `taskValidTo` (date)
  - `taskMandatoryFlag`
  - `taskDocuments` (array)
  - `noteContent`
- Response: empty (HTTP 200/204)

### `POST /cases/{caseKey}/updateFlags`

- Operation `updateFlags` (CPRDETAILCASEApi; `7794.5a468305.js`)
- Path params: `caseKey`
- Body (JSON `UpdateFlagsRequestDto`):
  - `caseFlagPublishOnline`
  - `caseEnableClientNotification`
- Response: empty (HTTP 200/204)

### `GET /employees/suggest`

- Operation `suggestEmployee` (CPRDETAILCASEApi; `7794.5a468305.js`)
- Query: `suggestField`, `suggestString`
- Response: JSON object:
  - `employees` (array)

### `GET /tasks/translate-id`

- Operation `translateTaskId` (CPRDETAILCASEApi; `7794.5a468305.js`)
- Query: `taskGuidCrm`, `taskIdCrm`, `taskIdJuz`
- Response: JSON object:
  - `taskKey`

### `GET /tasks/{taskKey}`

- Operation `getTaskDetail` (CPRDETAILCASEApi; `7794.5a468305.js`)
- Path params: `taskKey`
- Query: `assistMode`
- Response: JSON object:
  - `taskConfiguration` (object)
  - `taskType` (CodebookEntryDto)
  - `taskImportance` (CodebookEntryDto)
  - `taskDescription`
  - `taskDocuments` (array)
  - `solver` (object)
  - `taskValidTo` (date)
  - `taskIdCrm`
  - `taskCreateDate` (date)
  - `taskKey`
  - `taskMandatoryFlag`
  - `taskStatus` (CodebookEntryDto)
  - `taskClosureDate` (date)
  - `taskValidFrom` (date)
  - `firstEmployeeQuestionNote`
  - `lastCustomerResponseNote`
  - `lastEmployeeResponseNote`
  - `caseIdCrm`
  - `processIdCm`
  - `systemTaskId`
  - `taskIdJuz`
  - `solverComponent`
  - `reasonInactivation`
  - `active`

## CPRDOCDOCUMENTSApi (base URL `REACT_APP_DOC_API_URL`)

### `POST /documents/cancel`

- Operation `cancelDocument` (CPRDOCDOCUMENTSApi; `5503.50b79690.js`)
- Body (JSON `CancelDocumentRequestDto`):
  - `documentId`
  - `documentVersionNumber`
- Response: empty (HTTP 200/204)

### `POST /documents/convert`

- Operation `convertDocument` (CPRDOCDOCUMENTSApi; `5503.50b79690.js`)
- Body: `multipart/form-data` parts `convertDocumentBinary`
- Response: binary file (blob)

### `POST /documents/create`

- Operation `createDocumentWithoutBinary` (CPRDOCDOCUMENTSApi; `5503.50b79690.js`)
- Body (JSON `CreateDocumentDataDto`):
  - `documentVersionMetadata` (object)
  - `documentVersionTags` (array)
  - `documentVersionPartners` (array)
  - `document` (object)
  - `documentVersionParams` (array)
- Response: JSON object:
  - `documentId`
  - `documentVersionNumber`
  - `documentVersionName`

### `POST /documents/links/create`

- Operation `createLinks` (CPRDOCDOCUMENTSApi; `5503.50b79690.js`)
- Body (JSON array of `DocumentVersionLinkRequestDto`):
  - `duration`
  - `documentVersionNumber`
  - `documentId`
- Response: JSON array of object

### `GET /documents/links/{linkToken}`

- Operation `getLinkedDocument` (CPRDOCDOCUMENTSApi; `5503.50b79690.js`)
- Path params: `linkToken`
- Response: binary file (blob)

### `POST /documents/previews/download`

- Operation `downloadMergeDocuments` (CPRDOCDOCUMENTSApi; `5503.50b79690.js`)
- Body (JSON array of `DownloadMergeDocumentsPreviewDto`):
  - `previewSequenceNumber`
  - `previewId`
- Response: JSON object:
  - `virtualProperty`

### `POST /documents/previews/merge`

- Operation `mergeDocuments` (CPRDOCDOCUMENTSApi; `5503.50b79690.js`)
- Body (JSON array of `MergeDocumentDto`):
  - `createMergeData` (object)
  - `requestId`
  - `mergeSequence` (object)
  - `updateMergeData` (object)
- Response: JSON array of object

### `GET /documents/previews/{previewId}`

- Operation `getDocumentPagePreview` (CPRDOCDOCUMENTSApi; `5503.50b79690.js`)
- Path params: `previewId`
- Query: `smallPreviewSize`
- Response: binary file (blob)

### `POST /documents/register`

- Operation `registerDocument` (CPRDOCDOCUMENTSApi; `5503.50b79690.js`)
- Body (JSON `DocumentIdDto`):
  - `documentVersionIdLeonardo` (object)
  - `documentVersionURL` (object)
  - `documentVersionIdSharedContentDocument` (object)
  - `documentVersionIdSAP` (object)
- Response: JSON object:
  - `documentId`
  - `documentVersionNumber`

### `POST /documents/restore`

- Operation `restoreDocumentVersion` (CPRDOCDOCUMENTSApi; `5503.50b79690.js`)
- Body (JSON `RestoreDocumentVersionRequestDto`):
  - `documentId`
  - `documentVersionNumber`
- Response: JSON object:
  - `documentVersionNumber`

### `GET /documents/search`

- Operation `searchDocuments` (CPRDOCDOCUMENTSApi; `5503.50b79690.js`)
- Query: `documentId`, `lastVersionOnly`, `providePartnersDetail`, `relationObjectId`
- Response: JSON array of object

### `POST /documents/search`

- Operation `advanceSearchDocuments` (CPRDOCDOCUMENTSApi; `5503.50b79690.js`)
- Query: `size`, `page`
- Body (JSON `AdvanceSearchDocumentsRequestDto`):
  - `documentVersionPublishOnlineFlag`
  - `documentPurpose` (CodebookEntryIdentifierDto[])
  - `documentVersionActiveStatus` (CodebookEntryIdentifierDto[])
  - `documentStatus` (CodebookEntryIdentifierDto[])
  - `documentId`
  - `documentSharedContentFlag`
  - `providePartnersDetail`
  - `lastVersionOnly`
  - `documentCategory` (CodebookEntryIdentifierDto[])
  - `documentParameter` (array)
  - `partner` (object)
  - `relationObject` (array)
  - `documentVersionBarcode`
  - `validDate` (date)
- Response: JSON object

### `GET /documents/{documentId}`

- Operation `getDocumentMetadata` (CPRDOCDOCUMENTSApi; `5503.50b79690.js`)
- Path params: `documentId`
- Query: `documentVersionNumber`
- Response: JSON object:
  - `documentVersionMetadata` (object)
  - `document` (object)
  - `documentVersionPartners` (array)
  - `documentVersionParams` (array)
  - `documentVersionTags` (array)

### `PATCH /documents/{documentId}`

- Operation `patchDocument` (CPRDOCDOCUMENTSApi; `5503.50b79690.js`)
- Path params: `documentId`
- Body (JSON `DocumentPatchDataDto`):
  - `documentVersionMetadata` (object)
  - `document` (object)
  - `documentVersionParams` (array)
  - `documentVersionPartners` (array)
  - `documentVersionTags` (array)
- Response: empty (HTTP 200/204)

### `PUT /documents/{documentId}`

- Operation `updateDocument` (CPRDOCDOCUMENTSApi; `5503.50b79690.js`)
- Path params: `documentId`
- Body: `multipart/form-data` parts `documentVersionContent`, `documentVersionData`
- Response: JSON object:
  - `documentId`
  - `documentVersionNumber`

### `GET /documents/{documentId}/content`

- Operation `getDocumentContent` (CPRDOCDOCUMENTSApi; `5503.50b79690.js`)
- Path params: `documentId`
- Query: `documentVersionNumber`
- Response: binary file (blob)

### `DELETE /documents/{documentId}/delete`

- Operation `deleteDocument` (CPRDOCDOCUMENTSApi; `5503.50b79690.js`)
- Path params: `documentId`
- Response: empty (HTTP 200/204)

### `POST /documents/{documentId}/merge`

- Operation `mergeToDocument` (CPRDOCDOCUMENTSApi; `5503.50b79690.js`)
- Path params: `documentId`
- Body (JSON `MergeToDocumentDataDto`):
  - `mergeDocumentsDeleteFlag`
  - `mergeDocuments` (array)
  - `documentVersionData` (object)
- Response: JSON object:
  - `documentId`
  - `documentVersionNumber`

### `GET /documents/{documentId}/previews/list`

- Operation `getPreviewList` (CPRDOCDOCUMENTSApi; `5503.50b79690.js`)
- Path params: `documentId`
- Query: `documentVersionNumber`
- Body: raw `m`
- Response: JSON object:
  - `previews` (array)

### `PUT /documents/{documentId}/register`

- Operation `putRegisterDocument` (CPRDOCDOCUMENTSApi; `5503.50b79690.js`)
- Path params: `documentId`
- Body (JSON `DocumentIdObjectDto`):
  - `documentVersionIdSAP` (object)
  - `documentVersionNumber`
  - `documentVersionURL` (object)
  - `documentVersionIdLeonardo` (object)
- Response: JSON object:
  - `documentId`
  - `documentVersionNumber`

### `POST /documents/{documentId}/subscribe`

- Operation `postSubscribeApplication` (CPRDOCDOCUMENTSApi; `5503.50b79690.js`)
- Path params: `documentId`
- Body (JSON `SubscribeApplicationRequestDto`):
  - `application` (CodebookEntryIdentifierDto)
- Response: empty (HTTP 200/204)

### `POST /documents/{documentId}/unsubscribe`

- Operation `postUnsubscribeAppliaction` (CPRDOCDOCUMENTSApi; `5503.50b79690.js`)
- Path params: `documentId`
- Body (JSON `UnsubscribeApplicationRequestDto`):
  - `application` (CodebookEntryIdentifierDto)
- Response: empty (HTTP 200/204)

## CPRFEEAGREEMENTApi (base URL `REACT_APP_FEE_API_URL (falls back to REACT_APP_API_URL)`)

### `POST /agreement/marketing-consent`

- Operation `setAgreementMarketingConsent` (CPRFEEAGREEMENTApi; `4127.a8baf8ce.js`)
- Query: `processId`, `agreementId`, `marketingConsent`, `caseId`
- Response: empty (HTTP 200/204)

### `DELETE /agreements`

- Operation `deleteAgreement` (CPRFEEAGREEMENTApi; `4127.a8baf8ce.js`)
- Query: `agreementId`, `caseId`, `processId`
- Response: empty (HTTP 200/204)

### `GET /agreements`

- Operation `getAgreement` (CPRFEEAGREEMENTApi; `4127.a8baf8ce.js`)
- Query: `caseId`, `processId`, `agreementId`
- Response: JSON object:
  - `useEmailForElectronicInvoicing`
  - `marketingConsent`
  - `gdprConsent`
  - `agreementAdvancePaymentPaymentMethod` (object)
  - `agreementRefundingOverpaymentMethod` (object)
  - `agreementId`
  - `agreementInvoicePaymentMethod` (object)
  - `addresses` (array)
  - `contacts` (array)
  - `agreementGuidCrm`
  - `agreementIdCrm`
  - `agreementCreationStatus`
  - `billingReceivablesAndPayablesAccountDocumentNumbers`
  - `creationErrors` (array)

### `POST /agreements`

- Operation `createAgreement` (CPRFEEAGREEMENTApi; `4127.a8baf8ce.js`)
- Query: `caseId`, `processId`
- Body (JSON `AgreementDto`):
  - `useEmailForElectronicInvoicing`
  - `marketingConsent`
  - `gdprConsent`
  - `agreementAdvancePaymentPaymentMethod` (object)
  - `agreementRefundingOverpaymentMethod` (object)
  - `agreementId`
  - `agreementInvoicePaymentMethod` (object)
  - `addresses` (array)
  - `contacts` (array)
  - `agreementGuidCrm`
  - `agreementIdCrm`
  - `agreementCreationStatus`
  - `billingReceivablesAndPayablesAccountDocumentNumbers`
  - `creationErrors` (array)
- Response: JSON object:
  - `agreementId`

### `PUT /agreements`

- Operation `updateAgreement` (CPRFEEAGREEMENTApi; `4127.a8baf8ce.js`)
- Query: `caseId`, `processId`, `agreementId`
- Body (JSON `AgreementDto`):
  - `useEmailForElectronicInvoicing`
  - `marketingConsent`
  - `gdprConsent`
  - `agreementAdvancePaymentPaymentMethod` (object)
  - `agreementRefundingOverpaymentMethod` (object)
  - `agreementId`
  - `agreementInvoicePaymentMethod` (object)
  - `addresses` (array)
  - `contacts` (array)
  - `agreementGuidCrm`
  - `agreementIdCrm`
  - `agreementCreationStatus`
  - `billingReceivablesAndPayablesAccountDocumentNumbers`
  - `creationErrors` (array)
- Response: empty (HTTP 200/204)

### `POST /agreements/contract`

- Operation `uploadSignedContract` (CPRFEEAGREEMENTApi; `4127.a8baf8ce.js`)
- Query: `documentTypeStatusId`, `documentTypeFlagMandatory`, `processId`, `contractValidityStartDate`, `caseId`
- Body: `multipart/form-data` parts `attachment`
- Response: empty (HTTP 200/204)

### `GET /agreements/detail`

- Operation `getAgreementDetail` (CPRFEEAGREEMENTApi; `4127.a8baf8ce.js`)
- Query: `agreementIdCrm`
- Response: JSON object

### `POST /agreements/document`

- Operation `generateAgreementDocument` (CPRFEEAGREEMENTApi; `4127.a8baf8ce.js`)
- Query: `caseId`, `processId`
- Response: binary file (blob)

### `GET /agreements/documents/content`

- Operation `getDocumentContent` (CPRFEEAGREEMENTApi; `4127.a8baf8ce.js`)
- Query: `processId`, `caseIdCm`, `documentId`
- Response: binary file (blob)

### `PATCH /agreements/name`

- Operation `updateAgreementName` (CPRFEEAGREEMENTApi; `4127.a8baf8ce.js`)
- Query: `agreementGuidCrm`, `agreementIdCrm`
- Body (JSON `AgreementNameUpdateRequestDto`):
  - `agreementName`
- Response: empty (HTTP 200/204)

### `POST /agreements/retry-creation`

- Operation `retryAgreementCreation` (CPRFEEAGREEMENTApi; `4127.a8baf8ce.js`)
- Query: `caseIdCm`, `processId`
- Response: empty (HTTP 200/204)

### `GET /agreements/validate-create`

- Operation `validateAndOptionallyCreateAgreement` (CPRFEEAGREEMENTApi; `4127.a8baf8ce.js`)
- Query: `mode`, `supplyPointCode`, `processId`, `caseId`, `documentId`
- Response: empty (HTTP 200/204)

### `POST /agreements/verification-sms`

- Operation `sendVerificationSms` (CPRFEEAGREEMENTApi; `4127.a8baf8ce.js`)
- Query: `type`, `caseIdCm`
- Response: empty (HTTP 200/204)

### `GET /contracts`

- Operation `getFeeContracts` (CPRFEEAGREEMENTApi; `4127.a8baf8ce.js`)
- Response: JSON array of object

## CPRSASPARTNERSApi (base URL `unknown (not wired in the customer app)`)

### `GET /partners`

- Operation `getPartner` (CPRSASPARTNERSApi; `2876.637e1c40.js`)
- Query: `partnerIdCrm`, `partnerIdClientComponent`
- Response: JSON object:
  - `individual` (object)
  - `addresses` (array)
  - `partnerIdClientComponent`
  - `partnerIdCrm`
  - `partnerCategory` (CodebookEntryDto)
  - `partnerType` (CodebookEntryDto)
  - `partnerKind` (CodebookEntryDto)
  - `contacts` (array)
  - `bankAccounts` (array)
  - `legalEntity` (object)
  - `partnerGuidCrm`

### `PATCH /partners`

- Operation `patchPartner` (CPRSASPARTNERSApi; `2876.637e1c40.js`)
- Body (JSON `PatchPartnerRequestDto`):
  - `legalEntity` (object)
  - `partnerIdCrm`
  - `individual` (object)
  - `bankAccounts` (array)
  - `partnerIdClientComponent`
  - `contacts` (array)
  - `addresses` (array)
- Response: JSON object:
  - `partnerIdClientComponent`
  - `partnerIdCrm`

### `POST /partners`

- Operation `savePartner` (CPRSASPARTNERSApi; `2876.637e1c40.js`)
- Body (JSON `SavePartnerRequestDto`):
  - `contacts` (array)
  - `individual` (object)
  - `addresses` (array)
  - `legalEntity` (object)
  - `bankAccounts` (array)
  - `partnerKind` (CodebookEntryIdentifierDto)
  - `relatedPartners` (array)
- Response: JSON object:
  - `partnerIdCrm`
  - `partnerIdClientComponent`

### `GET /partners/consent`

- Operation `getGDPRConsent` (CPRSASPARTNERSApi; `2876.637e1c40.js`)
- Query: `partnerIdCrm`
- Response: JSON object:
  - `consentValidFromDate` (date)
  - `consentConfirmationType` (CodebookEntryDto)
  - `consentType` (CodebookEntryDto)
  - `consentGrantingDate` (date)
  - `consentProlongationType` (CodebookEntryDto)
  - `consentPurpouse` (CodebookEntryDto)
  - `consentValidToDate` (date)
  - `consentStatus` (CodebookEntryDto)

### `POST /partners/consent`

- Operation `saveGDPRConsent` (CPRSASPARTNERSApi; `2876.637e1c40.js`)
- Body (JSON `SaveGDPRConsentRequestDto`):
  - `partnerIdCrm`
- Response: empty (HTTP 200/204)

### `DELETE /partners/{partnerIdClientComponent}`

- Operation `rollbackPartner` (CPRSASPARTNERSApi; `2876.637e1c40.js`)
- Path params: `partnerIdClientComponent`
- Response: empty (HTTP 200/204)

### `PUT /partners/{partnerIdClientComponent}/commit`

- Operation `commitPartner` (CPRSASPARTNERSApi; `2876.637e1c40.js`)
- Path params: `partnerIdClientComponent`
- Body (JSON `CommitPartnerRequestDto`):
  - `forceCommit`
- Response: empty (HTTP 200/204)

### `GET /users/token-data`

- Operation `getTokenData` (CPRSASPARTNERSApi; `2876.637e1c40.js`)
- Response: JSON object:
  - `email`
  - `partners`
  - `defaultPartner`
  - `username`
  - `ppjmShortHash`
  - `ppjmFull`
  - `roleTypeName`
  - `ppjmShort`

## CPRVALVALIDATIONApi (base URL `REACT_APP_VALIDATION_API_URL`)

### `POST /check-duplicates-bank-account-ibans`

- Operation `ibanDuplicityCheck` (CPRVALVALIDATIONApi; `6507.c676d6d1.js`)
- Body (JSON `IbanDuplicityCheckRequestDto`):
  - `bankAccountIban`
  - `partnerId`
- Response: JSON object:
  - `validationResult` (object)
  - `duplicityResult` (array)

### `POST /check-duplicates-bank-accounts`

- Operation `bankAccountDuplicityCheck` (CPRVALVALIDATIONApi; `6507.c676d6d1.js`)
- Body (JSON `RequestDuplicityBankAccountsDto`):
  - `bankAccounts` (array)
- Response: JSON object:
  - `result` (array)

### `POST /check-duplicates-birth-numbers`

- Operation `birthNumberDuplicityCheck` (CPRVALVALIDATIONApi; `6507.c676d6d1.js`)
- Body (JSON `BirthNumberDuplicityCheckRequestDto`):
  - `individualPersonalIdentificationNumber`
  - `partnerId`
- Response: JSON object:
  - `validationResult` (object)
  - `duplicityResult` (array)

### `POST /check-duplicates-contacts`

- Operation `contactDuplicityCheck` (CPRVALVALIDATIONApi; `6507.c676d6d1.js`)
- Body (JSON `RequestDuplicityContactsDto`):
  - `contacts` (array)
- Response: JSON object:
  - `result` (array)

### `POST /check-duplicates-identity-documents`

- Operation `documentIdentificationDuplicityCheck` (CPRVALVALIDATIONApi; `6507.c676d6d1.js`)
- Body (JSON `DocumentIdentificationDuplicityCheckRequestDto`):
  - `partnerIdentityDocumentId`
  - `partnerIdentityDocumentTypeId`
  - `partnerId`
- Response: JSON object:
  - `validationResult` (object)
  - `duplicityResult` (array)

### `POST /check-duplicates-legal-entity-numbers`

- Operation `legalEntityNumberDuplicityCheck` (CPRVALVALIDATIONApi; `6507.c676d6d1.js`)
- Body (JSON `LegalEntityNumberDuplicityCheckRequestDto`):
  - `legalEntityNumber`
  - `partnerId`
- Response: JSON object:
  - `validationResult` (object)
  - `duplicityResult` (array)

### `POST /check-duplicates-partners`

- Operation `validatePartnerDuplicity` (CPRVALVALIDATIONApi; `6507.c676d6d1.js`)
- Body (JSON `ValidatePartnerDuplicityRequestDto`):
  - `addressStreetName`
  - `addressHouseNumber`
  - `partnerId`
  - `individualFirstName`
  - `legalEntityName`
  - `legalFormTypeId`
  - `addressCityName`
  - `bankAccountFullNumber`
  - `individualBirthDate` (date (YYYY-MM-DD))
  - `legalEntityNumber`
  - `addressZipCode`
  - `individualSurname`
  - `addressLandRegistryNumber`
- Response: JSON object:
  - `validationResult` (object)
  - `duplicityResult` (array)

### `POST /check-duplicates-tax-identification-numbers`

- Operation `dicIdentifierDuplicityCheck` (CPRVALVALIDATIONApi; `6507.c676d6d1.js`)
- Body (JSON `ValidateDicIdentifierRequestDto`):
  - `legalEntityTaxIdentificationNumber`
  - `partnerId`
- Response: JSON object:
  - `validationResult` (object)
  - `duplicityResult` (array)

### `POST /validate-bank-account-ibans`

- Operation `validateIbanIdentifier` (CPRVALVALIDATIONApi; `6507.c676d6d1.js`)
- Body (JSON `ValidateIbanIdentifierRequestDto`):
  - `bankAccountIban`
- Response: JSON object:
  - `validationResult` (object)

### `POST /validate-bank-accounts`

- Operation `validateBankAccount` (CPRVALVALIDATIONApi; `6507.c676d6d1.js`)
- Body (JSON `RequestBankAccountsDto`):
  - `bankAccounts` (array)
- Response: JSON object:
  - `result` (array)

### `POST /validate-birth-numbers`

- Operation `validateBirthNumber` (CPRVALVALIDATIONApi; `6507.c676d6d1.js`)
- Body (JSON `ValidateBirthNumberRequestDto`):
  - `genderId`
  - `individualBirthDate` (date (YYYY-MM-DD))
  - `individualPersonalIdentificationNumber`
- Response: JSON object:
  - `validationResult` (object)

### `POST /validate-contacts`

- Operation `validateContact` (CPRVALVALIDATIONApi; `6507.c676d6d1.js`)
- Body (JSON `RequestContactsDto`):
  - `contacts` (array)
- Response: JSON object:
  - `result` (array)

### `POST /validate-ean-eics`

- Operation `validateEanEicIdentifier` (CPRVALVALIDATIONApi; `6507.c676d6d1.js`)
- Body (JSON `ValidateEanEicIdentifierRequestDto`):
  - `commodityId`
  - `supplyPointCode`
- Response: JSON object:
  - `validationResult` (object)

### `POST /validate-identity-documents`

- Operation `validateIdentityDocument` (CPRVALVALIDATIONApi; `6507.c676d6d1.js`)
- Body (JSON `ValidateIdentityDocumentRequestDto`):
  - `partnerIdentityDocumentId`
  - `partnerIdentityDocumentTypeId`
- Response: JSON object:
  - `validationResult` (object)

### `POST /validate-legal-entity-numbers`

- Operation `validateLegalEntityNumber` (CPRVALVALIDATIONApi; `6507.c676d6d1.js`)
- Body (JSON `ValidateLegalEntityNumberRequestDto`):
  - `legalEntityNumber`
- Response: JSON object:
  - `validationResult` (object)

### `POST /validate-tax-identification-numbers`

- Operation `validateDicIdentifier` (CPRVALVALIDATIONApi; `6507.c676d6d1.js`)
- Body (JSON `ValidateDicIdentifierRequestDto`):
  - `legalEntityTaxIdentificationNumber`
  - `partnerId`
- Response: JSON object:
  - `validationResult` (object)

## CPRVALWHISPERERApi (base URL `REACT_APP_WHISPERER_API_URL`)

### `GET /whisper-address`

- Operation `whisperAddress` (CPRVALWHISPERERApi; `2012.734ddeee.js`)
- Query: `addressFull`
- Response: JSON object:
  - `whispererResultAddress` (array)
  - `validationResult` (object)

### `GET /whisper-cadastral-territory`

- Operation `whisperCadastralTerritory` (CPRVALWHISPERERApi; `2012.734ddeee.js`)
- Query: `addressCityId`, `addressCadastralTerritory`
- Response: JSON object:
  - `whispererResultCadastralTerritory` (array)
  - `validationResult` (object)

### `GET /whisper-city`

- Operation `whisperCity` (CPRVALWHISPERERApi; `2012.734ddeee.js`)
- Query: `addressCityName`
- Response: JSON object:
  - `validationResult` (object)
  - `whispererResultCity` (array)

### `GET /whisper-parcel-number`

- Operation `whisperParcelNumber` (CPRVALWHISPERERApi; `2012.734ddeee.js`)
- Query: `addressParcelNumber`, `addressCadastralTerritoryId`
- Response: JSON object:
  - `whispererResultParcelNumber` (array)
  - `validationResult` (object)

### `GET /whisper-partner-detail`

- Operation `whisperPartnerDetail` (CPRVALWHISPERERApi; `2012.734ddeee.js`)
- Query: `legalEntityNumber`
- Response: JSON object:
  - `whispererResultPartnerDetail` (object)
  - `validationResult` (object)

### `GET /whisper-street`

- Operation `whisperStreet` (CPRVALWHISPERERApi; `2012.734ddeee.js`)
- Query: `addressCityId`, `addressStreetName`
- Response: JSON object:
  - `whispererResultStreet` (array)
  - `validationResult` (object)

### `GET /whisper-zip-code`

- Operation `whisperZipCode` (CPRVALWHISPERERApi; `2012.734ddeee.js`)
- Query: `addressCityId`, `addressZipCode`
- Response: JSON object:
  - `whispererResultZipCode` (array)
  - `validationResult` (object)

