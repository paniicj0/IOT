import time
import RPi.GPIO as GPIO

class DPIR1:
    def __init__(self, pin):
        self.pin = pin
        GPIO.setup(self.pin, GPIO.IN)

    def read(self):
        return bool(GPIO.input(self.pin))

def run_dpir1_loop(sensor, delay, callback, stop_event):
    while True:
        motion = sensor.read()
        callback(motion, "GPIO")
        if stop_event.is_set():
            break
        time.sleep(delay)
