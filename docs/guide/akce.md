# Akce a automatizace

Akce se spouštějí ve **Vývojářské nástroje → Akce** nebo z automatizací a skriptů.

## Načíst doklady (`muj_cez.get_documents`)

Vrátí účetní doklady (faktury, zálohy, platby, poplatky) všech smluv účtu, od nejnovějších.
Všechny parametry jsou nepovinné:

| Parametr | Význam |
|---|---|
| `config_entry_id` | účet, pokud je jich víc |
| `date_from`, `date_to` | jen doklady se splatností nebo vystavením v tomto rozsahu |
| `document_type` | část názvu typu dokladu, např. `Faktura`, `Záloha`, `Platba` |
| `contract` | číslo smlouvy nebo část jejího názvu |
| `unpaid_only` | jen doklady se zbývající částkou k úhradě |
| `limit` | maximální počet dokladů (výchozí 100, nejvýš 1000) |

```yaml
action: muj_cez.get_documents
data:
  document_type: Faktura
  date_from: "2024-01-01"
  limit: 50
```

## Aktualizovat dashboard (`muj_cez.update_dashboard`)

Znovu vygeneruje záložky ČEZ ve zvoleném dashboardu podle aktuálních entit. Hodí se po
ruční úpravě dashboardu nebo po přidání referenčního senzoru.

```yaml
action: muj_cez.update_dashboard
```

## Příklad: upozornění na neuhrazené doklady po splatnosti

```yaml
alias: ČEZ – neuhrazené doklady po splatnosti
triggers:
  - trigger: numeric_state
    entity_id: sensor.cez_domov_castka_po_splatnosti
    above: 0
actions:
  - action: muj_cez.get_documents
    data:
      unpaid_only: true
    response_variable: docs
  - action: persistent_notification.create
    data:
      title: ČEZ – neuhrazeno po splatnosti
      message: >-
        {% for d in docs.documents %}
        {{ d.type }} {{ d.number }}: {{ d.balance }} Kč, splatnost {{ d.due_date }}
        {% endfor %}
```

Název senzoru `sensor.cez_domov_castka_po_splatnosti` nahraďte svým (najdete ho u zařízení
odběrného místa jako **Částka po splatnosti**).

## Příklad: připomenutí zálohy

Senzor splatnosti příští zálohy má v atributech `variable_symbol` a `bank_account`, které
jde použít v upozornění na platbu.

## Další karty

Jednoduché karty bez dalších závislostí (tabulka zúčtovacích období, kalendář dokladů) jsou
v [docs/dashboard.md](../dashboard.md).
