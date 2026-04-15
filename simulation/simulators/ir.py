import time
import random


def run_ir_simulator(delay, callback, stop_event):
    commands = [
        "ON",
        "OFF",
        "RED",
        "GREEN",
        "BLUE",
        "WHITE",
        "YELLOW",
        "PURPLE"
    ]

    while True:
        command = random.choice(commands)
        callback(command, "SIMULATED")

        if stop_event.is_set():
            break

        time.sleep(delay)