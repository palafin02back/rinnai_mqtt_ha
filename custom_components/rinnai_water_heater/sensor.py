"""Support for Rinnai Water Heater sensors."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import RinnaiDataUpdateCoordinator

@dataclass
class RinnaiSensorEntityDescription(SensorEntityDescription):
    """Class describing Rinnai sensor entities."""

    value_fn: callable[[dict[str, Any]], StateType] = None

SENSORS: tuple[RinnaiSensorEntityDescription, ...] = (
    RinnaiSensorEntityDescription(
        key="current_temperature",
        name="Current Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("current_temperature"),
    ),
    RinnaiSensorEntityDescription(
        key="target_temperature",
        name="Target Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("target_temperature"),
    ),
)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Rinnai sensors."""
    coordinator: RinnaiDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        RinnaiSensor(coordinator, description)
        for description in SENSORS
    )

class RinnaiSensor(CoordinatorEntity[RinnaiDataUpdateCoordinator], SensorEntity):
    """Representation of a Rinnai sensor."""

    entity_description: RinnaiSensorEntityDescription

    def __init__(
        self,
        coordinator: RinnaiDataUpdateCoordinator,
        description: RinnaiSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.rinnai_client._device_data.get('device_sn', '')}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.rinnai_client._device_data.get("device_sn", ""))},
            "name": "Rinnai Water Heater",
            "manufacturer": "Rinnai",
            "model": coordinator.rinnai_client._device_data.get("device_type", ""),
        }

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        return self.entity_description.value_fn(self.coordinator.data) 