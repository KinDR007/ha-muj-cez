"""Tests of pure parsing functions against recorded (sanitized) responses."""

from datetime import date

from custom_components.muj_cez import api

from .conftest import TODAY, UID, load


def test_supply_points() -> None:
    [sp] = api.parse_supply_points(load("supply_points.json"))
    assert sp.uid == UID
    assert sp.ean == "859100000000000001"
    assert sp.address == "Testovací 123, Praha"
    assert sp.advance_amount == 1450.0
    assert sp.product == "ELE_REFIX_2_E"


def test_supply_points_skips_incomplete() -> None:
    assert api.parse_supply_points([{"supplyPointCode": "x"}, {}]) == []
    assert api.parse_supply_points(None) == []


def test_simulation() -> None:
    sim = api.parse_simulation(load("simulation.json"))
    assert sim.total_amount == -1947.99
    assert sim.cost_with_tax == 14002.01
    assert sim.recommended_advance == 480
    assert sim.period_from == date(2026, 2, 18)
    assert sim.period_to == date(2027, 2, 15)
    assert sim.consumption_measured_kwh == 1284
    assert sim.consumption_estimated_kwh == 537.99
    assert sim.consumption_kwh == 1821.99


def test_simulation_empty() -> None:
    assert api.parse_simulation({}) is None
    sim = api.parse_simulation({"invoiceSimulationBillingPeriodTo": "bad"})
    assert sim.period_to is None
    assert sim.total_amount is None
    assert sim.cost_with_tax is None


def test_advance_plan() -> None:
    plan = api.parse_advance_plan(load("advance_plan.json"), TODAY)
    assert plan.total_count == 11
    assert plan.paid_count == 8
    assert plan.next_due_date == date(2026, 11, 16)
    assert plan.next_amount == 1450
    assert plan.unpaid_amount == 0


def test_advance_plan_unpaid_overdue() -> None:
    rows = [
        {"splatnost": "2026-10-15", "castka": 100, "kDoplaceni": 100, "stav": 0},
        {"splatnost": "2026-12-15", "castka": 200, "kDoplaceni": 200, "stav": 0},
    ]
    plan = api.parse_advance_plan(rows, TODAY)
    assert plan.unpaid_amount == 100
    assert plan.next_due_date == date(2026, 12, 15)
    assert plan.next_amount == 200


def test_consumption_history_takes_latest() -> None:
    period = api.parse_consumption_history(load("consumption_history.json"))
    assert period.date_to == date(2026, 2, 17)
    assert period.consumption_kwh == 1163
    assert period.amount == 10764.77
    assert api.parse_consumption_history([]) is None


def test_meter_reading_ignores_simulated_and_future() -> None:
    reading = api.parse_meter_readings(load("meter_readings.json"), TODAY)
    assert reading.reading_date == TODAY
    assert reading.value_ht == 12882
    assert reading.value_lt is None
    assert reading.device == "1000000001"


def test_meter_reading_before_any() -> None:
    assert api.parse_meter_readings(load("meter_readings.json"), date(2000, 1, 1)) is None
    assert api.parse_meter_readings("bad", TODAY) is None


def test_contract_info() -> None:
    info = api.parse_contract_info(load("contract_detail.json"), load("distribution_rate.json"))
    assert info.circuit_breaker == 25
    assert info.tariff_code == "D02D"
    assert info.contract_end == date(2027, 7, 16)
    assert info.price_change_date == date(2027, 7, 17)
    assert info.double_tariff is False
    assert info.distribution_rate.startswith("D02d")
    assert api.parse_contract_info({}, None) is None
    only_rate = api.parse_contract_info(None, load("distribution_rate.json"))
    assert only_rate.circuit_breaker is None
    assert only_rate.distribution_rate.startswith("D02d")


def test_advance_settings() -> None:
    s = api.parse_advance_settings(load("advance_settings.json"), load("advance_events.json"))
    assert s.is_sipo is False
    assert (s.min_amount, s.max_amount, s.remaining_payments) == (480, 14500, 3)
    assert s.variable_symbol == "1111111100"
    assert s.bank_account == "7770227/0100"
    without_events = api.parse_advance_settings(load("advance_settings.json"), None)
    assert without_events.variable_symbol is None
    assert api.parse_advance_settings({}, None) is None


def test_billings_filters_agreement() -> None:
    b = api.parse_billings(load("billings.json"), "000011111111", TODAY)
    assert b.last_invoice.amount == -4385.23
    assert b.last_invoice.issue_date == date(2026, 2, 19)
    assert b.last_payment.amount == 1450
    assert b.last_payment.issue_date == date(2026, 10, 15)
    assert b.overdue_amount == 0
    assert b.open_amount == 4350
    assert api.parse_billings(load("billings.json"), "nonexistent", TODAY) is None
    assert api.parse_billings(None, "000011111111", TODAY) is None


def test_billings_overdue() -> None:
    later = date(2027, 1, 1)
    b = api.parse_billings(load("billings.json"), "000011111111", later)
    assert b.overdue_amount == 2900


def test_outages() -> None:
    outages = api.parse_outages(load("outages.json"), "859100000000000001")
    assert len(outages) == 1
    assert outages[0].start_date == date(2026, 12, 3)
    assert outages[0].reason == "Údržba zařízení"
    assert api.parse_outages({"outages": []}, "x") == []
    assert api.parse_outages({}, "x") is None


