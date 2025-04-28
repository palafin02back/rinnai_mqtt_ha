"""Support for Rinnai Water Heater number entities."""
from __future__ import annotations

from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import RinnaiDataUpdateCoordinator

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Rinnai number entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([RinnaiTemperatureNumber(coordinator)])

class RinnaiTemperatureNumber(CoordinatorEntity[RinnaiDataUpdateCoordinator], NumberEntity):
    """Representation of a Rinnai temperature control."""

    def __init__(self, coordinator: RinnaiDataUpdateCoordinator) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._attr_name = "Target Temperature"
        self._attr_unique_id = f"{coordinator.rinnai_client._device_data.get('device_sn', '')}_target_temperature"
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_mode = NumberMode.SLIDER
        self._attr_native_min_value = 35
        self._attr_native_max_value = 65
        self._attr_native_step = 1
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.rinnai_client._device_data.get("device_sn", ""))},
            "name": "Rinnai Water Heater",
            "manufacturer": "Rinnai",
            "model": coordinator.rinnai_client._device_data.get("device_type", ""),
        }

    @property
    def native_value(self) -> float | None:
        """Return the current temperature."""
        return self.coordinator.data.get("target_temperature")

    async def async_set_native_value(self, value: float) -> None:
        """Set the target temperature."""
        await self.coordinator.rinnai_client.async_set_temperature(value)
        await self.coordinator.async_request_refresh() 