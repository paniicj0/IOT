import time
import random

def run_gsg_simulator(delay, callback, stop_event):
    while True:
        # "magnitude" pomeraja (0-1), povremeno veliki skok
        magnitude = random.uniform(0.0, 0.4)
        if random.random() < 0.15:
            magnitude = random.uniform(0.7, 1.0)  # značajan pomeraj

        callback(magnitude, "SIMULATED")

        if stop_event.is_set():
            break
        time.sleep(delay)