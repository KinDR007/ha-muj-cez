"""Sensors for the Muj CEZ integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfElectricCurrent, UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import BillingDocument, CezData, SupplyPointData, strip_zeros
from .const import DOMAIN, MANUFACTURER, PORTAL_URL
from .coordinator import MujCezConfigEntry, MujCezCoordinator
from .entity import account_device_info

PARALLEL_UPDATES = 0
CURRENCY = "CZK"


@dataclass(frozen=True, kw_only=True)
class MujCezSensorDescription(SensorEntityDescription):
    value_fn: Callable[[MujCezCoordinator, SupplyPointData], StateType | date | datetime]
    attrs_fn: Callable[[SupplyPointData], dict[str, Any]] | None = None


def _money(
    key: str, fn: Callable[[SupplyPointData], float | None], **kw: Any
) -> MujCezSensorDescription:
    return MujCezSensorDescription(
        key=key,
        translation_key=key,
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement=CURRENCY,
        suggested_display_precision=0,
        value_fn=lambda _c, d: fn(d),
        **kw,
    )


def _energy(
    key: str, fn: Callable[[SupplyPointData], float | None], **kw: Any
) -> MujCezSensorDescription:
    return MujCezSensorDescription(
        key=key,
        translation_key=key,
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=0,
        value_fn=lambda _c, d: fn(d),
        **kw,
    )


def _date(
    key: str, fn: Callable[[SupplyPointData], date | None], **kw: Any
) -> MujCezSensorDescription:
    return MujCezSensorDescription(
        key=key,
        translation_key=key,
        device_class=SensorDeviceClass.DATE,
        value_fn=lambda _c, d: fn(d),
        **kw,
    )


def _info(
    key: str, fn: Callable[[SupplyPointData], str | None], **kw: Any
) -> MujCezSensorDescription:
    return MujCezSensorDescription(
        key=key,
        translation_key=key,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda _c, d: fn(d),
        **kw,
    )


def _doc_attrs(doc: BillingDocument | None) -> dict[str, Any]:
    if doc is None:
        return {}
    return {
        "document_type": doc.doc_type,
        "document_number": doc.number,
        "issue_date": doc.issue_date,
        "due_date": doc.due_date,
    }


SENSORS: tuple[MujCezSensorDescription, ...] = (
    # Invoice prediction
    _money(
        "invoice_balance",
        lambda d: d.simulation and d.simulation.total_amount,
        attrs_fn=lambda d: (
            {
                "period_from": d.simulation.period_from,
                "period_to": d.simulation.period_to,
                "calculated_at": d.simulation.calculated_at,
            }
            if d.simulation
            else {}
        ),
    ),
    _money(
        "predicted_cost",
        lambda d: d.simulation and d.simulation.cost_with_tax,
        attrs_fn=lambda d: (
            {"cost_without_tax": d.simulation.cost_without_tax} if d.simulation else {}
        ),
    ),
    _energy(
        "predicted_consumption",
        lambda d: d.simulation and d.simulation.consumption_kwh,
        attrs_fn=lambda d: (
            {
                "measured": d.simulation.consumption_measured_kwh,
                "estimated": d.simulation.consumption_estimated_kwh,
            }
            if d.simulation
            else {}
        ),
    ),
    _date(
        "billing_period_end",
        lambda d: d.simulation and d.simulation.period_to,
        attrs_fn=lambda d: {"period_from": d.simulation.period_from} if d.simulation else {},
    ),
    # Advance payments
    _money("recommended_advance", lambda d: d.simulation and d.simulation.recommended_advance),
    _money(
        "current_advance",
        lambda d: d.supply_point.advance_amount,
        attrs_fn=lambda d: {
            "frequency": d.supply_point.advance_frequency,
            **(
                {
                    "sipo": d.advance_settings.is_sipo,
                    "min_amount": d.advance_settings.min_amount,
                    "max_amount": d.advance_settings.max_amount,
                    "remaining_payments": d.advance_settings.remaining_payments,
                }
                if d.advance_settings
                else {}
            ),
        },
    ),
    _date(
        "next_advance_date",
        lambda d: d.advance_plan and d.advance_plan.next_due_date,
        attrs_fn=lambda d: {
            **(
                {
                    "amount": d.advance_plan.next_amount,
                    "paid_count": d.advance_plan.paid_count,
                    "total_count": d.advance_plan.total_count,
                }
                if d.advance_plan
                else {}
            ),
            **(
                {
                    "variable_symbol": d.advance_settings.variable_symbol,
                    "bank_account": d.advance_settings.bank_account,
                }
                if d.advance_settings
                else {}
            ),
        },
    ),
    _money("next_advance_amount", lambda d: d.advance_plan and d.advance_plan.next_amount),
    _money("unpaid_advances", lambda d: d.advance_plan and d.advance_plan.unpaid_amount),
    # Billing documents
    _money(
        "last_invoice",
        lambda d: d.billing and d.billing.last_invoice and d.billing.last_invoice.amount,
        attrs_fn=lambda d: _doc_attrs(d.billing and d.billing.last_invoice),
    ),
    _money(
        "last_payment",
        lambda d: d.billing and d.billing.last_payment and d.billing.last_payment.amount,
        attrs_fn=lambda d: _doc_attrs(d.billing and d.billing.last_payment),
    ),
    _money(
        "overdue_amount",
        lambda d: d.billing and d.billing.overdue_amount,
        attrs_fn=lambda d: {"open_amount": d.billing.open_amount} if d.billing else {},
    ),
    # Consumption and meter
    _energy(
        "last_period_consumption",
        lambda d: d.last_period and d.last_period.consumption_kwh,
        attrs_fn=lambda d: (
            {
                "date_from": d.last_period.date_from,
                "date_to": d.last_period.date_to,
                "high_tariff": d.last_period.consumption_ht_kwh,
                "low_tariff": d.last_period.consumption_lt_kwh,
            }
            if d.last_period
            else {}
        ),
    ),
    _money(
        "last_period_cost",
        lambda d: d.last_period and d.last_period.amount,
        attrs_fn=lambda d: (
            {"date_from": d.last_period.date_from, "date_to": d.last_period.date_to}
            if d.last_period
            else {}
        ),
    ),
    _energy(
        "meter_reading",
        lambda d: d.meter_reading and d.meter_reading.value_ht,
        state_class=SensorStateClass.TOTAL_INCREASING,
        attrs_fn=lambda d: (
            {
                "reading_date": d.meter_reading.reading_date,
                "reading_type": d.meter_reading.reading_type,
                "low_tariff": d.meter_reading.value_lt,
            }
            if d.meter_reading
            else {}
        ),
    ),
    # Contract and connection
    MujCezSensorDescription(
        key="distribution_rate",
        translation_key="distribution_rate",
        value_fn=lambda _c, d: (
            d.contract and (d.contract.distribution_rate or d.contract.tariff_code)
        ),
        attrs_fn=lambda d: (
            {
                "tariff_code": d.contract.tariff_code,
                "recommended": d.contract.recommended_distribution_rate,
                "double_tariff": d.contract.double_tariff,
            }
            if d.contract
            else {}
        ),
    ),
    MujCezSensorDescription(
        key="circuit_breaker",
        translation_key="circuit_breaker",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=0,
        value_fn=lambda _c, d: d.contract and d.contract.circuit_breaker,
        attrs_fn=lambda d: {"phase": d.contract.phase} if d.contract else {},
    ),
    _date("contract_end", lambda d: d.contract and d.contract.contract_end),
    _date("price_change_date", lambda d: d.contract and d.contract.price_change_date),
    MujCezSensorDescription(
        key="planned_outages",
        translation_key="planned_outages",
        value_fn=lambda _c, d: None if d.outages is None else len(d.outages),
        attrs_fn=lambda d: {
            "outages": [
                {
                    "start_date": o.start_date,
                    "start_time": o.start_time,
                    "end": o.end,
                    "reason": o.reason,
                }
                for o in d.outages or []
            ]
        },
    ),
    MujCezSensorDescription(
        key="billing_periods",
        translation_key="billing_periods",
        value_fn=lambda _c, d: (
            None if d.periods is None else sum(1 for p in d.periods if not p.predicted)
        ),
        attrs_fn=lambda d: {"periods": [p.as_dict() for p in d.periods or []]},
    ),
    # Identification
    _info("ean", lambda d: d.supply_point.ean),
    _info("meter_number", lambda d: d.meter_reading and d.meter_reading.device),
    _info("contract_number", lambda d: strip_zeros(d.supply_point.agreement_id)),
    _info("customer_number", lambda d: d.simulation and d.simulation.customer_number),
    _info(
        "product",
        lambda d: (d.contract and d.contract.product) or d.supply_point.product or None,
        attrs_fn=lambda d: {
            "product_code": d.supply_point.product,
            "commodity": d.supply_point.commodity,
            "continuous_measurement": d.supply_point.continuous_measurement,
            "electronic_invoicing": d.supply_point.electronic_invoicing,
            "address": d.supply_point.address,
        },
    ),
    MujCezSensorDescription(
        key="last_update",
        translation_key="last_update",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda c, _d: c.last_success_time,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MujCezConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    entities: list[SensorEntity] = [
        MujCezSensor(coordinator, uid, description)
        for uid in coordinator.data.supply_points
        for description in SENSORS
    ]
    entities.extend(
        MujCezComparisonSensor(coordinator, uid) for uid in coordinator.data.supply_points
    )
    entities.append(MujCezUnreadMessagesSensor(coordinator))
    async_add_entities(entities)


class MujCezSensor(CoordinatorEntity[MujCezCoordinator], SensorEntity):
    _attr_has_entity_name = True
    entity_description: MujCezSensorDescription

    def __init__(
        self, coordinator: MujCezCoordinator, uid: str, description: MujCezSensorDescription
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._uid = uid
        sp = coordinator.data.supply_points[uid].supply_point
        self._attr_unique_id = f"{uid}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, uid)},
            name=f"ČEZ {sp.name}",
            manufacturer=MANUFACTURER,
            model=sp.product or None,
            serial_number=sp.ean,
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=PORTAL_URL,
        )

    @property
    def _data(self) -> SupplyPointData | None:
        data: CezData | None = self.coordinator.data
        return data.supply_points.get(self._uid) if data else None

    @property
    def available(self) -> bool:
        # Keep the last known values when a scheduled update fails.
        return self._data is not None

    @property
    def native_value(self) -> StateType | date | datetime:
        data = self._data
        if data is None:
            return None
        return self.entity_description.value_fn(self.coordinator, data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        data = self._data
        if data is None or self.entity_description.attrs_fn is None:
            return None
        return self.entity_description.attrs_fn(data)


class MujCezUnreadMessagesSensor(CoordinatorEntity[MujCezCoordinator], SensorEntity):
    """Account level: unread messages in the portal."""

    _attr_has_entity_name = True
    _attr_translation_key = "unread_messages"

    def __init__(self, coordinator: MujCezCoordinator) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_unread_messages"
        self._attr_device_info = account_device_info(entry)

    @property
    def available(self) -> bool:
        return self.coordinator.data is not None

    @property
    def native_value(self) -> int | None:
        return self.coordinator.data.unread_messages if self.coordinator.data else None


class MujCezComparisonSensor(CoordinatorEntity[MujCezCoordinator], SensorEntity):
    """HA reference sensor vs portal: state is the deviation in % over the current
    period up to the last meter reading; attributes hold data for charts."""

    _attr_has_entity_name = True
    _attr_translation_key = "consumption_comparison"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_suggested_display_precision = 1

    def __init__(self, coordinator: MujCezCoordinator, uid: str) -> None:
        super().__init__(coordinator)
        self._uid = uid
        sp = coordinator.data.supply_points[uid].supply_point
        self._attr_unique_id = f"{uid}_consumption_comparison"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, uid)}, name=f"ČEZ {sp.name}")

    @property
    def _comparison(self) -> dict[str, Any] | None:
        data: CezData | None = self.coordinator.data
        return data.comparison.get(self._uid) if data else None

    @property
    def available(self) -> bool:
        return self._comparison is not None

    @property
    def native_value(self) -> float | None:
        comparison = self._comparison or {}
        return (comparison.get("current") or {}).get("diff_pct")

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        return self._comparison
