import time

try:
    # Optional: only available on Raspberry Pi / systems with RPi.GPIO installed
    import RPi.GPIO as GPIO  # type: ignore
except Exception:
    GPIO = None


class DUS1:
    """
    Ultrasonic distance sensor (e.g., HC-SR04) using trigger/echo GPIO pins.

    Notes:
    - Requires RPi.GPIO (or compatible) and real hardware wiring.
    - Uses a simple pulse timing method and converts to centimeters.
    """

    SPEED_OF_SOUND_CM_PER_S = 34300.0  # 343 m/s = 34300 cm/s

    def __init__(
        self,
        trigger_pin: int,
        echo_pin: int,
        gpio_mode=None,
        gpio_module=None,
        settle_time: float = 0.05,
    ):
        """
        trigger_pin: GPIO pin number for TRIG
        echo_pin: GPIO pin number for ECHO
        gpio_mode: GPIO.BCM or GPIO.BOARD (defaults to GPIO.BCM if available)
        gpio_module: allow injecting a GPIO-like module for testing
        settle_time: time to let sensor settle after setup
        """
        self.trigger_pin = trigger_pin
        self.echo_pin = echo_pin
        self.GPIO = gpio_module if gpio_module is not None else GPIO

        if self.GPIO is None:
            raise RuntimeError(
                "RPi.GPIO is not available. Install it and run on compatible hardware, "
                "or pass a gpio_module implementing the RPi.GPIO interface."
            )

        if gpio_mode is None:
            gpio_mode = self.GPIO.BCM

        self.GPIO.setmode(gpio_mode)
        self.GPIO.setup(self.trigger_pin, self.GPIO.OUT)
        self.GPIO.setup(self.echo_pin, self.GPIO.IN)

        # Ensure trigger is low initially
        self.GPIO.output(self.trigger_pin, False)
        time.sleep(settle_time)

    def read_distance_cm(
        self,
        timeout_s: float = 0.03,
        samples: int = 3,
        inter_sample_delay_s: float = 0.01,
    ) -> float:
        """
        Returns distance in centimeters.

        timeout_s: max time to wait for echo transitions (prevents hanging)
        samples: take N readings and return the median-like filtered value (min of sorted middle)
        """
        readings = []
        for _ in range(max(1, samples)):
            d = self._read_once_cm(timeout_s=timeout_s)
            if d is not None:
                readings.append(d)
            time.sleep(inter_sample_delay_s)

        if not readings:
            return 0.0

        readings.sort()
        return readings[len(readings) // 2]

    def _read_once_cm(self, timeout_s: float) -> float | None:
        # Send a 10µs trigger pulse
        self.GPIO.output(self.trigger_pin, True)
        time.sleep(0.00001)
        self.GPIO.output(self.trigger_pin, False)

        # Wait for echo to go HIGH (start)
        start_wait = time.time()
        while self.GPIO.input(self.echo_pin) == 0:
            if (time.time() - start_wait) > timeout_s:
                return None

        pulse_start = time.time()

        # Wait for echo to go LOW (end)
        end_wait = time.time()
        while self.GPIO.input(self.echo_pin) == 1:
            if (time.time() - end_wait) > timeout_s:
                return None

        pulse_end = time.time()
        pulse_duration = pulse_end - pulse_start  # seconds

        # Distance = (time * speed_of_sound) / 2
        distance_cm = (pulse_duration * self.SPEED_OF_SOUND_CM_PER_S) / 2.0
        return float(distance_cm)

    def cleanup(self):
        """Optional cleanup method."""
        try:
            self.GPIO.cleanup()
        except Exception:
            pass


def run_dus1_loop(sensor: DUS1, delay: float, callback, stop_event):
    
    
    source = f"GPIO(trig={sensor.trigger_pin},echo={sensor.echo_pin})"
    while True:
        dist = sensor.read_distance_cm()
        callback(dist, source)

        if stop_event.is_set():
            break

        time.sleep(delay)
