import threading
from settings import load_settings

from components.ds1 import run_ds1
from components.dpir1 import run_dpir1
from components.dms import run_dms
from components.dus1 import run_dus1

from components.door_light import create_door_light
from components.buzzer import create_buzzer
from actuator_menu import actuator_menu

try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
except:
    GPIO = None


if __name__ == "__main__":
    print("Starting PI1 app (KT1)")
    settings = load_settings()

    threads = []
    stop_event = threading.Event()

    try:
        run_ds1(settings["DS1"], threads, stop_event)
        run_dpir1(settings["DPIR1"], threads, stop_event)
        run_dms(settings["DMS"], threads, stop_event)
        run_dus1(settings["DUS1"], threads, stop_event)

        #actuator handlers
        light_on, light_off = create_door_light(settings["DL"])
        buzzer_on, buzzer_off = create_buzzer(settings["DB"])

        actuator_menu(light_on, light_off, buzzer_on, buzzer_off)

    except KeyboardInterrupt:
        print("\nStopping app (KeyboardInterrupt)")

    finally:
        stop_event.set()
        for t in threads:
            t.join(timeout=3)

        if GPIO is not None:
            try:
                GPIO.cleanup()
            except:
                pass

        print("App stopped.")
