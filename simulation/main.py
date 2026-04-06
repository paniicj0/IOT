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

from system_state import SystemState

try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
except:
    GPIO = None


def make_record(settings, sensor_code: str, value, simulated_override=None):
    if simulated_override is None:
        simulated_flag = settings.get(sensor_code, {}).get("simulated", True)
    else:
        simulated_flag = bool(simulated_override)

    return {
        "pi_id": settings["device"]["pi_id"],
        "device_name": settings["device"]["device_name"],
        "sensor": sensor_code,
        "value": value,
        "simulated": simulated_flag,
        "timestamp": datetime.utcnow().isoformat()
    }


def push_alarm_status(settings, active: bool, reason: str):
    push(make_record(settings, "ALARM_STATUS", {
        "active": active,
        "reason": reason
    }, True))


def alarm_on(settings, system_state, buzzer_on, reason="UNKNOWN"):
    if not system_state.is_alarm_active():
        system_state.activate_alarm()
        print(f"[ALARM] ON ({reason})")
        buzzer_on()
        push_alarm_status(settings, True, reason)


def alarm_off(settings, system_state, buzzer_off, reason="PIN_OK"):
    if system_state.is_alarm_active():
        system_state.deactivate_alarm()
        print(f"[ALARM] OFF ({reason})")
        buzzer_off()
        push_alarm_status(settings, False, reason)


# --- DS hold detection ---
ds_state = {
    "DS1": {"pressed": False, "timer": None, "triggered": False},
    "DS2": {"pressed": False, "timer": None, "triggered": False},
}
ds_lock = threading.Lock()

# --- DUS state ---
dus_lock = threading.Lock()
last_dus_distance = {
    "DUS1": None,
    "DUS2": None,
}


def _start_ds_hold_timer(ds_code: str, stop_event, push_event_fn):
    def fire():
        with ds_lock:
            st = ds_state.get(ds_code)
            if st is None or stop_event.is_set():
                return
            if st["pressed"] and not st["triggered"]:
                st["triggered"] = True
            else:
                return

        push_event_fn(ds_code)

    t = threading.Timer(5.0, fire)
    t.daemon = True
    t.start()
    return t


def handle_people_count(sensor_code: str, system_state, settings):
    with dus_lock:
        distance = last_dus_distance.get(sensor_code)

    if distance is None:
        return

    threshold = 50.0

    if distance <= threshold:
        system_state.add_person()
        action = "ENTRY"
    else:
        before = system_state.get_people_count()
        system_state.remove_person()
        after = system_state.get_people_count()
        action = "EXIT" if before > 0 else "EXIT_IGNORED"

    count = system_state.get_people_count()

    print(f"[PEOPLE] {action} via {sensor_code}, count={count}")

    push(make_record(settings, "PEOPLE_COUNT", {
        "action": action,
        "source": sensor_code,
        "distance_cm": distance,
        "count": count
    }, True))


