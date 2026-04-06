import json
import threading
import paho.mqtt.client as mqtt


def start_actuator_listener(
    host,
    port,
    topic,
    light_on,
    light_off,
    buzzer_on,
    buzzer_off,
    stop_event,
    *,
    pi_label="PI",
    set_4sd=None,
    add_4sd=None,
    blink_4sd=None,
    stop_blink_4sd=None,
    rgb_on=None,
    rgb_off=None,
    rgb_set_color=None
):
    def log(*args):
        print(f"[{pi_label}]", *args)

    def on_connect(client, userdata, flags, rc):
        log("actuator mqtt connected rc=", rc)
        client.subscribe(topic)
        log("subscribed to", topic)

    def on_message(client, userdata, msg):
        try:
            payload = msg.payload.decode("utf-8")
            cmd = json.loads(payload)

            device = cmd.get("device")
            action = cmd.get("action")

            # ---- DOOR LIGHT ----
            if device == "DL":
                if action == "on":
                    light_on()
                elif action == "off":
                    light_off()
                log("Door light:", action)
                return

            # ---- BUZZER ----
            if device == "DB":
                if action == "on":
                    buzzer_on()
                elif action == "off":
                    buzzer_off()
                log("Buzzer:", action)
                return

            # ---- 4SD ----
            if device == "4SD":
                if action == "set":
                    if set_4sd is None:
                        log("4SD set ignored (not configured)")
                        return
                    seconds = int(cmd.get("seconds", 0))
                    set_4sd(seconds)
                    log("4SD set:", seconds)
                    return

                if action == "add":
                    if add_4sd is None:
                        log("4SD add ignored (not configured)")
                        return
                    seconds = int(cmd.get("seconds", 0))
                    add_4sd(seconds)
                    log("4SD add:", seconds)
                    return

                if action == "blink":
                    if blink_4sd is None:
                        log("4SD blink ignored (not configured)")
                        return
                    blink_4sd()
                    log("4SD blink ON")
                    return

                if action == "stop_blink":
                    if stop_blink_4sd is None:
                        log("4SD stop_blink ignored (not configured)")
                        return
                    stop_blink_4sd()
                    log("4SD blink OFF")
                    return

                log("Unknown 4SD action:", action)
                return

            # ---- BRGB ----
            if device == "BRGB":
                if action == "on":
                    if rgb_on is None:
                        log("BRGB on ignored (not configured)")
                        return
                    rgb_on()
                    log("BRGB ON")
                    return

                if action == "off":
                    if rgb_off is None:
                        log("BRGB off ignored (not configured)")
                        return
                    rgb_off()
                    log("BRGB OFF")
                    return

                if action == "set_color":
                    if rgb_set_color is None:
                        log("BRGB set_color ignored (not configured)")
                        return
                    color = str(cmd.get("color", "WHITE")).upper()
                    rgb_set_color(color)
                    log("BRGB COLOR:", color)
                    return

                log("Unknown BRGB action:", action)
                return

            log("Unknown device:", device, "payload:", cmd)

        except Exception as e:
            log("actuator cmd error:", e)

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