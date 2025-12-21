import time
import RPi.GPIO as GPIO

class DMS:
    def __init__(self, pin, pull="UP"):
        self.pin = pin
        self.pull = pull
        pud = GPIO.PUD_UP if pull == "UP" else GPIO.PUD_DOWN
        GPIO.setup(self.pin, GPIO.IN, pull_up_down=pud)

    def read(self):
        val = GPIO.input(self.pin)
        return (val == 0) if self.pull == "UP" else (val == 1)

def run_dms_loop(sensor, delay, callback, stop_event):
    while True:
        pressed = sensor.read()
        callback(pressed, "GPIO")
        if stop_event.is_set():
            break
        time.sleep(delay)
