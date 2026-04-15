import json
import paho.mqtt.client as mqtt

class MqttPublisher:
    def __init__(self, host: str, port: int):
        self.client = mqtt.Client()
        self.client.connect(host, port, keepalive=60)
        self.client.loop_start()

    def publish_json(self, topic: str, payload):
        self.client.publish(topic, json.dumps(payload))

    def close(self):
        try:
            self.client.loop_stop()
        except:
            pass
        try:
            self.client.disconnect()
        except:
            pass
