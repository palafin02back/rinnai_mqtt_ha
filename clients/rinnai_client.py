import json
import logging
from .mqtt_client import MQTTClientBase, MQTTConfig
from processors.message_processor import MessageProcessor


class RinnaiClient(MQTTClientBase):
    def __init__(self, config, message_processor: MessageProcessor):
        mqtt_config = MQTTConfig(
            host=config.RINNAI_MQTT_HOST,
            port=config.RINNAI_MQTT_PORT,
            username=config.RINNAI_USERNAME,
            password=config.RINNAI_PASSWORD,
            use_tls=True
        )
        super().__init__("rinnai_ha_bridge", mqtt_config)
        self.config = config
        self.message_processor = message_processor
        self.topics = config.get_rinnai_topics()
        logging.info(f"Rinnai topics: {self.topics}")

    def on_connect(self, client, userdata, flags, rc):
        logging.info(f"Rinnai MQTT connect status: {rc}")
        if rc == 0:
            for topic in self.topics.values():
                self.subscribe(topic)

    def on_message(self, client, userdata, msg):
        try:
            logging.info(
                f"Rinnai msg topic: {msg.topic}, payload: {json.loads(msg.payload.decode('utf-8'))}")
            self.message_processor.process_message(msg)
        except Exception as e:
            logging.error(f"Rinnai message error: {e}")

    def set_temperature(self, heat_type, temperature):
        if not heat_type:
            raise ValueError("Error: heat type not specified")

        request_payload = {
            "code": self.config.AUTH_CODE,
            "enl": [
                {
                    "data": hex(temperature)[2:].upper().zfill(2),
                    "id": heat_type
                }
            ],
            "id": self.config.DEVICE_TYPE,
            "ptn": "J00",
            "sum": "1"
        }
        self.publish(self.topics["set"], json.dumps(request_payload), qos=1)
        logging.info(f"Set {heat_type} temperature to {temperature}°C")

    def set_mode(self, mode):
        if not mode:
            raise ValueError("Error: mode not specified")

        request_payload = {
            "code": self.config.AUTH_CODE,
            "enl": [
                {
                    "data": "31",
                    "id": mode
                }
            ],
            "id": self.config.DEVICE_TYPE,
            "ptn": "J00",
            "sum": "1"
        }
        self.publish(self.topics["set"], json.dumps(request_payload), qos=1)
        logging.info(f"Set mode to: {mode}")

    def set_default_status(self):
        default_status = {'enl': []}
        for key, value in self.config.INIT_STATUS.items():
            default_status['enl'].append({'id': key, 'data': value})
        self.message_processor._process_device_info(default_status)
        self.message_processor.notify_observers()
