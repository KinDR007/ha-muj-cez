# Analýza proveditelnosti a udržitelnosti: HA integrace Můj ČEZ

Datum: 2026-11-16, verze frontendu muj.cez.cz 3.66.0 (release/2026-11)

## 1. Existující řešení

Žádná integrace pro muj.cez.cz (obchodník ČEZ Prodej) nebyla nalezena. Existují jen integrace pro jiné zdroje:

- HDO: zigul/HomeAssistant-CEZdistribuce, konikvranik/hacs_cez_hdo
- odstávky: konikvranik/hacs_cez_outages
- PND (naměřená data distributora, jiný portál): ondrejvysek/HomeAssistant-CEZDistribuce-PND, cez-distribuce-data-fetcher (Selenium)

## 2. Technické zjištění (z veřejného JS a HTTP sondy, bez přihlášení)

| Oblast | Zjištění |
|---|---|
| Frontend | React SPA `https://muj.cez.cz/col/`, runtime konfigurace v `/col/config.js` |
| API | REST `https://muj.cez.cz/col-api/prod/1.0` za WSO2 API Managerem |
| Autentizace | OAuth2 Authorization Code + PKCE, `auth.cez.cz` (WSO2 IS), federováno na Apereo CAS `mepas.cez.cz/cas/login` |
| Klient | veřejný `client_id` (`REACT_APP_CONSUMER_KEY` v config.js), bez secretu |
| Token | `https://api.cez.cz/token`, SPA používá i `refresh_token` |
| Login formulář | `username`, `password`, `execution`, `_eventId`, `geolocation`; na stránce není CAPTCHA |
| MFA | neověřeno |

Relevantní endpointy nalezené v JS:

- `/simulations/invoices/{supplyPointCode}`, `/simulations/invoices/recommend-amount` (predikce vyúčtování)
- `/invoice-simulations/calculate`
- `/supply-points/{supplyPointId}/ReadConsumptionHistory`, `/ReadAdvancePlan`
- `/advance-payments/{supplyPointId}`
- `/dynamic-tariff/consumption-summary/{uid}`, `/dynamic-tariff/data/{uid}`, `/dynamic-tariff/dynamic-price-info/{uid}`
- `/product-calculator/...`

Struktura odpovědí zatím neznámá (vyžaduje přihlášenou session).

## 3. Proveditelnost: vysoká (ověřeno, viz kap. 6)

- Data jdou přes čisté JSON API, prohlížeč v runtime není potřeba. Integrace může běžet na `aiohttp`, tedy nativně v HA OS bez Chromia/Selenia.
- Login lze provést HTTP tokem: GET authorize → CAS formulář → POST → redirect s `code` → výměna za token s PKCE. Pak pracovat s refresh tokenem, plný login jen při expiraci.
- Prohlížeč (Playwright) je potřeba jen jednorázově při vývoji pro zmapování odpovědí.

Varianty:

| Varianta | Hodnocení |
|---|---|
| A: HTTP klient (aiohttp) + OAuth/CAS tok | doporučeno; lehké, běží v HA OS |
| B: Headless prohlížeč v HA | nevhodné; HA OS nemá Chromium, nutný add-on, vysoká RAM, křehké |
| C: Externí scraper (Docker/Proxmox) → MQTT | záložní řešení, pokud by ČEZ přidal bot ochranu |

## 4. Udržitelnost: střední

Rizika:

1. Neoficiální API: ČEZ vydává frontend měsíčně, endpointy nebo schéma se mohou změnit bez ohlášení.
2. Rotace `client_id` nebo změna auth toku (WSO2/CAS). Mitigace: číst `client_id` a URL dynamicky z `config.js`.
3. Přidání CAPTCHA/MFA/bot ochrany na login (proměnná `REACT_APP_DISABLE_CAPTCHA` existuje). Mitigace: refresh token minimalizuje počet loginů; fallback varianta C.
4. Obchodní podmínky portálu: automatizovaný přístup k vlastnímu účtu 1× denně je nízké riziko, ale není výslovně povolen.

Opatření:

- API klient jako samostatný modul s testy na nahraných odpovědích (fixtures).
- HA `reauth` flow, `diagnostics`, srozumitelné chyby (`ConfigEntryAuthFailed`, `UpdateFailed`).
- Defenzivní parsování, chybějící pole → `unavailable` místo pádu.
- Distribuce přes HACS, verzování, changelog.

## 5. Návrh integrace (`custom_components/muj_cez`)

- `config_flow`: e-mail, heslo, výběr odběrných míst
- `options_flow`: perioda (den/týden/měsíc), čas běhu (výchozí 00:xx s náhodným posunem)
- `DataUpdateCoordinator` s vlastním plánováním (`async_track_time_change`), ne pevný `update_interval`
- entity podle odběrného místa: predikce vyúčtování, doporučená záloha, aktuální záloha, spotřeba za období, cena (dynamický tarif, pokud je)
- volitelně import historie spotřeby do long-term statistics (Energy dashboard)
- přihlašovací údaje uložené v config entry (standard HA)

