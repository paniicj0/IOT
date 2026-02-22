import time
import random

def run_dus2_simulator(delay, callback, stop_event):
    while True:
        distance = random.uniform(5.0, 120.0)
        callback(distance, "SIMULATED")
        if stop_event.is_set():
            break
        time.sleep(delay)