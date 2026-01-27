import threading
from settings import load_settings

from components.ds1 import run_ds1
from components.dpir1 import run_dpir1
from components.dms import run_dms
from components.dus1 import run_dus1

from components.door_light import create_door_light
from components.buzzer import create_buzzer
from actuator_menu import actuator_menu

from telemetry_buffer import push, telemetry_q
from mqtt_client import MqttPublisher
from batch_sender import start_batch_sender_daemon

from datetime import datetime

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
    print("Starting PI1 app (KT2)")
    settings = load_settings()

    stop_event = threading.Event()
    threads = []

    # MQTT + batch sender
    pub = MqttPublisher(settings["mqtt"]["host"], settings["mqtt"]["port"])
    batch_t = start_batch_sender_daemon(
        telemetry_q,
        pub,
        settings["mqtt"]["topic_sensors"],
        settings["batch"]["size"],
        settings["batch"]["interval_sec"],
        stop_event
    )

    try:
        # senzori: prosledi callback koji pravi record i ubacuje u queue
        run_ds1(settings["DS1"], threads, stop_event, on_value=lambda v: push(make_record(settings, "DS1", v)))
        run_dpir1(settings["DPIR1"], threads, stop_event, on_value=lambda v: push(make_record(settings, "DPIR1", v)))
        run_dms(settings["DMS"], threads, stop_event, on_value=lambda v: push(make_record(settings, "DMS", v)))
        run_dus1(settings["DUS1"], threads, stop_event, on_value=lambda v: push(make_record(settings, "DUS1", v)))

        # aktuatori kao i pre
        light_on, light_off = create_door_light(settings["DL"])
        buzzer_on, buzzer_off = create_buzzer(settings["DB"])

        actuator_menu(light_on, light_off, buzzer_on, buzzer_off)

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
