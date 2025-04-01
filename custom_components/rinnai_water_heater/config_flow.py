"""Config flow for Rinnai Water Heater integration."""
from __future__ import annotations

import hashlib
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig

from .const import (
    DOMAIN,
    CONF_RINNAI_HTTP_USERNAME,
    CONF_RINNAI_USERNAME,
    CONF_RINNAI_PASSWORD,
    CONF_RINNAI_HOST,
    CONF_RINNAI_PORT,
    CONF_LOCAL_MQTT_HOST,
    CONF_LOCAL_MQTT_PORT,
    CONF_LOCAL_MQTT_USERNAME,
    CONF_LOCAL_MQTT_PASSWORD,
    CONF_LOCAL_MQTT_TLS,
    CONF_UPDATE_INTERVAL,
    CONF_CONNECT_TIMEOUT,
    CONF_USE_HA_MQTT,
    CONF_DEVICE_SN,
    CONF_DEVICE_TYPE,
    CONF_AUTH_CODE,
    DEFAULT_RINNAI_HOST,
    DEFAULT_RINNAI_PORT,
    DEFAULT_LOCAL_MQTT_PORT,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_CONNECT_TIMEOUT,
    DEFAULT_USE_HA_MQTT,
)
from .http_client import RinnaiHttpClient

_LOGGER = logging.getLogger(__name__)

class RinnaiConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Rinnai Water Heater."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        # 检查 MQTT 集成是否已配置
        if not self._async_current_entries(include_ignore=False):
            mqtt_config = self.hass.config_entries.async_entries("mqtt")
            if not mqtt_config:
                return self.async_abort(
                    reason="mqtt_required",
                    description_placeholders={
                        "integration": "MQTT",
                        "integration_title": "MQTT",
                    },
                )

        if user_input is not None:
            try:
                # 初始化 HTTP 客户端
                http_client = RinnaiHttpClient(
                    username=user_input[CONF_RINNAI_HTTP_USERNAME],
                    password=user_input[CONF_RINNAI_PASSWORD],
                )

                # 获取设备信息
                if await http_client.initialize():
                    device_info = http_client.device_info
                    init_param = http_client.init_param

                    # 处理 Rinnai MQTT 用户名和密码
                    rinnai_username = f"a:rinnai:SR:01:SR:{user_input[CONF_RINNAI_HTTP_USERNAME]}"
                    rinnai_password = str.upper(
                        hashlib.md5(user_input[CONF_RINNAI_PASSWORD].encode('utf-8')).hexdigest()
                    )

                    # 更新配置数据
                    user_input.update({
                        CONF_RINNAI_USERNAME: rinnai_username,
                        CONF_RINNAI_PASSWORD: rinnai_password,
                        CONF_DEVICE_SN: device_info["mac"],
                        CONF_DEVICE_TYPE: device_info["deviceType"],
                        CONF_AUTH_CODE: device_info["authCode"],
                        "init_status": init_param,
                    })

                    await self.async_set_unique_id(device_info["mac"])
                    self._abort_if_unique_id_configured()

                    return self.async_create_entry(
                        title=f"Rinnai Water Heater ({device_info['name']})",
                        data=user_input
                    )
                else:
                    errors["base"] = "cannot_connect"
            except Exception as error:
                _LOGGER.error("Failed to initialize device: %s", error)
                errors["base"] = "unknown"

        schema = {
            vol.Required(CONF_RINNAI_HTTP_USERNAME): str,
            vol.Required(CONF_RINNAI_PASSWORD): str,
            vol.Optional(CONF_RINNAI_HOST, default=DEFAULT_RINNAI_HOST): str,
            vol.Optional(CONF_RINNAI_PORT, default=DEFAULT_RINNAI_PORT): int,
            vol.Optional(CONF_USE_HA_MQTT, default=DEFAULT_USE_HA_MQTT): bool,
            vol.Optional(CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL): int,
            vol.Optional(CONF_CONNECT_TIMEOUT, default=DEFAULT_CONNECT_TIMEOUT): int,
        }

        # 如果不使用 Home Assistant MQTT，则需要配置本地 MQTT
        if not user_input or not user_input.get(CONF_USE_HA_MQTT, DEFAULT_USE_HA_MQTT):
            schema.update({
                vol.Required(CONF_LOCAL_MQTT_HOST): str,
                vol.Optional(CONF_LOCAL_MQTT_PORT, default=DEFAULT_LOCAL_MQTT_PORT): int,
                vol.Optional(CONF_LOCAL_MQTT_USERNAME): str,
                vol.Optional(CONF_LOCAL_MQTT_PASSWORD): str,
                vol.Optional(CONF_LOCAL_MQTT_TLS, default=False): bool,
            })

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(schema),
            errors=errors,
        ) 