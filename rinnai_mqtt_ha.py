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
        """
            已知主题:
            rinnai/SR/01/SR/{device_sn}/sys/
            rinnai/SR/01/SR/{device_sn}/inf/
            rinnai/SR/01/SR/{device_sn}/set/
            rinnai/SR/01/SR/{device_sn}/res/
            rinnai/SR/01/SR/{device_sn}/get/
            rinnai/SR/01/SR/{device_sn}/stg/

        """
        self.rinnai_topics = {
            "inf": f"rinnai/SR/01/SR/{self.device_sn}/inf/",
            "stg": f"rinnai/SR/01/SR/{self.device_sn}/stg/",
            "set": f"rinnai/SR/01/SR/{self.device_sn}/set/"
        }
        """
            本地主题:
            hotWaterTempSetting: 热水温度设置
            heatingTempSettingNM: 暖气温度设置(普通模式)
            heatingTempSettingHES: 暖气温度设置(节能模式)
            energySavingMode: 节能模式
            outdoorMode: 外出模式
            rapidHeating: 快速采暖
            summerWinter: 采暖开关
            state: 设备状态
            gas: 耗气量
        """
        self.local_topics = {
            "hotWaterTempSetting": "local_mqtt/rinnai/set/temp/hotWaterTempSetting",
            "heatingTempSettingNM": "local_mqtt/rinnai/set/temp/heatingTempSettingNM",
            "heatingTempSettingHES": "local_mqtt/rinnai/set/temp/heatingTempSetting",
            "energySavingMode": "local_mqtt/rinnai/set/mode/energySavingMode",
            "outdoorMode": "local_mqtt/rinnai/set/mode/outdoorMode",
            "rapidHeating": "local_mqtt/rinnai/set/mode/rapidHeating",
            "summerWinter": "local_mqtt/rinnai/set/mode/summerWinter",
            "state": "local_mqtt/rinnai/state",
            "gas": "local_mqtt/rinnai/usage/gas",
            "supplyTime": "local_mqtt/rinnai/usage/supplyTime"
        }

        self.device_data = {
            "state": {},
            "gas": {},
            "supplyTime": {}
        }

        self.local_mqtt_host = os.getenv('LOCAL_MQTT_HOST')
        self.local_mqtt_port = int(os.getenv('LOCAL_MQTT_PORT', '1883'))
        self.rinnai_client = self._create_rinnai_client()
        self.local_client = self._create_local_client()
        #立马设置当前状态来获取最新状态
        self.init_data()


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
            # 订阅林内服务器主题
            for topic in self.rinnai_topics.values():
                client.subscribe(topic)

    def on_local_connect(self, client, userdata, flags, rc):
        logging.info(f"local mqtt connect status: {rc}")
        if rc == 0:
            # 本地服务器订阅设置主题
            for topic in self.local_topics.values():
                client.subscribe(topic)


    def on_rinnai_message(self, client, userdata, msg):
        try:
            logging.info(
                f"rinnai msg topic: {msg.topic}, payload: {json.loads(msg.payload.decode('utf-8'))}")
            self._process_rinnai_message(msg)
        except Exception as e:
            logging.info(f"Rinnai msg error: {e}")

    def _publish_device_state(self):

        # 同步完整的设备状态到本地MQTT
        self.local_client.publish(
            self.local_topics["state"],
            json.dumps(self.device_data["state"], ensure_ascii=False)
        )
        logging.info(f"Publish to local mqtt: {self.device_data['state']}")
    
    def _publish_gas_consumption(self):

        # 同步耗气量本地MQTT
        self.local_client.publish(
            self.local_topics["gas"],
            json.dumps(self.device_data["gas"], ensure_ascii=False)
        )
        logging.info(f"Publish to local mqtt: {self.device_data['gas']}")

    def _publish_supply_time(self):
            
            # 同步耗气量本地MQTT
            self.local_client.publish(
                self.local_topics["supplyTime"],
                json.dumps(self.device_data["supplyTime"], ensure_ascii=False)
            )
            logging.info(f"Publish to local mqtt: {self.device_data['supplyTime']}")
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
        self.rinnai_client.publish(
            self.rinnai_topics["set"], json.dumps(request_payload), qos=1)
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
        self.rinnai_client.publish(
            self.rinnai_topics["set"], json.dumps(request_payload), qos=1)
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
        try:
            parsed_data = json.loads(msg.payload.decode('utf-8'))
            parsed_topic = msg.topic.split('/')[-2]

            # 检查是否空数据
            if not parsed_data or not parsed_topic:
                logging.warning("Received invalid or empty message")
                return

            # 处理设备信息消息
            if parsed_topic == 'inf' and parsed_data.get('enl') and parsed_data.get('code') == "FFFF":
                # 重置设备状态
                # self.device_data["state"] = {}

                for param in parsed_data['enl']:
                    try:
                        param_id = param.get('id')
                        param_data = param.get('data')

                        # 仅处理有效的参数
                        if not param_id or not param_data:
                            continue

                        # 使用映射来简化和标准化处理逻辑
                        state_mapping = {
                            'operationMode': lambda x: self._get_operation_mode(x),
                            'roomTempControl': lambda x: str(int(x, 16)),
                            'heatingOutWaterTempControl': lambda x: str(int(x, 16)),
                            'burningState': lambda x: self._get_burning_state(x),
                            'hotWaterTempSetting': lambda x: str(int(x, 16)),
                            'heatingTempSettingNM': lambda x: str(int(x, 16)),
                            'heatingTempSettingHES': lambda x: str(int(x, 16))
                        }

                        # 根据映射处理参数
                        if param_id in state_mapping:
                            self.device_data["state"][param_id] = state_mapping[param_id](param_data)

                    except Exception as e:
                        logging.error(
                            f"Error processing parameter {param_id}: {e}")

                # 仅在有有效状态时发布
                if self.device_data["state"]:
                    self._publish_device_state()

            # 处理能耗信息
            elif parsed_topic == 'stg' and parsed_data.get('egy') and parsed_data.get('ptn') == "J05":
                # self.device_data["gas"] = {}
                for param in parsed_data['egy']:

                    try:
                        gas_consumption = param.get('gasConsumption')
                        totalPowerSupplyTime = param.get('totalPowerSupplyTime')
                        if not gas_consumption and not totalPowerSupplyTime:
                            continue
                        if gas_consumption is not None:
                            try:
                                consumption = int(gas_consumption, 16)
                                self.device_data["gas"]["gasConsumption"] = str(consumption)
                                logger.info(f"gasConsumption: {consumption}")
                            except ValueError:
                                logging.warning(
                                    f"Invalid gas consumption value: {gas_consumption}")
                        if totalPowerSupplyTime is not None:
                            try:
                                usage_mapping = {
                                    'totalPowerSupplyTime': lambda x: str(int(x, 16)),
                                    'actualUseTime': lambda x: str(int(x, 16)),
                                    'totalHeatingBurningTime': lambda x: str(int(x, 16)),
                                    'burningtotalHotWaterBurningTimeState': lambda x: str(int(x, 16)),
                                    'heatingBurningTimes': lambda x: str(int(x, 16)),
                                    'hotWaterBurningTimes': lambda x: str(int(x, 16))
                                }
                                if param_id in usage_mapping:
                                    self.device_data["supplyTime"][param_id] = usage_mapping[param_id](
                                        param.get(param_id))
                                logger.info(
                                    f"supplyTime: {self.device_data['supplyTime']}")
                            except ValueError:
                                logging.warning(
                                    f"Invalid total power supply time value: {totalPowerSupplyTime}")
                    except Exception as e:
                        logging.error(f"Error processing egy: {e}")

                # 仅在有有效消耗值时更新和发布
                if gas_consumption:
                    self._publish_gas_consumption()
                if totalPowerSupplyTime:
                    self._publish_supply_time()

        except json.JSONDecodeError:
            logging.error("Failed to parse JSON message")
        except Exception as e:
            logging.error(f"Unexpected error in message processing: {e}")
    
    def init_data(self):
        # 初始化数据
        mode_codes = {
            "energySavingMode": ["采暖节能", "快速采暖/节能"],
            "outdoorMode": ["采暖外出", "快速采暖/外出"],
            "rapidHeating": ["快速采暖", "快速采暖/节能", "快速采暖/外出", "快速采暖/预约"],
        }
        _mode = os.getenv('OPERATION_MODE')
        if _mode is None:
            logging.error("OPERATION_MODE is not set")
            return

        result = next((mode for mode, values in mode_codes.items()
                      if _get_operation_mode(_mode) in values), None)
        set_rinnai_mode(result)

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
