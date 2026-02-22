import time
import random

def run_dht3_simulator(delay, callback, stop_event):
    while True:
        temperature = random.uniform(18.0, 30.0)
        humidity = random.uniform(30.0, 70.0)

        callback(temperature, humidity, "SIMULATED")

        if stop_event.is_set():
            break

        time.sleep(delay)