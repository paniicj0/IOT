import time
import random

def run_btn_simulator(delay, callback, stop_event):
    while True:
        # simuliraj "klik" povremeno (ređe nego true/false stalno)
        pressed = (random.random() < 0.25)  # ~25% šanse na tick
        callback(pressed, "SIMULATED")

        if stop_event.is_set():
            break
        time.sleep(delay)