import json
import paho.mqtt.client as mqtt

def start_mqtt(influx_writer, host, port, topic="iot/+/sensors"):

    def on_connect(client, userdata, flags, rc):
        print(f"[MQTT] Connected rc={rc}")
        client.subscribe(topic)
        print(f"[MQTT] Subscribed to {topic}")

    def on_message(client, userdata, msg):
        print("[MQTT] message received on", msg.topic, "bytes=", len(msg.payload))

        try:
            batch = json.loads(msg.payload.decode())
            print("[MQTT] decoded type:", type(batch), "len:", (len(batch) if isinstance(batch, list) else "n/a"))

            if isinstance(batch, dict):
                batch = [batch]

            count = 0
            for rec in batch:
                print(
                    f"[MQTT] PI={rec.get('pi') or rec.get('pi_id')} | "
                    f"device={rec.get('device_name')} | "
                    f"sensor={rec.get('sensor_code') or rec.get('sensor')} | "
                    f"simulated={rec.get('simulated')}"
                )
                influx_writer.write_record(rec)
                count += 1

            print(f"[INFLUX] Written {count} records")

        except Exception as e:
            print("[ERROR] MQTT message handling:", e)
            print(msg.payload)

    print("[MQTT] Listener starting...")
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(host, port, 60)
    client.loop_forever()