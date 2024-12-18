import requests
from dotenv import load_dotenv, set_key
import os
import hashlib
import logging

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.disabled = os.getenv('LOGGING', 'False') == 'true'

HOST = "https://iot.rinnai.com.cn/app"
LOGIN_URL = f"{HOST}/V1/login"
INFO_URL = f"{HOST}/V1/device/list"
AK = "A39C66706B83CCF0C0EE3CB23A39454D"  # 林内智家app内置acessKey

class RinnaiHttpProxy:
    def __init__(self, username, password):
        self.username = str(username)
        self.password = str.upper(hashlib.md5(
            password.encode('utf-8')).hexdigest())
        self.token = None
        self.mac = None
        self.name = None
        self.authCode = None
        self.deviceType = None
        self.deviceId = None
        self.operationMode = None
    
    def login(self):
        params = {
            "username": self.username,
            "password": self.password,
            "accessKey": AK,
            "appType": "2",
            "appVersion": "3.1.0",
            "identityLevel": "0"
        }
        response = requests.get(LOGIN_URL, params=params)
        if response.status_code == 200 and response.json().get("success") !=False:
            self.token = response.json().get("data").get("token")
            logger.info(f"login success, token: {self.token}")
            return True
        return False

    def get_devices(self):
        self.login()
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(INFO_URL, headers=headers)
        if response.status_code == 200 and response.json().get("success"):
            devices = response.json().get("data").get("list")
            logger.info(f"devices: {devices}")
            if devices[0].get("online") == "1":
                self.mac = devices[0].get("mac")
                self.name = devices[0].get("name")
                self.authCode = devices[0].get("authCode")
                self.deviceType = devices[0].get("deviceType")
                self.deviceId = devices[0].get("id")
                self.operationMode = devices[0].get("operationMode")
                return True
        return None

def env_setup():
    dotenv_path = '.env'
    Rinnai = RinnaiHttpProxy(
        os.getenv('RINNAI_USERNAME'), os.getenv('RINNAI_PASSWORD'))
    Rinnai.get_devices()
    # 把环境变量写到 .env 文件
    set_key(dotenv_path, "DEVICE_SN", Rinnai.mac, quote_mode="never")
    set_key(dotenv_path, "AUTH_CODE", Rinnai.authCode, quote_mode="never")
    set_key(dotenv_path, "DEVICE_TYPE", Rinnai.deviceType, quote_mode="never")
    set_key(dotenv_path, "DEVICE_ID", Rinnai.deviceId, quote_mode="never")
    set_key(dotenv_path, "OPERATION_MODE", Rinnai.operationMode, quote_mode="never")

# Example usage
if __name__ == "__main__":
    env_setup()
