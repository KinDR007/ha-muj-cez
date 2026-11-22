# Entity

Názvy entit jsou v češtině nebo angličtině podle jazyka Home Assistantu.

## Odběrné místo

| Senzor | Význam |
|---|---|
| Predikce vyúčtování | očekávaný výsledek vyúčtování, záporné číslo = přeplatek |
| Predikované náklady / spotřeba za období | odhad ČEZ za celé zúčtovací období |
| Aktuální / doporučená záloha | výše zálohy a doporučení ČEZ |
| Splatnost a výše příští zálohy | atributy obsahují variabilní symbol a číslo účtu |
| Nezaplacené zálohy, Částka po splatnosti | dlužné částky |
| Poslední faktura / platba | poslední doklady |
| Stav elektroměru | poslední odečet (u dvoutarifu VT, NT v atributu `low_tariff`) |
| Stav elektroměru NT | jen dvoutarif: nízký tarif posledního odečtu |
| Spotřeba a náklady za minulé období | uzavřené zúčtovací období |
| Distribuční sazba, Hlavní jistič, Konec smlouvy, Datum změny ceny | údaje ze smlouvy |
| Plánované odstávky | odstávky distribuce, seznam v atributu `outages` |
| Zúčtovací období | historie období v atributu `periods`: spotřeba, náklady, zálohy, vyúčtování, Kč/kWh; `invoices_updated` = poslední kontrola faktur |
| Odchylka od ČEZ | porovnání s referenčním senzorem v %, data pro grafy v atributech |

Tlačítko **Aktualizovat faktury** (jen se zapnutým cenovým rozpadem) hned stáhne nové
faktury a ceníky odběrného místa.

Diagnostické entity: EAN, číslo elektroměru, číslo smlouvy, zákaznické číslo, produkt,
čas poslední aktualizace.

## Plyn

Plynové odběrné místo má stejné senzory vyúčtování, záloh, dokladů a období (spotřeba
v kWh, jak je účtuje ČEZ). Místo stavu elektroměru má **Stav plynoměru** v m³ (typ plyn,
lze použít v panelu Energie) s historií odečtů v atributu `readings` (stav, spotřeba
v m³ od předchozího odečtu, po výměně plynoměru prázdná) a diagnostiku **Číslo plynoměru**.
Jistič, HDO, aktuální cena, průběhová data, cenový rozpad a odečet z Home Assistantu
u plynu nejsou; porovnání s referenčním senzorem HA se nepočítá (ten měří elektřinu).

Verze před 1.6 vytvářely u plynu stav elektroměru v kWh a hlavní jistič 0 A. Tyto
entity se po aktualizaci odstraní; jejich dlouhodobé statistiky lze smazat v
**Vývojářské nástroje → Statistiky**.

## Průběhové měření a fotovoltaika

Pokud portál pro odběrné místo eviduje průběhová data elektroměru, přibudou senzory
**Odběr ze sítě** a **Přetoky do sítě** (tento měsíc, letos), **Data elektroměru k**
a **Spotová cena včera**. Integrace také importuje hodinové statistiky odběru a přetoků,
které jdou vybrat v panelu **Energie**, a spotové ceny. Data jsou den zpětně.

Výrobní místo (výkup přetoků) má vlastní zařízení se senzory **Výkup za poslední měsíc**,
**Výkup letos** a **Výkupní cena**.

Bez průběhových dat se nic z toho nevytvoří.

## HDO a aktuální cena

S volbou **HDO z ČEZ Distribuce**: **Tarif (HDO)** (NT/VT, v atributech dnešní a zítřejší
časy NT), **Příští přepnutí tarifu** a **Aktuální cena** (Kč/kWh s DPH za aktuální tarif
podle poslední simulace vyúčtování, bez stálých plateb). Rozpis se ukládá asi na týden
dopředu, tarif se tedy přepíná včas i bez spojení s portálem. Odběrná místa bez HDO
(jednotarif, jiný distributor) tyto senzory nedostanou, cenu ano.

## Účet

- **Doklady** (kalendář): všechny doklady všech smluv na účtu (faktury, zálohy, platby,
  poplatky). Kliknutím na událost se zobrazí podrobnosti (smlouva, číslo dokladu, data,
  variabilní symbol).
- **Nepřečtené zprávy** z portálu.
- **Jednotka grafů** (výběr kWh / Kč): přepíná grafy dashboardu.
