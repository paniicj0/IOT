import time
import random


def run_dht2_simulator(delay, callback, stop_event):
    while True:
        temp = random.uniform(18.0, 28.0)
        hum = random.uniform(35.0, 65.0)

        callback(temp, hum, "SIMULATED")

        if stop_event.is_set():
            break

        time.sleep(delay)