def test_unread_messages() -> None:
    assert api.parse_unread_messages(load("messages_summary.json")) == 2
    assert api.parse_unread_messages({}) is None


def test_strip_zeros() -> None:
    assert api.strip_zeros("000012345678") == "12345678"
    assert api.strip_zeros("0000") is None
    assert api.strip_zeros(None) is None


def _docs() -> list[api.BillingDocument]:
    sp = api.parse_supply_points(load("supply_points.json"))[0]
    names = api.contract_names([sp], load("historical_supply_points.json"))
    return api.parse_documents(load("billings.json"), names)


def test_contract_names() -> None:
    sp = api.parse_supply_points(load("supply_points.json"))[0]
    names = api.contract_names([sp], load("historical_supply_points.json"))
    assert names == {
        "000011111111": "Testovací 123",
        "000044444444": "Testovací 123 (plyn, ukončeno)",
    }
    assert api.contract_names([], None) == {}


def test_parse_documents() -> None:
    docs = _docs()
    assert len(docs) == 45
    dates = [d.event_date for d in docs]
    assert dates == sorted(dates)
    payments = [d for d in docs if d.is_payment]
    assert payments and all(d.amount > 0 for d in payments)
    invoice = next(d for d in docs if d.is_invoice and d.issue_date == date(2026, 2, 19))
    assert invoice.amount == -4385.23
    assert invoice.event_date == invoice.due_date
    gas = [d for d in docs if d.agreement_id == "000044444444"]
    assert {d.contract_name for d in gas} == {"Testovací 123 (plyn, ukončeno)"}
    assert api.parse_documents(None) == []


def test_parse_documents_unknown_contract_label() -> None:
    [doc] = api.parse_documents(
        [{"agreementIdIsu": "000099999999", "billingAccountingDocumentTypeText": "Platba"}]
    )
    assert doc.contract_name == "Smlouva 99999999"
    assert doc.amount is None
    assert doc.event_date is None


def test_billing_periods() -> None:
    docs = _docs()
    history = api.parse_consumption_periods(load("consumption_history.json"))
    sim = api.parse_simulation(load("simulation.json"))
    plan = api.parse_advance_plan(load("advance_plan.json"), TODAY)
    periods = api.build_billing_periods(history, docs, "000011111111", sim, plan)
    assert len(periods) == 5
    oldest, *_, last_closed, current = periods
    # No documents in the fixture for the oldest period.
    assert oldest.paid is None
    assert oldest.settlement is None
    assert oldest.avg_price == 8.58
    assert last_closed.date_to == date(2026, 2, 17)
    assert last_closed.paid == 15150
    assert last_closed.settlement == -4385.23
    assert last_closed.settlement_date == date(2026, 2, 19)
    assert current.predicted
    assert current.settlement == -1947.99
    assert current.paid == 11600
    # Advances: closed = credited in the settlement, current = advance plan.
    assert oldest.advances_total is None
    assert last_closed.advances_total == 15150
    assert periods[2].paid == 9000
    assert periods[2].advances_total == 16519.57
    assert current.advances_total == 15950
    assert current.advances_remaining == 4350
    assert current.advances_remaining_count == 3
    assert current.advances_installment == 1450
    assert current.as_dict()["advances_remaining_count"] == 3
    assert api.build_billing_periods([], docs, "000011111111", None) == []


def test_billing_periods_without_plan() -> None:
    """Current period falls back to the portal prediction (cost - settlement)."""
    sim = api.parse_simulation(load("simulation.json"))
    [current] = api.build_billing_periods([], _docs(), "000011111111", sim)
    assert current.advances_total == 15950
    assert current.advances_remaining is None
    assert current.advances_remaining_count is None
    assert current.advances_installment is None


def test_billing_periods_plan_outside_period() -> None:
    """Plan items due outside the current period are ignored."""
    sim = api.parse_simulation(load("simulation.json"))
    rows = [
        {"splatnost": "2026-01-15", "castka": 999, "kDoplaceni": 0, "stav": 1},
        {"splatnost": "2026-12-15", "castka": 1450, "kDoplaceni": 1450, "stav": 2},
        {"splatnost": "2027-03-15", "castka": 999, "kDoplaceni": 999, "stav": 2},
    ]
    plan = api.parse_advance_plan(rows, TODAY)
    [current] = api.build_billing_periods([], _docs(), "000011111111", sim, plan)
    assert current.advances_total == 1450
    assert current.advances_remaining == 1450
    assert current.advances_remaining_count == 1
    assert current.advances_installment == 1450


def test_billing_periods_unequal_advances() -> None:
    """No single installment amount when the remaining advances differ."""
    sim = api.parse_simulation(load("simulation.json"))
    rows = [
        {"splatnost": "2026-11-16", "castka": 1450, "kDoplaceni": 1450, "stav": 2},
        {"splatnost": "2026-12-15", "castka": 1600, "kDoplaceni": 1600, "stav": 2},
    ]
    plan = api.parse_advance_plan(rows, TODAY)
    [current] = api.build_billing_periods([], _docs(), "000011111111", sim, plan)
    assert current.advances_remaining == 3050
    assert current.advances_remaining_count == 2
    assert current.advances_installment is None
