"""Rinnai HTTP client for device initialization."""
import logging
import requests

_LOGGER = logging.getLogger(__name__)

# API URLs
LOGIN_URL = "https://iot.rinnai.com.cn/v1/user/login"
INFO_URL = "https://iot.rinnai.com.cn/v1/device/info"
PROCESS_PARAMETER_URL = "https://iot.rinnai.com.cn/v1/device/processParameter"

# Constants
AK = "SR:01:SR"
STATE_PARAMETERS = [
    "hotWaterTempSetting",
    "heatingTempSettingNM",
    "heatingTempSettingHES",
    "energySavingMode",
    "outdoorMode",
    "rapidHeating",
    "summerWinter",
]

class RinnaiHttpClient:
    """HTTP client for Rinnai device initialization."""

    def __init__(self, username: str, password: str) -> None:
        """Initialize the client."""
        self._username = username
        self._password = password
        self._token = None
        self._device_info = {
            "mac": None,
            "name": None,
            "authCode": None,
            "deviceType": None,
            "deviceId": None,
        }
        self._init_param = {}

    async def login(self) -> bool:
        """Login to Rinnai server."""
        params = {
            "username": self._username,
            "password": self._password,
            "accessKey": AK,
            "appType": "2",
            "appVersion": "3.1.0",
            "identityLevel": "0",
        }

        try:
            _LOGGER.info("Logging in to Rinnai server...")
            response = requests.get(LOGIN_URL, params=params)
            response.raise_for_status()

            data = response.json()
            if not data.get("success"):
                _LOGGER.error("Login validation failed: %s", data.get("message", "Unknown error"))
                return False

            self._token = data.get("data", {}).get("token")
            if not self._token:
                _LOGGER.error("No token in login response")
                return False

            _LOGGER.info("Login successful")
            return True

        except requests.RequestException as error:
            _LOGGER.error("Login request failed: %s", error)
            return False

    async def get_devices(self) -> dict | None:
        """Get device information."""
        if not self._token:
            _LOGGER.error("No token available")
            return None

        try:
            headers = {"Authorization": f"Bearer {self._token}"}
            response = requests.get(INFO_URL, headers=headers)
            response.raise_for_status()

            data = response.json()
            if not data.get("success"):
                return None

            devices = data.get("data", {}).get("list", [])
            if not devices or devices[0].get("online") != "1":
                _LOGGER.error("No devices found or device is offline")
                return None

            device = devices[0]
            self._device_info = {
                "mac": device.get("mac"),
                "name": device.get("name"),
                "authCode": device.get("authCode"),
                "deviceType": device.get("deviceType"),
                "deviceId": device.get("id"),
            }
            return self._device_info

        except requests.RequestException as error:
            _LOGGER.error("Failed to get devices: %s", error)
            return None

    async def get_process_parameter(self) -> dict | None:
        """Get device process parameters."""
        if not self._token or not self._device_info.get("deviceId"):
            return None

        try:
            headers = {"Authorization": f"Bearer {self._token}"}
            params = {"deviceId": self._device_info["deviceId"]}
            response = requests.get(PROCESS_PARAMETER_URL, params=params, headers=headers)
            response.raise_for_status()

            data = response.json()
            if not data.get("success"):
                return None

            parameters = data.get("data", {})
            self._init_param = {
                key: parameters[key]
                for key in STATE_PARAMETERS
                if key in parameters
            }
            return self._init_param

        except requests.RequestException as error:
            _LOGGER.error("Failed to get process parameters: %s", error)
            return None

    async def initialize(self) -> bool:
        """Initialize all device data."""
        if not await self.login():
            return False

        if not await self.get_devices():
            return False

        if not await self.get_process_parameter():
            return False

        return True

    @property
    def device_info(self) -> dict:
        """Get device information."""
        return self._device_info

    @property
    def init_param(self) -> dict:
        """Get initialization parameters."""
        return self._init_param 