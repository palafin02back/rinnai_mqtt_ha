"""Data update coordinator for Rinnai Water Heater integration."""
from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .rinnai_client import RinnaiClient

_LOGGER = logging.getLogger(__name__)

class RinnaiDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the Rinnai Water Heater."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: RinnaiClient,
        update_interval: timedelta,
    ) -> None:
        """Initialize."""
        self.client = client
        self._hass = hass

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library."""
        try:
            if not self.client.is_connected:
                await self.client.async_connect()
                
            return {
                "state": self.client.state,
                "gas": self.client.gas,
                "supply_time": self.client.supply_time,
                "temperature": self.client.temperature,
                "mode": self.client.mode,
                "power": self.client.power,
            }
        except Exception as error:
            _LOGGER.error("Error updating Rinnai data: %s", error)
            raise UpdateFailed(error) from error

    async def async_unload(self):
        """Disconnect from MQTT brokers when unloading."""
        await self.client.async_disconnect() 