if __name__ == "__main__":

    settings_path = sys.argv[1] if len(sys.argv) > 1 else "settings.json"
    settings = load_settings(settings_path)

    system_state = SystemState(settings.get("security", {}).get("pin_code", "1234"))

    stop_event = threading.Event()
    threads = []

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
        light_on = light_off = lambda: None
        buzzer_on = buzzer_off = lambda: None

        if "DL" in settings:
            light_on, light_off = create_door_light(settings["DL"])

        if "DB" in settings:
            buzzer_on, buzzer_off = create_buzzer(settings["DB"])

        # ---------------- DS1 ----------------
        if "DS1" in settings:
            def ds1_handler(v):
                push(make_record(settings, "DS1", v))
                pressed = (v.get("value") == 1)

                if pressed and system_state.is_armed():
                    alarm_on(settings, system_state, buzzer_on, "DS1_ARMED")

                def push_alarm_event(code):
                    alarm_on(settings, system_state, buzzer_on, "DS1_HELD")

                with ds_lock:
                    st = ds_state["DS1"]

                    if pressed and not st["pressed"]:
                        st["pressed"] = True
                        st["triggered"] = False
                        st["timer"] = _start_ds_hold_timer("DS1", stop_event, push_alarm_event)

                    elif not pressed and st["pressed"]:
                        st["pressed"] = False
                        if st["timer"]:
                            st["timer"].cancel()

            run_ds1(settings["DS1"], threads, stop_event, on_value=ds1_handler)

        # ---------------- DS2 ----------------
        if "DS2" in settings:
            def ds2_handler(v):
                push(make_record(settings, "DS2", v))
                pressed = (v.get("value") == 1)

                if pressed and system_state.is_armed():
                    alarm_on(settings, system_state, buzzer_on, "DS2_ARMED")

                def push_alarm_event(code):
                    alarm_on(settings, system_state, buzzer_on, "DS2_HELD")

                with ds_lock:
                    st = ds_state["DS2"]

                    if pressed and not st["pressed"]:
                        st["pressed"] = True
                        st["timer"] = _start_ds_hold_timer("DS2", stop_event, push_alarm_event)

                    elif not pressed and st["pressed"]:
                        st["pressed"] = False
                        if st["timer"]:
                            st["timer"].cancel()

            run_ds2(settings["DS2"], threads, stop_event, on_value=ds2_handler)

        # ---------------- DMS ----------------
        if "DMS" in settings:
            def dms_handler(v):
                if v.get("value") == 1:
                    pin = input("PIN: ")

                    if system_state.check_pin(pin):
                        if system_state.is_alarm_active():
                            alarm_off(settings, system_state, buzzer_off)
                            system_state.disarm()
                        else:
                            print("Arming...")
                            system_state.arm_pending()

                            def arm():
                                if system_state.is_pending_arm():
                                    system_state.arm_now()
                                    print("ARMED")

                            threading.Timer(10, arm).start()

            run_dms(settings["DMS"], threads, stop_event, on_value=dms_handler)

        # ---------------- GSG ----------------
        if "GSG" in settings:
            def gsg_handler(v):
                mag = float(v.get("value", 0))
                if mag >= 0.7:
                    alarm_on(settings, system_state, buzzer_on, "GSG")

            run_gsg(settings["GSG"], threads, stop_event, on_value=gsg_handler)

        # ---------------- DPIR1 ----------------
        if "DPIR1" in settings:
            def dpir1_handler(v):
                push(make_record(settings, "DPIR1", v))

                if v.get("value") == 1:
                    light_on()
                    threading.Timer(10, light_off).start()

                    handle_people_count("DUS1", system_state, settings)

                    if system_state.get_people_count() == 0:
                        alarm_on(settings, system_state, buzzer_on, "EMPTY_ROOM")

            run_dpir1(settings["DPIR1"], threads, stop_event, on_value=dpir1_handler)

        # ---------------- DPIR2 ----------------
        if "DPIR2" in settings:
            def dpir2_handler(v):
                push(make_record(settings, "DPIR2", v))

                if v.get("value") == 1:
                    handle_people_count("DUS2", system_state, settings)

                    if system_state.get_people_count() == 0:
                        alarm_on(settings, system_state, buzzer_on, "EMPTY_ROOM")

            run_dpir2(settings["DPIR2"], threads, stop_event, on_value=dpir2_handler)

        # ---------------- DUS1 ----------------
        if "DUS1" in settings:
            def dus1_handler(v):
                with dus_lock:
                    last_dus_distance["DUS1"] = float(v.get("distance_cm", v.get("value", 0)))

            run_dus1(settings["DUS1"], threads, stop_event, on_value=dus1_handler)

        # ---------------- DUS2 ----------------
        if "DUS2" in settings:
            def dus2_handler(v):
                with dus_lock:
                    last_dus_distance["DUS2"] = float(v.get("distance_cm", v.get("value", 0)))

            run_dus2(settings["DUS2"], threads, stop_event, on_value=dus2_handler)

        actuator_menu(light_on, light_off, buzzer_on, buzzer_off)

    except KeyboardInterrupt:
        print("Stopping...")

    finally:
        stop_event.set()
        pub.close()