import paho.mqtt.client as mqtt
import uuid
import logging
import ssl
from abc import ABC, abstractmethod


class MQTTConfig:
    def __init__(self, host, port, username=None, password=None, use_tls=False):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_tls = use_tls

    def apply_to_client(self, client):
        if self.use_tls:
            client.tls_set(
                cert_reqs=ssl.CERT_NONE,
                tls_version=ssl.PROTOCOL_TLSv1_2
            )
            client.tls_insecure_set(True)
            logging.info("MQTT TLS enabled")

        if self.username and self.password:
            client.username_pw_set(self.username, self.password)
            logging.info("MQTT authentication enabled")


class MQTTClientBase(ABC):
    def __init__(self, client_prefix, mqtt_config=None):
        self.client = mqtt.Client(
            client_id=f"{client_prefix}_{str(uuid.uuid4())[:8]}",
            callback_api_version=mqtt.CallbackAPIVersion.VERSION1
        )
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.topics = {}
        self.mqtt_config = mqtt_config

        if mqtt_config:
            mqtt_config.apply_to_client(self.client)

    @abstractmethod
    def on_connect(self, client, userdata, flags, rc):
        pass

    @abstractmethod
    def on_message(self, client, userdata, msg):
        pass

    def connect(self, host=None, port=None, keepalive=60):
        if self.mqtt_config:
            host = host or self.mqtt_config.host
            port = port or self.mqtt_config.port
        self.client.connect(host, port, keepalive)

    def disconnect(self):
        self.client.disconnect()

    def publish(self, topic, payload, qos=0, retain=False):
        try:
            return self.client.publish(topic, payload, qos, retain)
        except Exception as e:
            logging.error(f"Failed to publish to {topic}: {e}")
            raise

    def subscribe(self, topics):
        try:
            self.client.subscribe(topics)
        except Exception as e:
            logging.error(f"Failed to subscribe to {topics}: {e}")
            raise

    def start(self):
        self.client.loop_start()

    def stop(self):
        self.client.loop_stop()
