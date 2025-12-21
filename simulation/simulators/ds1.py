import time
import random

def run_ds1_simulator(delay, callback, stop_event):
    while True:
        pressed = random.choice([True, False])
        callback(pressed, "SIMULATED")
        if stop_event.is_set():
            break
        time.sleep(delay)
