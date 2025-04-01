"""Rinnai Water Heater client."""
import asyncio
import json
import logging
import ssl
from typing import Any, Callable

import paho.mqtt.client as mqtt
from homeassistant.components import mqtt as ha_mqtt
from homeassistant.core import HomeAssistant

from .const import (
    TOPIC_INF,
    TOPIC_STG,
    TOPIC_SET,
    HA_MQTT_STATE_TOPIC,
    HA_MQTT_COMMAND_TOPIC,
)

_LOGGER = logging.getLogger(__name__)

class RinnaiClient:
    """Rinnai Water Heater client."""

    def __init__(
        self,
        hass: HomeAssistant,
        rinnai_username: str,
        rinnai_password: str,
        rinnai_host: str,
        rinnai_port: int,
        device_sn: str | None = None,
        device_type: str | None = None,
        auth_code: str | None = None,
        init_status: dict | None = None,
    ) -> None:
        """Initialize the client."""
        self.hass = hass
        self._rinnai_username = rinnai_username
        self._rinnai_password = rinnai_password
        self._rinnai_host = rinnai_host
        self._rinnai_port = rinnai_port
        self._device_sn = device_sn
        self._device_type = device_type
        self._auth_code = auth_code
        self._init_status = init_status or {}
        
        self._rinnai_client = mqtt.Client()
        self._device_data = {
            "state": {},
            "gas": {},
            "supplyTime": {},
        }
        self._callbacks = []
        self._ha_mqtt_unsubscribe_callbacks = []
        self._is_connected = False

        # Configure TLS for Rinnai MQTT
        self._rinnai_client.tls_set(
            cert_reqs=ssl.CERT_NONE,
            tls_version=ssl.PROTOCOL_TLSv1_2
        )
        self._rinnai_client.tls_insecure_set(True)

    async def async_connect(self) -> None:
        """Connect to MQTT brokers."""
        def on_rinnai_connect(client, userdata, flags, rc):
            """Handle connection to Rinnai MQTT broker."""
            rc_messages = {
                0: "连接成功",
                1: "协议版本错误",
                2: "无效的客户端标识",
                3: "服务器无法使用",
                4: "错误的用户名或密码",
                5: "未授权"
            }
            message = rc_messages.get(rc, f"未知错误 {rc}")
            _LOGGER.info("Rinnai MQTT连接状态: %s", message)

            if rc == 0 and self._device_sn:
                topics = [
                    TOPIC_INF.format(device_sn=self._device_sn),
                    TOPIC_STG.format(device_sn=self._device_sn),
                ]
                for topic in topics:
                    client.subscribe(topic)
                    _LOGGER.debug("已订阅主题: %s", topic)
                
                self._is_connected = True
                # 设置初始状态
                self.set_default_status()

        def on_rinnai_message(client, userdata, msg):
            """Handle messages from Rinnai MQTT broker."""
            try:
                _LOGGER.debug("Rinnai msg topic: %s, payload: %s", 
                            msg.topic, msg.payload.decode('utf-8'))
                
                payload = json.loads(msg.payload.decode())
                topic_parts = msg.topic.split('/')
                message_type = topic_parts[-2]

                if message_type == "inf":
                    self._process_device_info(payload)
                elif message_type == "stg":
                    self._process_device_status(payload)
                
                # 使用 Home Assistant MQTT 发布状态
                if self._device_sn:
                    topic = HA_MQTT_STATE_TOPIC.format(device_sn=self._device_sn)
                    self.hass.async_create_task(
                        ha_mqtt.async_publish(
                            self.hass, topic, json.dumps(self._device_data), retain=True
                        )
                    )
                
                self._notify_callbacks()
            except json.JSONDecodeError:
                _LOGGER.error("Failed to decode message: %s", msg.payload)
            except Exception as error:
                _LOGGER.error("Error processing message: %s", error)

        # 配置 Rinnai MQTT 客户端
        self._rinnai_client.username_pw_set(self._rinnai_username, self._rinnai_password)
        self._rinnai_client.on_connect = on_rinnai_connect
        self._rinnai_client.on_message = on_rinnai_message

        # 设置 Home Assistant MQTT 命令订阅
        if self._device_sn:
            command_topic = HA_MQTT_COMMAND_TOPIC.format(device_sn=self._device_sn)
            self._ha_mqtt_unsubscribe_callbacks.append(
                await ha_mqtt.async_subscribe(
                    self.hass,
                    command_topic,
                    self._handle_ha_mqtt_command,
                )
            )

        # 连接到 Rinnai MQTT 服务器
        await self._async_mqtt_connect(
            self._rinnai_client, self._rinnai_host, self._rinnai_port
        )

    def _process_device_info(self, payload: dict) -> None:
        """处理设备信息消息。"""
        if "enl" in payload:
            for item in payload["enl"]:
                if "id" in item and "data" in item:
                    self._device_data["state"][item["id"]] = item["data"]

    def _process_device_status(self, payload: dict) -> None:
        """处理设备状态消息。"""
        if "gas" in payload:
            self._device_data["gas"] = payload["gas"]
        if "supplyTime" in payload:
            self._device_data["supplyTime"] = payload["supplyTime"]

    def set_default_status(self) -> None:
        """设置设备初始状态。"""
        if self._init_status:
            default_status = {"enl": []}
            for key, value in self._init_status.items():
                default_status["enl"].append({"id": key, "data": value})
            self._process_device_info(default_status)
            self._notify_callbacks()

    async def _handle_ha_mqtt_command(self, msg):
        """处理来自 Home Assistant MQTT 的命令。"""
        try:
            if not self._device_sn:
                return

            payload = json.loads(msg.payload)
            command_type = None
            command_value = None

            if "hotWaterTempSetting" in payload:
                command_type = "temperature"
                command_value = payload["hotWaterTempSetting"]
            elif "mode" in payload:
                command_type = "mode"
                command_value = payload["mode"]
            elif "power" in payload:
                command_type = "power"
                command_value = payload["power"]

            if command_type:
                await self._send_command(command_type, command_value)

        except Exception as error:
            _LOGGER.error("Error handling Home Assistant MQTT command: %s", error)

    async def _send_command(self, command_type: str, value: Any) -> None:
        """发送命令到设备。"""
        if not self._device_sn or not self._device_type or not self._auth_code:
            return

        request_payload = {
            "code": self._auth_code,
            "enl": [],
            "id": self._device_type,
            "ptn": "J00",
            "sum": "1"
        }

        if command_type == "temperature":
            request_payload["enl"].append({
                "data": hex(int(value))[2:].upper().zfill(2),
                "id": "hotWaterTempSetting"
            })
        elif command_type == "mode":
            request_payload["enl"].append({
                "data": "31",
                "id": value
            })
        elif command_type == "power":
            request_payload["enl"].append({
                "data": "31" if value else "30",
                "id": "power"
            })

        topic = TOPIC_SET.format(device_sn=self._device_sn)
        self._rinnai_client.publish(topic, json.dumps(request_payload), qos=1)

    async def async_disconnect(self) -> None:
        """Disconnect from MQTT brokers."""
        # 取消订阅 Home Assistant MQTT
        for unsubscribe_callback in self._ha_mqtt_unsubscribe_callbacks:
            unsubscribe_callback()
        self._ha_mqtt_unsubscribe_callbacks = []

        # 断开 Rinnai MQTT 连接
        self._rinnai_client.loop_stop()
        self._rinnai_client.disconnect()
        self._is_connected = False

    async def _async_mqtt_connect(self, client: mqtt.Client, host: str, port: int) -> None:
        """Connect to an MQTT broker."""
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: client.connect(host, port)
            )
            client.loop_start()
        except Exception as error:
            _LOGGER.error("Failed to connect to MQTT broker: %s", error)
            raise

    @property
    def is_connected(self) -> bool:
        """Return if client is connected."""
        return self._is_connected

    @property
    def state(self) -> dict:
        """Return device state."""
        return self._device_data.get("state", {})

    @property
    def gas(self) -> dict:
        """Return gas usage data."""
        return self._device_data.get("gas", {})

    @property
    def supply_time(self) -> dict:
        """Return supply time data."""
        return self._device_data.get("supplyTime", {})

    @property
    def temperature(self) -> float | None:
        """Return current temperature setting."""
        temp_hex = self.state.get("hotWaterTempSetting")
        return int(temp_hex, 16) if temp_hex else None

    @property
    def mode(self) -> str | None:
        """Return current mode."""
        for mode_key in ["energySavingMode", "outdoorMode", "rapidHeating"]:
            if self.state.get(mode_key) == "31":
                return mode_key
        return None

    @property
    def power(self) -> bool | None:
        """Return power state."""
        power_state = self.state.get("power")
        if power_state is not None:
            return power_state == "31"
        return None

    def register_callback(self, callback: Callable[[], None]) -> None:
        """Register callback for data updates."""
        self._callbacks.append(callback)

    def _notify_callbacks(self) -> None:
        """Notify all registered callbacks of data updates."""
        for callback in self._callbacks:
            callback()

    async def async_set_temperature(self, temperature: float) -> None:
        """Set the target temperature."""
        await self._send_command("temperature", temperature)

    async def async_set_power(self, power: bool) -> None:
        """Set the power state."""
        await self._send_command("power", power)

    async def async_set_mode(self, mode: str) -> None:
        """Set operation mode."""
        await self._send_command("mode", mode) 