import json
import logging
from .mqtt_client import MQTTClientBase, MQTTConfig


class RinnaiHomeAssistantDiscovery(MQTTClientBase):
    def __init__(self, config):
        mqtt_config = MQTTConfig(
            host=config.LOCAL_MQTT_HOST,
            port=config.LOCAL_MQTT_PORT,
            username=config.LOCAL_MQTT_USERNAME,
            password=config.LOCAL_MQTT_PASSWORD,
            use_tls=config.LOCAL_MQTT_TLS
        )
        super().__init__("rinnai_ha_discovery", mqtt_config)
        self.config = config
        self.unique_id = "rinnai_heater"
        self.discovery_prefix = "homeassistant"

    def on_connect(self, client, userdata, flags, rc):
        logging.info(f"HomeAssistant MQTT connect status: {rc}")

    def on_message(self, client, userdata, msg):
        pass

    def generate_config(self, component_type, object_id, name, topic, config_type='sensor', unit=None):
        """生成通用配置"""
        base_topic = f"{self.discovery_prefix}/{component_type}/rinnai_{object_id}"

        config = {
            "name": name,
            "unique_id": f"{self.unique_id}_{object_id}",
            "state_topic": self.config.get_local_topics().get("state"),
            "value_template": f"{{{{ value_json.{object_id} }}}}",
            "device": {
                "identifiers": [self.unique_id],
                "name": "Rinnai Heater",
                "manufacturer": "Rinnai",
                "model": "G56"
            }
        }

        if unit:
            config["unit_of_measurement"] = unit

        if config_type == 'sensor' and object_id == 'gasConsumption':
            config.update({
                "state_topic": self.config.get_local_topics().get("gas"),
                "value_template": f"{{{{ (value_json.{object_id} | float) / 10000 }}}}",
                "unit_of_measurement": "m³",
                "device_class": "gas"
            })
        elif config_type == 'sensor' and 'supplyTime' in object_id:
            config.update({
                "state_topic": self.config.get_local_topics().get("supplyTime"),
                "value_template": f"{{{{ value_json.{object_id.split('/')[-1]} }}}}"
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
                "state_topic": self.config.get_local_topics().get("state"),
                "command_topic": topic,
                "payload_on": "ON",
                "payload_off": "OFF",
                "value_template": self.get_switch_value_template(object_id)
            })

        return f"{base_topic}/config", json.dumps(config)

    def get_switch_value_template(self, object_id):
        """根据 object_id 返回对应的 value_template，用于解析 switch 的状态"""
        mode_codes = {
            "energySavingMode": ["采暖节能", "快速采暖/节能"],
            "outdoorMode": ["采暖外出", "快速采暖/外出"],
            "rapidHeating": ["快速采暖", "快速采暖/节能", "快速采暖/外出", "快速采暖/预约"],
        }

        if object_id == "summerWinter":
            return "{% if value_json.operationMode in ['关机', '采暖关闭', '休眠'] %}OFF{% else %}ON{% endif %}"
        else:
            codes = mode_codes.get(object_id, [])
            codes_string = ','.join(f"'{code}'" for code in codes)
            return f"{{% if value_json.operationMode in [{codes_string}] %}}ON{{% else %}}OFF{{% endif %}}"

    def publish_discovery_configs(self):
        """发布Home Assistant自动发现配置"""
        try:
            self.connect()

            # 传感器配置
            sensors = [
                ("模式", "operationMode", None),
                ("燃烧状态", "burningState", None),
                ("热水温度", "hotWaterTempSetting", "°C"),
                ("锅炉温度", "heatingTempSettingNM", "°C"),
                ("锅炉温度/节能", "heatingTempSettingHES", "°C"),
                ("耗气量", "gasConsumption", "m³"),
                ("供电时间", "supplyTime/totalPowerSupplyTime", "h"),
                ("使用时间", "supplyTime/actualUseTime", "h"),
                ("燃烧时间", "supplyTime/totalHeatingBurningTime", "h"),
                ("地暖燃烧次数", "supplyTime/heatingBurningTimes", "次"),
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
                self.publish(topic, config, retain=True)

            # 温度控制
            temp_controls = [
                ("热水温度", "hotWaterTempSetting", self.config.get_local_topics().get("hotWaterTempSetting")),
                ("锅炉温度", "heatingTempSettingNM", self.config.get_local_topics().get("heatingTempSettingNM")),
                ("锅炉温度/节能", "heatingTempSettingHES", self.config.get_local_topics().get("heatingTempSettingHES"))
            ]

            for label, object_id, topic in temp_controls:
                number_topic, number_config = self.generate_config(
                    'number',
                    object_id,
                    f"Rinnai {label}",
                    topic,
                    'number'
                )
                self.publish(number_topic, number_config, retain=True)

            # 模式控制
            mode_controls = [
                ("节能模式", "energySavingMode", self.config.get_local_topics().get("energySavingMode")),
                ("外出模式", "outdoorMode", self.config.get_local_topics().get("outdoorMode")),
                ("快速采暖", "rapidHeating", self.config.get_local_topics().get("rapidHeating")),
                ("采暖开关", "summerWinter", self.config.get_local_topics().get("summerWinter"))
            ]

            for label, object_id, topic in mode_controls:
                switch_topic, switch_config = self.generate_config(
                    'switch',
                    object_id,
                    f"Rinnai {label}",
                    topic,
                    'switch'
                )
                self.publish(switch_topic, switch_config, retain=True)

        except Exception as e:
            logging.error(f"Failed to publish discovery configs: {e}")
        finally:
            self.disconnect()
