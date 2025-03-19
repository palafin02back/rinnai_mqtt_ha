import paho.mqtt.client as mqtt
import uuid
import logging
import datetime
from abc import ABC, abstractmethod


class MQTTClientBase(ABC):
    def __init__(self, client_prefix):
        ts = datetime.datetime.now()
        self.client = mqtt.Client(
            client_id=f"{client_prefix}:{ts.second}{ts.microsecond}",
            callback_api_version=mqtt.CallbackAPIVersion.VERSION1
        )
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.topics = {}

    @abstractmethod
    def on_connect(self, client, userdata, flags, rc):
        pass

    @abstractmethod
    def on_message(self, client, userdata, msg):
        pass

    def connect(self, host, port, keepalive=60):
        self.client.connect(host, port, keepalive)

    def disconnect(self):
        self.client.disconnect()

    def publish(self, topic, payload, qos=0, retain=False):
        return self.client.publish(topic, payload, qos, retain)

    def subscribe(self, topics):
        self.client.subscribe(topics)

    def start(self):
        self.client.loop_start()

    def stop(self):
        self.client.loop_stop()
