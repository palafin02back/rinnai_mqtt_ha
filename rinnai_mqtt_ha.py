import paho.mqtt.client as mqtt
import json
import ssl
import uuid
import time
import os
import hashlib
from dotenv import load_dotenv
import logging

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.disabled = os.getenv('LOGGING', 'False') == 'true'

class RinnaiHomeAssistantIntegration:
    def __init__(self):
        # Rinnai mqtt连接配置
        password = os.getenv('RINNAI_PASSWORD')
        self.rinnai_host = os.getenv('RINNAI_HOST', 'mqtt.rinnai.com.cn')
        self.rinnai_port = int(os.getenv('RINNAI_PORT', '8883'))
        self.rinnai_username = f"a:rinnai:SR:01:SR:{os.getenv('RINNAI_USERNAME')}"
        self.rinnai_password = str.upper(
            hashlib.md5(password.encode('utf-8')).hexdigest())
        self.device_sn = os.getenv('DEVICE_SN')

        # 本地MQTT服务器配置
        self.local_mqtt_host = os.getenv('LOCAL_MQTT_HOST')
        self.local_mqtt_port = int(os.getenv('LOCAL_MQTT_PORT', '1883'))

        # Rinnai MQTT客户端
        self.rinnai_client = self._create_rinnai_client()

        # 本地MQTT客户端
        self.local_client = self._create_local_client()

        # 设备状态和耗气量
        self.device_state = {}
        self.gas_consumption = {}

    def _create_rinnai_client(self):
        client = mqtt.Client(
            client_id=f"rinnai_ha_bridge_{str(uuid.uuid4())[:8]}",
            transport="tcp",
            callback_api_version=mqtt.CallbackAPIVersion.VERSION1
        )
        client.tls_set(
            cert_reqs=ssl.CERT_NONE,
            tls_version=ssl.PROTOCOL_TLSv1_2
        )
        client.tls_insecure_set(True)
        client.username_pw_set(self.rinnai_username, self.rinnai_password)
        client.on_connect = self.on_rinnai_connect
        client.on_message = self.on_rinnai_message
        return client

    def _create_local_client(self):
        client = mqtt.Client(
            client_id=f"rinnai_ha_local_{str(uuid.uuid4())[:8]}",
            callback_api_version=mqtt.CallbackAPIVersion.VERSION1
        )
        client.on_connect = self.on_local_connect
        client.on_message = self.on_local_message
        return client

    def on_rinnai_connect(self, client, userdata, flags, rc):
        logging.info(f"rinnai mqtt connect status: {rc}")
        if rc == 0:
            """
            已知主题:
            rinnai/SR/01/SR/{device_sn}/sys/
            rinnai/SR/01/SR/{device_sn}/inf/
            rinnai/SR/01/SR/{device_sn}/set/
            rinnai/SR/01/SR/{device_sn}/res/
            rinnai/SR/01/SR/{device_sn}/get/
            rinnai/SR/01/SR/{device_sn}/stg/

            """
            client.subscribe(f"rinnai/SR/01/SR/{self.device_sn}/inf/")
            client.subscribe(f"rinnai/SR/01/SR/{self.device_sn}/stg/")

    def on_local_connect(self, client, userdata, flags, rc):
        logging.info(f"local mqtt connect status: {rc}")
        if rc == 0:
            # 本地服务器订阅设置主题，区分热水和暖气
            client.subscribe("local_mqtt/rinnai/set/temp/hotWaterTempSetting")
            client.subscribe("local_mqtt/rinnai/set/temp/heatingTempSettingNM")
            client.subscribe("local_mqtt/rinnai/set/temp/heatingTempSettingHES")
            client.subscribe("local_mqtt/rinnai/set/mode/energySavingMode")
            client.subscribe("local_mqtt/rinnai/set/mode/outdoorMode")
            client.subscribe("local_mqtt/rinnai/set/mode/rapidHeating")
            client.subscribe("local_mqtt/rinnai/set/mode/summerWinter")


    def on_rinnai_message(self, client, userdata, msg):
        try:
            self._process_rinnai_message(msg)
        except Exception as e:
            logging.info(f"Rinnai msg error: {e}")

    def _publish_device_state(self):

        # 发布完整的设备状态到本地MQTT
        state_topic = "local_mqtt/rinnai/state"
        self.local_client.publish(
            state_topic,
            json.dumps(self.device_state, ensure_ascii=False)
        )
        logging.info(f"Publish to local mqtt: {self.device_state}")
    
    def _publish_gas_consumption(self):

            # 发布完整的设备状态到本地MQTT
        gas_topic = "local_mqtt/rinnai/gas"
        self.local_client.publish(
            gas_topic,
            json.dumps(self.gas_consumption, ensure_ascii=False)
        )
        logging.info(f"Publish to local mqtt: {self.gas_consumption}")

    def on_local_message(self, client, userdata, msg):
        try:
            action = msg.topic.split('/')[-2]
            if action == 'temp':
                temperature = int(msg.payload.decode())
                heat_type = msg.topic.split('/')[-1]
                self.set_rinnai_temperature(heat_type, temperature)
            elif action == 'mode':
                mode = msg.topic.split('/')[-1]
                self.set_rinnai_mode(mode)
        except Exception as e:
            logging.info(f"local mqtt set fail: {e}")

    def set_rinnai_temperature(self, heat_type, temperature):
        if heat_type:
            param_id = heat_type
        else:
            raise ValueError("error heat type")
        # 向林内服务器发布设置温度主题
        request_payload = {
            "code": os.getenv('AUTH_CODE'),
            "enl": [
                {
                    "data": hex(temperature)[2:].upper().zfill(2),
                    "id": param_id
                }
            ],
            "id": os.getenv('DEVICE_TYPE'),
            "ptn": "J00",
            "sum": "1"
        }

        set_topic = f"rinnai/SR/01/SR/{self.device_sn}/set/"
        self.rinnai_client.publish(
            set_topic, json.dumps(request_payload), qos=1)
        print(f"设置{heat_type}温度为 {temperature}°C")

    def set_rinnai_mode(self, mode):
        if mode :
            param_id = mode
        else:
            raise ValueError("error mode type")

        # 向林内服务器发布设置温度模式
        request_payload = {
            "code": os.getenv('AUTH_CODE'),
            "enl": [
                {
                    "data": "31",
                    "id": param_id
                }
            ],
            "id": os.getenv('DEVICE_TYPE'),
            "ptn": "J00",
            "sum": "1"
        }

        set_topic = f"rinnai/SR/01/SR/{self.device_sn}/set/"
        self.rinnai_client.publish(
            set_topic, json.dumps(request_payload), qos=1)
        logging.info(f"SET {mode}")

    def _get_operation_mode(self, mode_code):
        """模式映射"""
        mode_mapping = {
            "0": "关机",
            "1": "采暖关闭",
            "2": "休眠",
            "3": "冬季普通",
            "4": "快速热水",
            "B": "采暖节能",
            "23": "采暖预约",
            "13": "采暖外出",
            "43": "快速采暖",
            "4B": "快速采暖/节能",
            "53": "快速采暖/外出",
            "63": "快速采暖/预约"
        }
        return mode_mapping.get(mode_code, f"invalid ({mode_code})")

    def _get_burning_state(self, state_code):
        """
        已知状态码:
        30: 待机中
        31: 热水点火
        32: 燃气点火
        """
        
        state_mapping = {
            "30": "待机中",
            "31": "烧水中",
            "32": "燃烧中",
            "33": "异常"
        }
        return state_mapping.get(state_code, f"invalid ({state_code})")

    def _process_rinnai_message(self, msg):
        payload = msg.payload.decode('utf-8')
        parsed_data = json.loads(payload)
        # if msg.topic.endswith('/inf/'):
        self.device_state = {}
        self.gas_consumption = {}
        if "enl" in parsed_data:        
            for param in parsed_data['enl']:
                param_id = param['id']
                param_data = param['data']

                if param_id == 'operationMode':
                    self.device_state['operationMode'] = self._get_operation_mode(
                        param_data)
                elif param_id == 'roomTempControl':
                    self.device_state['roomTempControl'] = f"{int(param_data, 16)}"
                elif param_id == 'heatingOutWaterTempControl':
                    self.device_state['heatingOutWaterTempControl'] = f"{int(param_data, 16)}"
                elif param_id == 'burningState':
                    self.device_state['burningState'] = self._get_burning_state(
                        param_data)
                elif param_id == 'hotWaterTempSetting':
                    self.device_state['hotWaterTempSetting'] = f"{int(param_data, 16)}"
                elif param_id == 'heatingTempSettingNM':
                    self.device_state['heatingTempSettingNM'] = f"{int(param_data, 16)}"
                elif param_id == 'heatingTempSettingHES':
                    self.device_state['heatingTempSettingHES'] = f"{int(param_data, 16)}"
            self._publish_device_state()
        elif "egy" in parsed_data:
            for param in parsed_data['egy']:
                gas_consumption = param.get('gasConsumption')
                if gas_consumption is not None:
                    logger.info(f"gasConsumption: {gas_consumption}")
                    self.gas_consumption['gasConsumption'] = f"{int(gas_consumption, 16)}"

            self._publish_gas_consumption()
    def start(self):
        # 连接Rinnai MQTT服务器
        self.rinnai_client.connect(
            self.rinnai_host,
            self.rinnai_port,
            60
        )

        # 连接本地MQTT服务器
        self.local_client.connect(
            self.local_mqtt_host,
            self.local_mqtt_port,
            60
        )

        # 启动客户端循环
        self.rinnai_client.loop_start()
        self.local_client.loop_forever()


def main():
    integration = RinnaiHomeAssistantIntegration()
    integration.start()


if __name__ == "__main__":
    main()
