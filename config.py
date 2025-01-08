import os
import hashlib
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Rinnai MQTT settings
    RINNAI_HTTP_USERNAME = os.getenv('RINNAI_USERNAME')
    RINNAI_MQTT_HOST = os.getenv('RINNAI_MQTT_HOST', 'mqtt.rinnai.com.cn')
    RINNAI_MQTT_PORT = int(os.getenv('RINNAI_MQTT_PORT', '8883'))
    RINNAI_USERNAME = f"a:rinnai:SR:01:SR:{os.getenv('RINNAI_USERNAME')}"
    RINNAI_PASSWORD = str.upper(
        hashlib.md5(os.getenv('RINNAI_PASSWORD').encode('utf-8')).hexdigest())
    DEVICE_SN = None
    AUTH_CODE = None
    DEVICE_TYPE = None
    INIT_STATUS = None

    # Local MQTT settings
    LOCAL_MQTT_HOST = os.getenv('LOCAL_MQTT_HOST')
    LOCAL_MQTT_PORT = int(os.getenv('LOCAL_MQTT_PORT', '1883'))
    LOCAL_MQTT_USERNAME =os.getenv('LOCAL_MQTT_USERNAME', None)
    LOCAL_MQTT_PASSWORD =os.getenv('LOCAL_MQTT_PASSWORD', None)
    LOCAL_MQTT_TLS = os.getenv('LOCAL_MQTT_TLS', 'False').lower() == 'true'
    LOGGING = os.getenv('LOCAL_MQTT_TLS', 'False').lower() == 'true'


    # Topic structures
    @classmethod
    def get_rinnai_topics(cls):
        return {
            "inf": f"rinnai/SR/01/SR/{cls.DEVICE_SN}/inf/",
            "stg": f"rinnai/SR/01/SR/{cls.DEVICE_SN}/stg/",
            "set": f"rinnai/SR/01/SR/{cls.DEVICE_SN}/set/"
        }

    @classmethod
    def update_device_sn(cls, device_sn):
        cls.DEVICE_SN = device_sn
    
    @classmethod
    def update_auth_code(cls, auth_code):
        cls.AUTH_CODE = auth_code
    
    @classmethod
    def update_device_type(cls, device_type):
        cls.DEVICE_TYPE = device_type

    @classmethod
    def update_init_status(cls, init_status):
        cls.INIT_STATUS = init_status


    @classmethod
    def get_local_topics(cls):
        return {
            "hotWaterTempSetting": "local_mqtt/rinnai/set/temp/hotWaterTempSetting",
            "heatingTempSettingNM": "local_mqtt/rinnai/set/temp/heatingTempSettingNM",
            "heatingTempSettingHES": "local_mqtt/rinnai/set/temp/heatingTempSettingHES",
            "energySavingMode": "local_mqtt/rinnai/set/mode/energySavingMode",
            "outdoorMode": "local_mqtt/rinnai/set/mode/outdoorMode",
            "rapidHeating": "local_mqtt/rinnai/set/mode/rapidHeating",
            "summerWinter": "local_mqtt/rinnai/set/mode/summerWinter",
            "state": "local_mqtt/rinnai/state",
            "gas": "local_mqtt/rinnai/usage/gas",
            "supplyTime": "local_mqtt/rinnai/usage/supplyTime"
        }