Poznámka k pevné půlnoci: data simulací se na straně ČEZ mění zřídka (odečet, faktura). Lepší je nastavitelný čas s náhodným posunem než přesně 00:00.

## 6. Ověřeno živě (2026-11-16, se souhlasem uživatele)

Login bez prohlížeče funguje. Tok (`tools/probe/probe_login.py`):

1. GET `auth.cez.cz/oauth2/authorize` (`client_id` z config.js, `redirect_uri=https://muj.cez.cz/col`, `scope=openid device_<uuid>`, PKCE S256) → redirect na CAS formulář
2. POST `mepas.cez.cz/cas/login` (`username`, `password`, `execution`, `_eventId=submit`, `geolocation=`)
3. 5 redirectů → `https://muj.cez.cz/col?code=...`
4. POST `api.cez.cz/token` (`authorization_code` + `code_verifier`) → `access_token` (900 s), `refresh_token`, `id_token`
5. `grant_type=refresh_token` funguje

Žádná CAPTCHA, MFA ani bot ochrana. API volání: `Authorization: Bearer <token>`.

### Funkční endpointy (base `https://muj.cez.cz/col-api/prod/1.0`)

| Endpoint | Data |
|---|---|
| `GET /supply-points/RetrieveSupplyPoints` | odběrná místa: EAN, `supplyPointUniqueId`, adresa, produkt, výše a frekvence zálohy |
| `GET /simulations/invoices/{EAN}?supplyPointUid=` | predikce vyúčtování: celková částka (+ doplatek / − přeplatek), doporučená záloha, zúčtovací období, spotřeba po úsecích (skutečná i odhad), 39 položek faktury |
| `GET /billing-period?supplyPointId=` | zúčtovací období |
| `GET /supply-points/{uid}/ReadAdvancePlan` | splátkový kalendář záloh (splatnost, částka, stav) |
| `GET /supply-points/{uid}/ReadConsumptionHistory?aggregation=MONTH` | roční historie spotřeby VT/NT (kWh) a částky (Kč) |
| `GET /supply-points/{uid}/ReadMeterReading` | historie odečtů (120 záznamů od 2017) |
| `GET /meter-reading-consumption-vals?supplyPointCode=` | spotřeba za poslední období, limity pro samoodečet |
| `GET /tapp/metering/price-lists/spot-prices-simple` | spotové ceny 15MIN/HODINA, jen do včerejška, rozsah max ~1 den, hranice celých hodin |
| `GET /hdo-signal/get?supplyPointId=` | HDO (u tohoto odběru prázdné, jednotarif) |

Prázdné pro tento odběr: `/tapp/metering/profile-data`, `grid-data`, `time-intervals` (čtvrthodinová data), `/dynamic-tariff/*`. Účet má `supplyPointIsContinuousMeasurement: true`, ale profilová data portál nevrací. Platné hodnoty `profileReadingIntervalId`: `15MIN`, `HODINA`, `DEN`, `MESIC`, `ROK`.

### Poznámky

- Simulace se přepočítává při dotazu (`invoiceSimulationOriginDate` = čas volání), takže 1× denně má smysl.
- Data v API jsou osobní (adresa, EAN). Uložené odpovědi v `tools/probe/probe_out/` jsou v `.gitignore`.

## 7. Návrh entit (na odběrné místo)

| Entita | Zdroj |
|---|---|
| Predikce vyúčtování (Kč, ± doplatek/přeplatek) | `invoiceSimulationTotalAmount` |
| Predikované náklady za období (Kč s DPH) | součet `invoiceItemAmountWithTax` |
| Doporučená záloha (Kč) | `invoiceSimulationFirstRecommendedAdvancePayment` |
| Aktuální záloha (Kč) | `contractAdvancePaymentAmount` |
| Predikovaná spotřeba za období (kWh) | součet `consumptionValue` |
| Konec zúčtovacího období (datum) | `invoiceSimulationBillingPeriodTo` |
| Příští splátka zálohy (datum, Kč), nezaplacené zálohy | `ReadAdvancePlan` |
| Spotřeba a cena za minulé období (kWh, Kč) | `ReadConsumptionHistory` |
| Poslední stav elektroměru (kWh) | `ReadMeterReading` |

## 8. Rozhodnutí

- Spotové ceny nejsou součástí integrace (ČEZ vrací jen historii do včerejška). Pro aktuální ceny použít samostatnou integraci (např. rnovacek/homeassistant_cz_energy_spot_prices).
- Implementace: `custom_components/muj_cez`, viz README.
