"""The Rinnai Water Heater integration."""
from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import (
    DOMAIN,
    CONF_RINNAI_USERNAME,
    CONF_RINNAI_PASSWORD,
    CONF_RINNAI_HOST,
    CONF_RINNAI_PORT,
    CONF_UPDATE_INTERVAL,
    CONF_DEVICE_SN,
    CONF_DEVICE_TYPE,
    CONF_AUTH_CODE,
    PLATFORMS,
)
from .coordinator import RinnaiDataUpdateCoordinator
from .rinnai_client import RinnaiClient

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Rinnai Water Heater from a config entry."""
    # 检查 MQTT 集成是否已配置
    mqtt_config = hass.config_entries.async_entries("mqtt")
    if not mqtt_config:
        _LOGGER.error("MQTT integration is not configured")
        return False
    
    # 创建 Rinnai 客户端
    client = RinnaiClient(
        hass=hass,
        rinnai_username=entry.data[CONF_RINNAI_USERNAME],
        rinnai_password=entry.data[CONF_RINNAI_PASSWORD],
        rinnai_host=entry.data[CONF_RINNAI_HOST],
        rinnai_port=entry.data[CONF_RINNAI_PORT],
        device_sn=entry.data[CONF_DEVICE_SN],
        device_type=entry.data[CONF_DEVICE_TYPE],
        auth_code=entry.data[CONF_AUTH_CODE],
        init_status=entry.data.get("init_status", {}),
    )

    coordinator = RinnaiDataUpdateCoordinator(
        hass,
        client,
        update_interval=timedelta(seconds=entry.data.get(CONF_UPDATE_INTERVAL, 30)),
    )

    try:
        # 初始更新
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryNotReady:
        await client.async_disconnect()
        raise

    # 存储协调器供平台使用
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # 设置平台
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_unload()

    return unload_ok 