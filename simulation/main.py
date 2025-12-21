import threading
from settings import load_settings
import time

from components.ds1 import run_ds1
from components.dpir1 import run_dpir1
from components.dms import run_dms
from components.dus1 import run_dus1

try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
except:
    pass

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

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("Stopping app")
        stop_event.set()
        for t in threads:
            t.join(timeout=2)
