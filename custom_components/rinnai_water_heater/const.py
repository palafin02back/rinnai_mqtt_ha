"""Constants for the Rinnai Water Heater integration."""
from homeassistant.const import Platform

DOMAIN = "rinnai_water_heater"

# Configuration
CONF_RINNAI_HTTP_USERNAME = "rinnai_http_username"
CONF_RINNAI_USERNAME = "rinnai_username"
CONF_RINNAI_PASSWORD = "rinnai_password"
CONF_RINNAI_HOST = "rinnai_host"
CONF_RINNAI_PORT = "rinnai_port"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_CONNECT_TIMEOUT = "connect_timeout"
CONF_DEVICE_SN = "device_sn"
CONF_DEVICE_TYPE = "device_type"
CONF_AUTH_CODE = "auth_code"

# Default values
DEFAULT_RINNAI_HOST = "mqtt.rinnai.com.cn"
DEFAULT_RINNAI_PORT = 8883
DEFAULT_UPDATE_INTERVAL = 30
DEFAULT_CONNECT_TIMEOUT = 10

# Entity categories
ENTITY_CATEGORY_CONFIG = "config"
ENTITY_CATEGORY_DIAGNOSTIC = "diagnostic"

# Platforms
PLATFORMS = [
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.NUMBER,
]

# MQTT Topics
TOPIC_INF = "rinnai/SR/01/SR/{device_sn}/inf"
TOPIC_STG = "rinnai/SR/01/SR/{device_sn}/stg"
TOPIC_SET = "rinnai/SR/01/SR/{device_sn}/set"

# Home Assistant MQTT Topics
HA_MQTT_STATE_TOPIC = "homeassistant/rinnai/{device_sn}/state"
HA_MQTT_COMMAND_TOPIC = "homeassistant/rinnai/{device_sn}/set"

# Dependencies
DEPENDENCIES = ["mqtt"] 