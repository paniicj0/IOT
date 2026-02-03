import json
import paho.mqtt.client as mqtt


class MqttCmdPublisher:
    def __init__(self, host: str, port: int):
        self.client = mqtt.Client()
        self.client.connect(host, port, keepalive=60)

    def send(self, topic: str, payload: dict):
        self.client.publish(topic, json.dumps(payload))
