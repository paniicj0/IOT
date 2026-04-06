import time
import random


def run_dpir3_simulator(delay, callback, stop_event):
    while True:
        motion = random.choice([True, False, False, False])

        callback(motion, "SIMULATED")

        if stop_event.is_set():
            break

        time.sleep(delay)