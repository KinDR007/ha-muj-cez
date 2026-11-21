# Řešení potíží

## Oznámení v Nastavení → Opravy

- **Dashboard Můj ČEZ potřebuje karty**: záložce ČEZ chybí některá z karet button-card,
  stack-in-card nebo mini-graph-card. Tlačítko **Opravit** je nainstaluje přes Market nebo
  HACS, jinak z GitHubu. Po instalaci obnovte stránku prohlížeče.
- **Dashboard Můj ČEZ se nepodařilo vytvořit**: zvolený dashboard nejde upravit (například
  je v režimu YAML nebo ho generuje strategie). Vyberte v [nastavení](nastaveni.md) jiný
  dashboard nebo **Nový dashboard „ČEZ“**.

## Přihlášení

Po změně hesla na portálu zobrazí Home Assistant výzvu k novému přihlášení; stačí zadat
nové heslo. Když přihlášení selhává i se správnými údaji, ověřte, že se stejnými údaji
přihlásíte na muj.cez.cz; portál může být dočasně nedostupný.

## Data se neaktualizují

- Data se načítají podle zvolené periody a při startu Home Assistantu. Neúspěšná
  aktualizace se zkouší znovu 6× po 30 minutách.
- Ručně: **Nastavení → Zařízení a služby → Můj ČEZ → ⋮ u účtu → Nově načíst**.
- Průběhová data elektroměru jsou na portálu den zpětně.

## Karta se nezobrazuje nebo hlásí „Chyba nastavení“

Po aktualizaci integrace obnovte stránku prohlížeče (případně vymažte mezipaměť aplikace
Home Assistant v mobilu), aby se načetly nové karty.

## Cenový rozpad je prázdný nebo neúplný

- Zkontrolujte, že je v [nastavení](nastaveni.md) zapnutý **Cenový rozpad**.
- První stažení faktur běží na pozadí a může trvat několik minut.
- Faktura, kterou se nepodařilo zpracovat, se zkusí znovu po týdnu.

## Diagnostika pro nahlášení chyby

**Nastavení → Zařízení a služby → Můj ČEZ → ⋮ u účtu → Stáhnout diagnostická data** vytvoří soubor
s daty integrace a odpověďmi portálu. Jména, adresy, kontakty a všechny identifikátory
jsou nahrazené zástupnými hodnotami; data, kWh a číselníkové hodnoty zůstávají. Před
přiložením k chybě v [Issues](https://github.com/KinDR007/ha-muj-cez/issues) soubor
zkontrolujte. Šablona [nahlášení chyby](https://github.com/KinDR007/ha-muj-cez/issues/new/choose)
provede vším potřebným.

## Ladicí log

1. **Nastavení → Zařízení a služby → Můj ČEZ → menu ⋮ vpravo nahoře → Povolit protokolování
   ladících informací.**
2. Zopakujte chybu (u chyb při načítání dat: menu ⋮ u účtu → **Nově načíst**).
3. Stejnou položkou ladění vypněte; prohlížeč stáhne soubor s logem. Do hlášení vložte řádky
   s `muj_cez` a zkontrolujte, že neobsahují osobní údaje.

Bez ladění jsou logy v **Nastavení → Systém → Protokoly → Zobrazit nezpracované protokoly**.
Trvale zapnutý podrobný log jde nastavit v `configuration.yaml`:

```yaml
logger:
  logs:
    custom_components.muj_cez: debug
```
