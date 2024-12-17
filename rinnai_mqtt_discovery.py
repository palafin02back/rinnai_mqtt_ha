import paho.mqtt.client as mqtt
import json
import uuid
import os
from dotenv import load_dotenv
import logging

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.disabled = os.getenv('LOGGING', 'False') == 'true'

class RinnaiHomeAssistantDiscovery:
    def __init__(self):
        self.mqtt_host = os.getenv('LOCAL_MQTT_HOST')
        self.mqtt_port = int(os.getenv('LOCAL_MQTT_PORT', '1883'))
        # 唯一标识符
        self.unique_id = f"rinnai_heater"
        # MQTT客户端
        self.client = mqtt.Client(
            client_id=f"ha_discovery_{str(uuid.uuid4())[:8]}",
            callback_api_version=mqtt.CallbackAPIVersion.VERSION1
        )
        self.client.on_connect = self.on_connect
        # Home Assistant Discovery主题
        self.discovery_prefix = "homeassistant"

    def on_connect(self, client, userdata, flags, rc):
        logger.info(f"HomeAssistant MQTT connect status: {rc}")

    def generate_config(self, component_type, object_id, name, topic, config_type='sensor', unit=None):
        """
        生成通用配置
        """
        base_topic = f"{self.discovery_prefix}/{component_type}/rinnai_{object_id}"

        config = {
            "name": name,
            "unique_id": f"{self.unique_id}_{object_id}",
            "state_topic": "local_mqtt/rinnai/state",
            "value_template": f"{{{{ value_json.{object_id} }}}}",
            "device": {
                "identifiers": [self.unique_id],
                "name": "Rinnai Heater",
                "manufacturer": "Rinnai",
                "model": "G56"
            }
        }
        # 添加单位
        if unit:
            config["unit_of_measurement"] = unit

        if config_type == 'sensor' and object_id == 'gasConsumption':
            config.update({
                "state_topic": "local_mqtt/rinnai/usage/gas",
                "unit_of_measurement": "m³",
                "device_class": "gas"
            })
        elif config_type == 'sensor' and 'supplyTime' in object_id:
            config.update({
                "state_topic": "local_mqtt/rinnai/usage/supplyTime",
                "value_template": f"{{{{ value_json.{object_id.split('/')[-1]} }}}}",
            })


        if config_type == 'number' and object_id == 'hotWaterTempSetting':
            config.update({
                "command_topic": topic,
                "min": 35,
                "max": 60,
                "step": 1,
                "unit_of_measurement": "°C"
            })
        elif config_type == 'number' and (object_id == 'heatingTempSettingNM' or object_id == 'heatingTempSettingHES'):
            config.update({
                "command_topic": topic,
                "min": 45,
                "max": 70,
                "step": 1,
                "unit_of_measurement": "°C"
            })
        elif config_type == 'switch':
            config.update({
                "state_topic": "local_mqtt/rinnai/state",
                "command_topic": topic,
                "payload_on": "ON",
                "payload_off": "OFF",
                "value_template": self.get_switch_value_template(object_id)
            })

        return f"{base_topic}/config", json.dumps(config)


    def get_switch_value_template(self, object_id):
        """
        根据 object_id 返回对应的 value_template，用于解析 switch 的状态
        """
        # 定义模式对应的 operationMode 值集合
        mode_codes = {
            "energySavingMode": ["采暖节能", "快速采暖/节能"],
            "outdoorMode": ["采暖外出", "快速采暖/外出"],
            "rapidHeating": ["快速采暖", "快速采暖/节能", "快速采暖/外出", "快速采暖/预约"],
        }

        if object_id == "summerWinter":
            # 对于采暖开关，operationMode 为 '0', '1', '2' 时为 OFF，其它为 ON
            return "{% if value_json.operationMode in ['关机', '采暖关闭', '休眠'] %}OFF{% else %}ON{% endif %}"
        else:
            codes = mode_codes.get(object_id, [])
            # 构建用于判断的模板字符串
            codes_string = ','.join(f"'{code}'" for code in codes)
            return f"{{% if value_json.operationMode in [{codes_string}] %}}ON{{% else %}}OFF{{% endif %}}"




    def publish_discovery_configs(self):
        """
        发布Home Assistant自动发现配置
        """
        self.client.connect(self.mqtt_host, self.mqtt_port, 60)

        # 传感器配置
        sensors = [
            # ("室温控制", "roomTempControl", "°C"),
            # ("出水温度", "heatingOutWaterTempControl", "°C"),
            ("模式", "operationMode", None),
            ("燃烧状态", "burningState", None),
            ("热水温度", "hotWaterTempSetting", "°C"),
            ("锅炉温度", "heatingTempSettingNM", "°C"),
            ("锅炉温度/节能", "heatingTempSettingHES", "°C"),
            ("耗气量", "gasConsumption", "m³"),
            ("总供电时间", "supplyTime/totalPowerSupplyTime", "h"),
            ("实际使用时间", "supplyTime/actualUseTime", "h"),
            ("总采暖燃烧时间", "supplyTime/totalHeatingBurningTime", "h"),
            ("总热水燃烧时间", "supplyTime/totalHotWaterBurningTime", "h"),
            ("采暖燃烧次数", "supplyTime/heatingBurningTimes", "次"),
            ("热水燃烧次数", "supplyTime/hotWaterBurningTimes", "次")

        ]

        for label, object_id, unit in sensors:
            topic, config = self.generate_config(
                'sensor',
                object_id,
                f"Rinnai {label}",
                None,
                'sensor',
                unit
            )
            self.client.publish(topic, config, retain=True)

        #温度控制
        temp_controls = [
            ("热水温度", "hotWaterTempSetting","local_mqtt/rinnai/set/temp/hotWaterTempSetting"),
            ("锅炉温度", "heatingTempSettingNM","local_mqtt/rinnai/set/temp/heatingTempSettingNM"),
            ("锅炉温度/节能", "heatingTempSettingHES","local_mqtt/rinnai/set/temp/heatingTempSettingHES")
        ]


        for label, object_id, topic in temp_controls:
            number_topic, number_config = self.generate_config(
                'number',
                object_id,
                f"Rinnai {label}",
                topic,
                'number'
            )
            self.client.publish(number_topic, number_config, retain=True)

        # 模式控制
        mode_controls = [
            ("节能模式", "energySavingMode", "local_mqtt/rinnai/set/mode/energySavingMode"),
            ("外出模式", "outdoorMode", "local_mqtt/rinnai/set/mode/outdoorMode"),
            ("快速采暖", "rapidHeating", "local_mqtt/rinnai/set/mode/rapidHeating"),
            ("采暖开关", "summerWinter", "local_mqtt/rinnai/set/mode/summerWinter")
        ]

        for label, object_id, topic in mode_controls:
            switch_topic, switch_config = self.generate_config(
                'switch',
                object_id,
                f"Rinnai {label}",
                topic,
                'switch'
            )
            self.client.publish(switch_topic, switch_config, retain=True)

        self.client.disconnect()


def main():
    discovery = RinnaiHomeAssistantDiscovery()
    discovery.publish_discovery_configs()


if __name__ == "__main__":
    main()
