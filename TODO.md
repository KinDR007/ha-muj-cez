# TODO

- [x] Analýza proveditelnosti, ověření HTTP loginu a endpointů
- [x] API klient, config flow, options flow (perioda, čas), reauth
- [x] Senzory, diagnostika, překlady cs/en
- [x] Testy (parsování, config flow, plánování), hassfest
- [x] Nasazeno na HA 2026.11.1 (192.168.88.201), ověřeno po restartu
- [x] GitHub repozitář (privátní)
- [x] HACS custom repository (veřejný repozitář)
- [x] Ikona, rozšířené údaje (smlouva, platby, odstávky, zprávy)
- [x] Kalendář dokladů, akce get_documents, zúčtovací období
- [x] Porovnání HA vs ČEZ (měsíce, období, odečty), grafy v pohledu ČEZ, přepínač kWh/Kč
- [x] Offline vývoj ze snímků (.snapshot)
- [ ] Ověřit formát plánovaných odstávek na reálných datech
- [ ] Volitelně: výběr odběrných míst v options (víc OM na účtu)
- [ ] Volitelně: uložení refresh tokenu mezi restarty (méně loginů)
- [x] Výrobní odběrné místo (výkup), dvoutarif v historii odečtů, data elektroměru (odběr/přetoky), statistiky, spotové ceny
- [ ] Ověřit na vzdáleném HA: backfill statistik a výběr v panelu Energie
- [x] Ocenění přetoků ze spotového senzoru v HA (portál má ceny jen do 30. 9. 2025)
- [x] Historické spotové ceny z OTE (kurz ČNB), portál ČEZ jako záloha
- [x] HDO z portálu ČEZ Distribuce (tarif, příští přepnutí), aktuální cena VT/NT ze simulace 
- [x] HDO: ověřeno na lokálním i vzdáleném HA, sekce v dashboardu
- [x] Release 1.0.0
- [ ] HDO: volba signálu, pokud portál vrací víc signálů (zatím první)
- [x] 15minutová data elektroměru: úložiště s historií, websocket `muj_cez/profile`, sekce dashboardu (týdny, teplotní mapa, typický den, detail týdne, tooltipy); ověřeno na vzdáleném HA
- [x] Okna průběhových dat max. 28 dní (portál vrací max. jeden kalendářní měsíc na dotaz)
- [x] Díry v hodinových statistikách ze starších verzí: jednorázová kontrola a doimport od první díry (ověřeno na vzdáleném HA)
- [x] Odpověď profile-data rozdělená na víc bloků na hranách období portálu: slučují se všechny
- [x] Release 1.1.0
- [x] 15minutová data: jen aktuální měsíc + 12 předchozích (starší se mažou), tlačítko Dnes, rok v indexu i bez změny dat
- [x] Release 1.1.1
- [x] Issue #1: senzor Stav elektroměru NT, výběr zákaznického účtu (X-COL-PARTNER), anonymizovaná surová data v diagnostice (+ redakce e-mailu, kódu OM a adres v diagnostice)
- [ ] Issue #1: ověření výběru účtu autorem (nemáme účet s více zákaznickými čísly)

## Cenový rozpad (branch feature/price-breakdown, jen lokálně)
- [x] Analýza zdrojů: simulace (3 agregáty/měsíc), invoice-detail (souhrn), DIP (sazba, jistič)
- [x] Dokumenty: CSV `POST /documents/attachment` + `GET /documents/{key}/attachment`, PDF `POST /documents` + `/documents/{guid}/attachment`; parametry dokladu vždy z čerstvého `/billings/extended` (header/snapshot id se mění)
- [x] Sonda `tools/probe/probe_documents.py` na obou loginech (CSV jen u části faktur, PDF u všech; výkup = SLF jen množství a částka)
- [x] Parser CSV / PDF / výkup (`invoice.py`), součty sedí na základ daně u všech faktur
- [x] Rozpad simulace podle posledních jednotkových cen (přesně, když ceny sedí; jinak souhrn ze simulace)
- [x] Úložiště faktur (`pricing.py`, stažení jednou, retry 7 dní), websocket `muj_cez/prices`, offline `tools/prices_offline.py`
- [x] Záložka `cez-ceny` (vlastní tab s ikonou) s listováním měsíc/kvartál/rok, s/bez DPH, graf historie, výkup
- [x] Nasazeno a ověřeno na lokálním HA (editor, 5 faktur CSV/PDF) i vzdáleném HA (generovaný dashboard, 6 PDF + 19 výkupů, součty sedí)
- [x] Volba „Cenový rozpad“ (nové vypnuto, stávající zapnuto; vypnutí smaže faktury, bez záložky a bez stahování; pypdf až při zapnutí), ověřeno vyp/zap na lokálním HA
- [ ] Váhy pro rozpočet spotřeby do měsíců: průběhová data / HA statistiky místo dnů
- [x] Nový cenový rok bez faktury: rozpad z ceníku produktu (PDF CEN), i kombinace s poslední fakturou; ověřeno na vzdáleném HA (2026 celý rozložen)
- [x] Opravné faktury a překryvy: pozdější doklad platí pro své dny (ořez), rozdílová oprava se přičítá; nasazeno na obě HA (zatím bez reálné opravné faktury v datech)
- [x] Ověření na HA (pypdf z requirements se nainstaloval)

## Samoodečet elektroměru (branch feature/meter-reading, jen lokálně)
- [x] Rešerše API portálu z JS bundlu: `docs/api/` (README + skupiny endpointů, samoodečet podrobně)
- [x] Validace jako portál (`reading.py`): celé kWh, nižší než předchozí = chyba, nezvykle vysoká (×1,5) = varování, jeden odečet za den, roční limit kontrolních odečtů, poznámka 160 znaků
- [x] Backend `meter_reading.py`, websocket `reading_form` / `reading_check` / `reading_submit`, multipart `POST /self-meter-reading` (ověřeno proti lokálnímu serveru)
- [x] Vlastní karta `custom:muj-cez-reading-card` (servíruje integrace), záložka `cez-odecet`
- [x] Sonda `tools/probe/probe_reading.py` na obou loginech: tvary ověřeny (kWh, dny), validace odpovídá screenshotům portálu; nabízené typy z `requests-advanced`, rozsah data z `form-config`
- [x] Ostrý test odeslání (2026-11-21, jednotarif, deníčkový odečet s poznámkou): HTTP 200, odečet hned na portálu; zkušební režim a volba „Odesílat odečty“ odebrány
- [ ] Ostrý test na dvoutarifu (vzdálené HA) až bude stav VT/NT
- [x] Nasazeno na lokální HA (záložka přes Dashboard Editor) i vzdálené HA (generovaný dashboard), karta se znovu registruje (polyfill scoped registry ztrácel brzkou definici)
