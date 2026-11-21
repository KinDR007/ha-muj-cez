# Pro pokročilé

Technické podrobnosti pro automatizace, vlastní karty a šablony.

## Atributy senzorů odběrného místa

| Senzor | Jednotka | Atributy a poznámky |
|---|---|---|
| Predikce vyúčtování | Kč | záporné číslo = přeplatek, kladné = doplatek |
| Predikované náklady za období | Kč | s DPH, `cost_without_tax` |
| Predikovaná spotřeba za období | kWh | `measured`, `estimated` |
| Konec zúčtovacího období | datum | |
| Splatnost / výše příští zálohy | datum / Kč | `variable_symbol`, `bank_account` |
| Nezaplacené zálohy | Kč | dlužná částka po splatnosti |
| Spotřeba / náklady za minulé období | kWh / Kč | poslední uzavřené zúčtovací období |
| Stav elektroměru | kWh | poslední skutečný odečet (VT), `total_increasing`, `low_tariff` |
| Stav elektroměru NT | kWh | jen dvoutarif: registr NT posledního odečtu |
| Poslední faktura | Kč | záporné číslo = přeplatek; číslo dokladu, datum vystavení a splatnosti |
| Poslední platba | Kč | datum |
| Částka po splatnosti | Kč | neuhrazené doklady po splatnosti, `open_amount` |
| Distribuční sazba | text | např. `D02d - Běžná domácnost…`, `tariff_code`, `recommended` |
| Hlavní jistič | A | `phase` (hodnota z portálu) |
| Konec smlouvy / Datum změny ceny | datum | konec smlouvy na dobu určitou, plánovaná změna ceny |
| Plánované odstávky | počet | seznam v `outages` |
| Zúčtovací období | počet | `periods`: spotřeba, náklady, zaplaceno, zálohy za celé období (`advances_total`, u běžného zbývá), vyúčtování, Kč/kWh; poslední položka je běžné období (predikce) |
| Odběr / přetoky tento měsíc, letos | kWh | jen s průběhovým měřením |
| Data elektroměru k | datum | poslední den s průběhovými daty; `months`, `import_comparison`, `export_comparison`, `payouts`, `statistics` |
| Spotová cena včera | Kč/kWh | průměr, `min`, `max` |

Výrobní odběrné místo (výkup přetoků) má zařízení **ČEZ &lt;adresa&gt; výroba** se senzory
**Výkup za poslední měsíc**, **Výkup letos** a **Výkupní cena** (výkup / kWh přetoků);
atribut `payouts` obsahuje každý měsíc s kWh přetoků, cenou a hodnotou přetoků za spotovou
cenu. Zálohy, predikce ani stav elektroměru se pro něj nevytváří.

Kalendář **Doklady** má jednu celodenní událost na doklad v den splatnosti (nebo vystavení);
popis události obsahuje smlouvu, číslo dokladu, data, zbývající částku a variabilní symbol.
Zahrnuje i ukončené smlouvy.

## Průběhová data a statistiky

Pokud portál pro odběrné místo eviduje průběhová data, integrace navíc:

- ukládá denní odběr a přetoky (historie od začátku dat, pak jen nové dny),
- importuje hodinové dlouhodobé statistiky `muj_cez:grid_import_<místo>`
  a `muj_cez:grid_export_<místo>` pro panel Energie (zpoždění asi den),
- importuje hodinové spotové ceny `muj_cez:spot_price` (Kč/kWh) z denního trhu
  [OTE](https://www.ote-cr.cz) přepočtené kurzem ČNB (shodné s cenami, které portál ČEZ
  ukazoval do září 2025), portál je jen záloha; vždy do včerejška,
- oceňuje přetoky po měsících spotovou cenou (srovnání s výkupem); hodiny bez cen z portálu
  doplní volitelný senzor spotové ceny (jen pokud sahají jeho statistiky),
- ukládá čtvrthodinové hodnoty aktuálního měsíce a 12 předchozích
  (`.storage/muj_cez.<entry>.profile_*`, pod 1 MB, starší dny se mažou) pro sekci
  *Průběh po 15 minutách*.

První běh stáhne historii na pozadí (desítky dotazů, několik minut). Účty bez průběhových
dat se ověřují jednou za měsíc a nic dalšího se pro ně nestahuje.

## HDO

Časy spínání nízkého a vysokého tarifu nejsou na muj.cez.cz, načítají se z portálu
[ČEZ Distribuce](https://dip.cezdistribuce.cz) se stejnými přihlašovacími údaji. Přihlášení
a endpointy vycházejí z [MattXcz/CEZ](https://github.com/MattXcz/CEZ) (MIT).

- **Tarif (HDO)**: `low` / `high`; atributy `today`, `tomorrow` (intervaly NT),
  `low_hours_today`, `signal`, `schedule_until`.
- **Příští přepnutí tarifu**: časové razítko.
- **Aktuální cena** (Kč/kWh s DPH): cena aktuálního tarifu z položek poslední simulace
  vyúčtování (silová elektřina + distribuce, bez stálých plateb); atributy `price_vt`,
  `price_nt`. Jednotarifová místa ji mají i bez HDO.

Rozpis (asi 7 dní dopředu) se načítá při startu, s pravidelnou aktualizací a denně v 0:20
a ukládá se, takže tarif se přepíná včas i bez portálu a vydrží několikadenní výpadek.

## Porovnání s měřením v Home Assistantu

S **referenčním senzorem odběru** integrace jednou denně načte jeho denní statistiky
a porovná je s portálem:

- **Odchylka od ČEZ**: HA proti ČEZ v % za běžné období do posledního odečtu. Atributy pro
  grafy: `current`, `months` (měsíční rozpis portálu proti HA, odhadnuté měsíce označené),
  `periods` (zúčtovací období ČEZ proti HA; běžné = naměřeno HA + odhad portálu do konce),
  `readings` (rozdíl mezi odečty proti HA), `ha_months` (HA po měsících pro meziroční
  srovnání).
- **Jednotka grafů** (kWh / Kč) na zařízení účtu přepíná karty dashboardu.

Odečet s datem D se bere jako stav elektroměru na konci dne D (stejně jako zúčtovací
období). Kč pro HA se počítají cenou portálu za stejný měsíc nebo období (náklady včetně
stálých plateb / kWh).

## Dashboard a karty

Dashboard se generuje z entit tohoto Home Assistantu (funguje i s přejmenovanými entitami
a jiným jazykem) a integrace přidává nebo nahrazuje jen své záložky (`cez`, `cez-ceny`,
`cez-odecet`). Potřebné karty (button-card, stack-in-card, mini-graph-card) instaluje přes
Marketplace nebo HACS jejich vlastním příkazem, takže je dál aktualizují; jinak stáhne
poslední vydání z GitHubu do `/config/www/muj_cez/cards/` a zaregistruje zdroj Lovelace.

Karta odečtu `custom:muj-cez-reading-card` je součástí integrace (volby `entry_id`, `ean`,
`title`).

## Websocket příkazy

| Příkaz | Účel |
|---|---|
| `muj_cez/profile` | 15minutové hodnoty jednoho měsíce (`entity_id` senzoru *Data elektroměru k*, volitelně `month` `YYYY-MM`) |
| `muj_cez/prices` | cenový rozpad odběrného místa (`entity_id` senzoru místa) |
| `muj_cez/reading_form`, `muj_cez/reading_check`, `muj_cez/reading_submit` | formulář odečtu, kontrola hodnot, odeslání (jen administrátor) |

Popis API portálu Můj ČEZ: [docs/api](../api/README.md).
