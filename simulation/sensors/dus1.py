import time

class DUS1:
    def __init__(self, trigger_pin, echo_pin):
        self.trigger_pin = trigger_pin
        self.echo_pin = echo_pin

    def read_distance_cm(self):
        # TODO: implement real ultrasonic measurement if you have hardware
        return 0.0

def run_dus1_loop(sensor, delay, callback, stop_event):
    while True:
        dist = sensor.read_distance_cm()
        callback(dist, "GPIO_TODO")
        if stop_event.is_set():
            break
        time.sleep(delay)
