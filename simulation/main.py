import threading
import sys
from datetime import datetime

from settings import load_settings

# PI1 senzori
from components.ds1 import run_ds1
from components.dpir1 import run_dpir1
from components.dms import run_dms
from components.dus1 import run_dus1

# PI2 senzori
from components.ds2 import run_ds2
from components.dpir2 import run_dpir2
from components.dus2 import run_dus2
from components.dht3 import run_dht3
from components.btn import run_btn
from components.gsg import run_gsg
from components.display_4sd import create_4sd

# Aktuatori
from components.door_light import create_door_light
from components.buzzer import create_buzzer
from actuator_menu import actuator_menu

# Telemetrija + MQTT
from telemetry_buffer import push, telemetry_q
from mqtt_client import MqttPublisher
from batch_sender import start_batch_sender_daemon
from mqtt_actuator_listener import start_actuator_listener

try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
except:
    GPIO = None


def make_record(settings, sensor_code: str, value):
    return {
        "pi_id": settings["device"]["pi_id"],
        "device_name": settings["device"]["device_name"],
        "sensor": sensor_code,
        "value": value,
        "simulated": settings[sensor_code]["simulated"],
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":

    # -------- SETTINGS ARGUMENT --------
    settings_path = sys.argv[1] if len(sys.argv) > 1 else "settings.json"
    settings = load_settings(settings_path)

    pi_id = settings["device"]["pi_id"]
    print(f"Starting {pi_id} app")

    stop_event = threading.Event()
    threads = []

    # -------- MQTT + BATCH --------
    pub = MqttPublisher(settings["mqtt"]["host"], settings["mqtt"]["port"])

    start_batch_sender_daemon(
        telemetry_q,
        pub,
        settings["mqtt"]["topic_sensors"],
        settings["batch"]["size"],
        settings["batch"]["interval_sec"],
        stop_event
    )

    try:
        # -------- ACTUATORS (create first, for DPIR->DL logic) --------
        light_on = light_off = lambda: None
        buzzer_on = buzzer_off = lambda: None

        if "DL" in settings:
            light_on, light_off = create_door_light(settings["DL"])

        if "DB" in settings:
            buzzer_on, buzzer_off = create_buzzer(settings["DB"])

        # -------- 4SD DISPLAY --------
        set_4sd = add_4sd = blink_4sd = stop_blink_4sd = None

        if "4SD" in settings:
            set_4sd, add_4sd, blink_4sd, stop_blink_4sd, run_4sd_loop = create_4sd(settings["4SD"])
            t4 = threading.Thread(target=run_4sd_loop, args=(stop_event,), daemon=True)
            t4.start()
            threads.append(t4)

        # -------- MQTT ACTUATOR LISTENER --------
        act_t = start_actuator_listener(
            settings["mqtt"]["host"],
            settings["mqtt"]["port"],
            settings["mqtt"]["topic_actuators"],
            light_on, light_off,
            buzzer_on, buzzer_off,
            stop_event,
            pi_label=pi_id,
            set_4sd=set_4sd,
            add_4sd=add_4sd,
            blink_4sd=blink_4sd,
            stop_blink_4sd=stop_blink_4sd
        )
        threads.append(act_t)

        # -------- SENSORS AUTO START --------

        # PI1
        if "DS1" in settings:
            run_ds1(settings["DS1"], threads, stop_event,
                    on_value=lambda v: push(make_record(settings, "DS1", v)))

        if "DPIR1" in settings:
            def dpir1_handler(v):
                push(make_record(settings, "DPIR1", v))

                # DPIR1 -> DL ON 10s (zahtev)
                if v.get("value") == 1 and "DL" in settings:
                    print("[LOGIC] DPIR1 motion -> DL ON for 10s")
                    light_on()

                    def turn_off():
                        print("[LOGIC] DL OFF (10s expired)")
                        light_off()

                    t = threading.Timer(10, turn_off)
                    t.daemon = True
                    t.start()

            run_dpir1(settings["DPIR1"], threads, stop_event, on_value=dpir1_handler)

        if "DMS" in settings:
            run_dms(settings["DMS"], threads, stop_event,
                    on_value=lambda v: push(make_record(settings, "DMS", v)))

        if "DUS1" in settings:
            run_dus1(settings["DUS1"], threads, stop_event,
                     on_value=lambda v: push(make_record(settings, "DUS1", v)))

        # PI2
        if "DS2" in settings:
            run_ds2(settings["DS2"], threads, stop_event,
                    on_value=lambda v: push(make_record(settings, "DS2", v)))

        if "DPIR2" in settings:
            run_dpir2(settings["DPIR2"], threads, stop_event,
                      on_value=lambda v: push(make_record(settings, "DPIR2", v)))

        if "DUS2" in settings:
            run_dus2(settings["DUS2"], threads, stop_event,
                     on_value=lambda v: push(make_record(settings, "DUS2", v)))

        if "DHT3" in settings:
            run_dht3(settings["DHT3"], threads, stop_event,
                     on_value=lambda v: push(make_record(settings, "DHT3", v)))

        if "BTN" in settings:
            run_btn(settings["BTN"], threads, stop_event,
                    on_value=lambda v: push(make_record(settings, "BTN", v)))

        if "GSG" in settings:
            run_gsg(settings["GSG"], threads, stop_event,
                    on_value=lambda v: push(make_record(settings, "GSG", v)))

        # -------- LOCAL MENU --------
        if "DL" in settings or "DB" in settings:
            actuator_menu(light_on, light_off, buzzer_on, buzzer_off)
        else:
            stop_event.wait()

    except KeyboardInterrupt:
        print("\nStopping app (KeyboardInterrupt)")

    finally:
        stop_event.set()
        for t in threads:
            t.join(timeout=3)

        pub.close()

        if GPIO is not None:
            try:
                GPIO.cleanup()
            except:
                pass

        print("App stopped.")