# Dashboard examples

Entity IDs below assume the supply point named "Domov" (entity IDs `sensor.cez_domov_*`) and the account device
"Můj ČEZ". Adjust them to your installation (Settings → Entities, search "ČEZ").

## Billing periods table

Closed periods come from the portal consumption history; the last row is the current
period with the portal's prediction. `paid` is the sum of payments dated within the
period, `settlement` is the invoice issued after the period (negative = overpayment).
`advances_total` is the advance amount for the whole period: for closed periods what the
settlement credited (cost - settlement, so it includes state contributions or carried over
overpayments), for the current period the advance plan total; `advances_remaining` and
`advances_remaining_count` are the advances still to be paid in the current period,
`advances_installment` the amount of one of them when they are all equal.

```yaml
type: markdown
title: Zúčtovací období
content: |
  {% set periods = state_attr('sensor.cez_domov_zuctovaci_obdobi', 'periods') or [] %}
  | Období | Spotřeba | Náklady | Zálohy za období | Vyúčtování | Kč/kWh |
  |:--|--:|--:|--:|--:|--:|
  {% for p in periods | reverse %}{% set s = p.settlement %}| {{ (p['from'] | as_datetime).strftime('%d.%m.%Y') }} – {{ (p['to'] | as_datetime).strftime('%d.%m.%Y') }}{{ ' *(predikce)*' if p.predicted }} | {{ '%.0f' | format(p.consumption_kwh or 0) }} kWh | {{ '%.0f' | format(p.cost or 0) }} Kč | {% set a = p.advances_total if p.advances_total is not none else p.paid %}{{ ('%.0f' | format(a)) ~ ' Kč' if a is not none else '–' }} | {% if s is none %}–{% elif s < 0 %}přeplatek {{ '%.0f' | format(-s) }} Kč{% else %}doplatek {{ '%.0f' | format(s) }} Kč{% endif %} | {{ p.avg_price if p.avg_price is not none else '–' }} |
  {% endfor %}
```

## Documents calendar

All documents of all contracts (invoices, advances, payments, fees, reminders, ...).
Click an event for details (contract, document number, dates, variable symbol).

```yaml
type: calendar
initial_view: dayGridMonth
entities:
  - calendar.muj_cez_doklady
```

## Querying documents

Developer tools → Actions → `Můj ČEZ: Načíst doklady` (`muj_cez.get_documents`):

```yaml
action: muj_cez.get_documents
data:
  document_type: Faktura
  date_from: "2020-01-01"
  limit: 50
```

Example automation: notify about unpaid documents after due date.

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

## VRM style view (Dashboard Editor model)

The ČEZ view for dashboards managed by the Dashboard Editor app (model in
`/addon_configs/local_dashboard_editor/dashboards/*.yaml` is the source of truth; the editor
renders it with viewlib and publishes it). Editing the Lovelace config directly would be
overwritten by the next publish from the editor, so the view goes into the model:

```bash
CEZ_PREFIX=sensor.cez_domov_ .venv/bin/python tools/dashboard/build_cez_view.py view.json
HA_HOST=<ha> HA_SSH_PASS=... HA_TOKEN=... EDITOR_DIR=<path to dashboard_editor_app> \
  .venv/bin/python tools/dashboard/push_to_editor.py view.json --dry-run   # then without --dry-run
```

`build_cez_view.py` outputs an editor model view: `block` cards (head value/extra and rows as
JS bodies, 30-day mini-graph as an embedded card), headings and the calendar. JS bodies use
full entity IDs (validated by the editor's check, tracked by button-card) and helper names
that do not clash with the helpers viewlib adds (n, f, st, u, cz, dashTap).

`push_to_editor.py` refuses to run when the live dashboard was changed outside the editor in
another view, validates schema and entities with the editor's own checks, backs up the live
config (editor `backups/` and local `.backup/`), saves the model with a history version,
publishes and updates the editor's published state (so the editor does not report a conflict).

Charts are drawn by button-card (no fixed time window, so the x axis follows the billing
period): monthly ČEZ vs HA for the current period with estimate to the end, year-over-year by
billing-period month, period totals and the meter reading check. The kWh/Kč pills switch
`select.muj_cez_jednotka_grafu`; hovering (or tapping on mobile) a column shows its values.

`tools/dashboard/ha_ws.py` sends raw websocket messages with a long-lived token in `HA_TOKEN`.
