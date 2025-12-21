import time
import random

def generate_values(initial_temp=25, initial_humidity=20):
    temperature = initial_temp
    humidity = initial_humidity
    while True:
        temperature = temperature + random.randint(-1, 1)
        humidity = humidity + random.randint(-1, 1)
        humidity = max(0, min(100, humidity))
        yield humidity, temperature

def run_dht_simulator(delay, callback, stop_event):
    for h, t in generate_values():
        time.sleep(delay)
        callback(h, t, "SIMULATED")   # ✅ dodaj code
        if stop_event.is_set():
            break
