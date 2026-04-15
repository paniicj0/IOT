import threading
import sys
import time
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

# PI3 senzori
from components.dpir3 import run_dpir3
from components.dht1 import run_dht1
from components.dht2 import run_dht2
from components.lcd import create_lcd
from components.ir import run_ir

# Aktuatori
from components.door_light import create_door_light
from components.buzzer import create_buzzer
from components.brgb import create_brgb
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
except Exception:
    GPIO = None

last_disarm_time = 0
DISARM_COOLDOWN = 10  # sekundi


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
        "active": 1 if active else 0,
        "reason": reason
    }, True))

def push_system_armed_status(settings, armed: bool):
    push(make_record(settings, "SYSTEM_ARMED", {
        "armed": 1 if armed else 0
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


ds_state = {
    "DS1": {"pressed": False, "timer": None, "triggered": False},
    "DS2": {"pressed": False, "timer": None, "triggered": False},
}
ds_lock = threading.Lock()

dus_lock = threading.Lock()
last_dus_distance = {
    "DUS1": None,
    "DUS2": None,
}

dht_lock = threading.Lock()
last_dht_values = {
    "DHT1": None,
    "DHT2": None,
    "DHT3": None,
}

# ---- prekidač za auto alarm logiku ----
alarm_logic_enabled = True


def enable_alarm_logic():
    global alarm_logic_enabled
    alarm_logic_enabled = True
    print("[ALARM LOGIC] ENABLED")


def disable_alarm_logic():
    global alarm_logic_enabled
    alarm_logic_enabled = False
    print("[ALARM LOGIC] DISABLED")


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
        action = "EXIT" if before > 0 else "EXIT_IGNORED"

    count = system_state.get_people_count()

    print(f"[PEOPLE] {action} via {sensor_code}, count={count}")

    push(make_record(settings, "PEOPLE_COUNT", {
        "action": action,
        "source": sensor_code,
        "distance_cm": distance,
        "count": count
    }, True))


def start_lcd_rotation(lcd_write, stop_event):
    def worker():
        sensor_order = ["DHT1", "DHT2", "DHT3"]
        idx = 0

        while not stop_event.is_set():
            sensor_code = sensor_order[idx % len(sensor_order)]

            with dht_lock:
                dht_data = last_dht_values.get(sensor_code)

            if dht_data is not None:
                temp = dht_data["temperature"]
                hum = dht_data["humidity"]

                line1 = f"{sensor_code} T:{temp:.1f}C"
                line2 = f"H:{hum:.1f}%"
                lcd_write(line1, line2)

            idx += 1
            time.sleep(3)

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    return t


def push_brgb_state(settings, rgb_get_state):
    if rgb_get_state is None:
        return

    state = rgb_get_state()
    push(make_record(settings, "BRGB_STATE", state, simulated_override=True))


if __name__ == "__main__":

    settings_path = sys.argv[1] if len(sys.argv) > 1 else "settings.json"
    settings = load_settings(settings_path)

    system_state = SystemState(settings.get("security", {}).get("pin_code", "1234"))
    timer_add_seconds = int(settings.get("timer", {}).get("button_add_seconds", 30))

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
        rgb_on = rgb_off = rgb_set_color = lambda *args, **kwargs: None
        rgb_get_state = None

            # ----- AKTUATORI -----
        if "DL" in settings:
            light_on, light_off = create_door_light(settings["DL"])

        if "DB" in settings:
            buzzer_on, buzzer_off = create_buzzer(settings["DB"])

        if "BRGB" in settings:
            rgb_on, rgb_off, rgb_set_color, rgb_get_state = create_brgb(settings["BRGB"])

        # ----- 4SD INIT -----
        set_4sd = add_4sd = blink_4sd = stop_blink_4sd = None
        is_4sd_blinking = get_4sd_seconds = None


        # ===== INIT STATE SYNC (OVDE!!!) =====
        push_alarm_status(settings, system_state.is_alarm_active(), "INIT")
        push_system_armed_status(settings, system_state.is_armed())

        push(make_record(settings, "PEOPLE_COUNT", {
            "action": "INIT",
            "source": "SYSTEM",
            "distance_cm": 0,
            "count": system_state.get_people_count()
        }, True))

        if rgb_get_state is not None:
            push_brgb_state(settings, rgb_get_state)

        if get_4sd_seconds is not None and is_4sd_blinking is not None:
            push(make_record(settings, "4SD", {
                "seconds": get_4sd_seconds(),
                "blinking": is_4sd_blinking()
            }, True))
        # =====================================

        if "4SD" in settings:
            (
                set_4sd,
                add_4sd,
                blink_4sd,
                stop_blink_4sd,
                run_4sd_loop,
                is_4sd_blinking,
                get_4sd_seconds
            ) = create_4sd(settings["4SD"])

            t4 = threading.Thread(target=run_4sd_loop, args=(stop_event,), daemon=True)
            t4.start()
            threads.append(t4)

        lcd_write = lcd_clear = None
        if "LCD" in settings:
            lcd_write, lcd_clear, run_lcd_loop = create_lcd(settings["LCD"])
            tlcd = threading.Thread(target=run_lcd_loop, args=(stop_event,), daemon=True)
            tlcd.start()
            threads.append(tlcd)

            rot_t = start_lcd_rotation(lcd_write, stop_event)
            threads.append(rot_t)

        def handle_remote_pin(pin: str):
            global last_disarm_time

            print(f"######## HANDLE_REMOTE_PIN CALLED pin={pin} ########")

            if not system_state.check_pin(pin):
                print("[WEB/DMS] WRONG PIN")
                return

            print("[WEB/DMS] PIN OK")

            # 1) Ako je alarm aktivan -> ugasi alarm i disarmuj sistem
            if system_state.is_alarm_active():
                alarm_off(settings, system_state, buzzer_off, "PIN_OK")
                system_state.disarm()
                push_system_armed_status(settings, False)
                last_disarm_time = time.time()
                print("[SYSTEM] DISARMED")
                print("[COOLDOWN] Alarm disabled for 10s")
                return

            # 2) Ako je sistem vec armed -> disarm
            if system_state.is_armed():
                system_state.disarm()
                push_system_armed_status(settings, False)
                last_disarm_time = time.time()
                print("[SYSTEM] DISARMED")
                return

            # 3) Ako je armiranje u toku -> otkazi
            if system_state.is_pending_arm():
                system_state.disarm()
                push_system_armed_status(settings, False)
                print("[SYSTEM] ARMING CANCELED")
                return

            # 4) Inace pokreni armiranje za 10 sekundi
            print("[SYSTEM] Arming in 10 seconds...")
            system_state.arm_pending()

            def arm():
                if system_state.is_pending_arm():
                    system_state.arm_now()
                    push_system_armed_status(settings, True)
                    print("[SYSTEM] ARMED")

            t = threading.Timer(10, arm)
            t.daemon = True
            t.start()

        def handle_arm_system():
            print("######## HANDLE_ARM_SYSTEM CALLED ########")
            print("STATE alarm_active =", system_state.is_alarm_active())
            print("STATE armed =", system_state.is_armed())
            print("STATE pending =", system_state.is_pending_arm())

            if system_state.is_alarm_active():
                print("[ARM] alarm active -> turning OFF first")
                alarm_off(settings, system_state, buzzer_off, "AUTO_BEFORE_ARM")

            if system_state.is_armed():
                print("[ARM] already armed")
                return

            if system_state.is_pending_arm():
                print("[ARM] already pending")
                return

            print("[SYSTEM] Arming in 10 seconds...")
            system_state.arm_pending()

            def arm():
                if system_state.is_pending_arm():
                    system_state.arm_now()
                    enable_alarm_logic()
                    push_system_armed_status(settings, True)   
                    print("[SYSTEM] ARMED")

            t = threading.Timer(10, arm)
            t.daemon = True
            t.start()



        def handle_manual_alarm():
            alarm_on(settings, system_state, buzzer_on, "MANUAL_WEB")

        act_t = start_actuator_listener(
            settings["mqtt"]["host"],
            settings["mqtt"]["port"],
            settings["mqtt"]["topic_actuators"],
            light_on,
            light_off,
            buzzer_on,
            buzzer_off,
            stop_event,
            pi_label=settings["device"]["pi_id"],
            set_4sd=set_4sd,
            add_4sd=add_4sd,
            blink_4sd=blink_4sd,
            stop_blink_4sd=stop_blink_4sd,
            rgb_on=rgb_on,
            rgb_off=rgb_off,
            rgb_set_color=rgb_set_color,
            on_dms_pin=handle_remote_pin,
            on_arm_system=handle_arm_system
        )
        threads.append(act_t)

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
                        st["timer"] = None

            run_ds1(settings["DS1"], threads, stop_event, on_value=ds1_handler)

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
                        st["triggered"] = False
                        st["timer"] = _start_ds_hold_timer("DS2", stop_event, push_alarm_event)

                    elif not pressed and st["pressed"]:
                        st["pressed"] = False
                        if st["timer"]:
                            st["timer"].cancel()
                        st["timer"] = None

            run_ds2(settings["DS2"], threads, stop_event, on_value=ds2_handler)

        if "DMS" in settings:
            def dms_handler(v):
                push(make_record(settings, "DMS", v))

                if v.get("value") == 1:
                    print("[DMS] Press detected - use web PIN control")

            run_dms(settings["DMS"], threads, stop_event, on_value=dms_handler)
           
        if "GSG" in settings:
            def gsg_handler(v):
                push(make_record(settings, "GSG", v))
                mag = float(v.get("magnitude", v.get("value", 0)))
                if mag >= 0.7:
                    alarm_on(settings, system_state, buzzer_on, "GSG")

            run_gsg(settings["GSG"], threads, stop_event, on_value=gsg_handler)

        if "DPIR1" in settings:
            def dpir1_handler(v):
                push(make_record(settings, "DPIR1", v))

                if v.get("value") == 1:
                    start_ts = time.time()
                    print(f"[DPIR1->DL] ON at {start_ts:.3f}")
                    light_on()

                    def delayed_off():
                        end_ts = time.time()
                        print(f"[DPIR1->DL] OFF at {end_ts:.3f} (delta={end_ts - start_ts:.2f}s)")
                        light_off()

                    t = threading.Timer(10, delayed_off)
                    t.daemon = True
                    t.start()

                    handle_people_count("DUS1", system_state, settings)

                    if alarm_logic_enabled and system_state.get_people_count() == 0:
                        if time.time() - last_disarm_time < DISARM_COOLDOWN:
                            print("[ALARM BLOCKED] cooldown active")
                            return
                        alarm_on(settings, system_state, buzzer_on, "EMPTY_ROOM_DUS1")

            run_dpir1(settings["DPIR1"], threads, stop_event, on_value=dpir1_handler)

        if "DPIR2" in settings:
            def dpir2_handler(v):
                push(make_record(settings, "DPIR2", v))

                if v.get("value") == 1:
                    handle_people_count("DUS2", system_state, settings)

                    if alarm_logic_enabled and system_state.get_people_count() == 0:
                        alarm_on(settings, system_state, buzzer_on, "EMPTY_ROOM_DUS2")

            run_dpir2(settings["DPIR2"], threads, stop_event, on_value=dpir2_handler)

        if "DPIR3" in settings:
            def dpir3_handler(v):
                push(make_record(settings, "DPIR3", v))

                if v.get("value") == 1:
                    print("[LOGIC] DPIR3 motion detected")

                    if alarm_logic_enabled and system_state.get_people_count() == 0:
                        alarm_on(settings, system_state, buzzer_on, "EMPTY_ROOM_DPIR3")

            run_dpir3(settings["DPIR3"], threads, stop_event, on_value=dpir3_handler)

        if "DUS1" in settings:
            def dus1_handler(v):
                push(make_record(settings, "DUS1", v))
                with dus_lock:
                    last_dus_distance["DUS1"] = float(v.get("distance_cm", v.get("value", 0)))

            run_dus1(settings["DUS1"], threads, stop_event, on_value=dus1_handler)

        if "DUS2" in settings:
            def dus2_handler(v):
                push(make_record(settings, "DUS2", v))
                with dus_lock:
                    last_dus_distance["DUS2"] = float(v.get("distance_cm", v.get("value", 0)))

            run_dus2(settings["DUS2"], threads, stop_event, on_value=dus2_handler)

        if "DHT1" in settings:
            def dht1_handler(v):
                push(make_record(settings, "DHT1", v))
                with dht_lock:
                    last_dht_values["DHT1"] = {
                        "temperature": float(v.get("temperature", v.get("value", 0.0))),
                        "humidity": float(v.get("humidity", 0.0))
                    }

            run_dht1(settings["DHT1"], threads, stop_event, on_value=dht1_handler)

        if "DHT2" in settings:
            def dht2_handler(v):
                push(make_record(settings, "DHT2", v))
                with dht_lock:
                    last_dht_values["DHT2"] = {
                        "temperature": float(v.get("temperature", v.get("value", 0.0))),
                        "humidity": float(v.get("humidity", 0.0))
                    }

            run_dht2(settings["DHT2"], threads, stop_event, on_value=dht2_handler)

        if "DHT3" in settings:
            def dht3_handler(v):
                push(make_record(settings, "DHT3", v))
                with dht_lock:
                    last_dht_values["DHT3"] = {
                        "temperature": float(v.get("temperature", v.get("value", 0.0))),
                        "humidity": float(v.get("humidity", 0.0))
                    }

            run_dht3(settings["DHT3"], threads, stop_event, on_value=dht3_handler)

        if "BTN" in settings:
            def btn_handler(v):
                push(make_record(settings, "BTN", v))

                if v.get("value") == 1 and add_4sd is not None:
                    if is_4sd_blinking is not None and is_4sd_blinking():
                        stop_blink_4sd()
                        print("[BTN] Blink stopped")
                    else:
                        add_4sd(timer_add_seconds)
                        print(f"[BTN] Added {timer_add_seconds} seconds")

            run_btn(settings["BTN"], threads, stop_event, on_value=btn_handler)

        if "IR" in settings:
            def ir_handler(v):
                push(make_record(settings, "IR", v))

                command = str(v.get("command", v.get("value", ""))).upper()

                if command == "ON":
                    rgb_on()
                    push_brgb_state(settings, rgb_get_state)
                    return

                if command == "OFF":
                    rgb_off()
                    push_brgb_state(settings, rgb_get_state)
                    return

                color_map = {
                    "RED": "RED",
                    "GREEN": "GREEN",
                    "BLUE": "BLUE",
                    "WHITE": "WHITE",
                    "YELLOW": "YELLOW",
                    "PURPLE": "PURPLE"
                }

                if command in color_map:
                    rgb_set_color(color_map[command])
                    push_brgb_state(settings, rgb_get_state)
                    return

            run_ir(settings["IR"], threads, stop_event, on_value=ir_handler)

        if "DL" in settings or "DB" in settings:
            actuator_menu(light_on, light_off, buzzer_on, buzzer_off)
        else:
            stop_event.wait()

    except KeyboardInterrupt:
        print("Stopping...")

    finally:
        stop_event.set()

        for t in threads:
            t.join(timeout=3)

        pub.close()

        if GPIO is not None:
            try:
                GPIO.cleanup()
            except Exception:
                pass