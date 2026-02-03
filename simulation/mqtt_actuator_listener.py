import json
import threading
import paho.mqtt.client as mqtt

def start_actuator_listener(host, port, topic, light_on, light_off, buzzer_on, buzzer_off, stop_event):
    def on_connect(client, userdata, flags, rc):
        print("[PI1] actuator mqtt connected rc=", rc)
        client.subscribe(topic)
        print("[PI1] subscribed to", topic)

    def on_message(client, userdata, msg):
        try:
            payload = msg.payload.decode("utf-8")
            cmd = json.loads(payload)

            device = cmd.get("device")   # "DL" ili "DB"
            action = cmd.get("action")   # "on" ili "off"

            if device == "DL":
                (light_on if action == "on" else light_off)()
                print("[PI1] Door light:", action)
            elif device == "DB":
                (buzzer_on if action == "on" else buzzer_off)()
                print("[PI1] Buzzer:", action)
        except Exception as e:
            print("[PI1] actuator cmd error:", e)

    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(host, port, keepalive=60)
    client.loop_start()

    def _stopper():
        stop_event.wait()
        try:
            client.loop_stop()
            client.disconnect()
        except:
            pass

    t = threading.Thread(target=_stopper, daemon=True)
    t.start()
    return t
