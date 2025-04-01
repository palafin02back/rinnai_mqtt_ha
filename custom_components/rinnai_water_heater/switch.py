"""Support for Rinnai Water Heater switches."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
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
    """Set up the Rinnai switches."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([RinnaiPowerSwitch(coordinator)])

class RinnaiPowerSwitch(CoordinatorEntity[RinnaiDataUpdateCoordinator], SwitchEntity):
    """Representation of a Rinnai power switch."""

    def __init__(self, coordinator: RinnaiDataUpdateCoordinator) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._attr_name = "Power"
        self._attr_unique_id = f"{coordinator.rinnai_client._device_data.get('device_sn', '')}_power"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.rinnai_client._device_data.get("device_sn", ""))},
            "name": "Rinnai Water Heater",
            "manufacturer": "Rinnai",
            "model": coordinator.rinnai_client._device_data.get("device_type", ""),
        }

    @property
    def is_on(self) -> bool | None:
        """Return true if the switch is on."""
        return self.coordinator.data.get("power")

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self.coordinator.rinnai_client.async_set_power(True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self.coordinator.rinnai_client.async_set_power(False)
        await self.coordinator.async_request_refresh() 