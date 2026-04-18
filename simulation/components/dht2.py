from simulators.dht2 import run_dht2_simulator
import threading
import time


def dht2_callback(temp, hum, code, on_value=None):
    t = time.localtime()
    print("=" * 20)
    print(f"Timestamp: {time.strftime('%H:%M:%S', t)}")
    print("Sensor: DHT2 (Master Bedroom Temperature/Humidity)")
    print(f"Code: {code}")
    print(f"Temperature: {temp:.2f} C")
    print(f"Humidity: {hum:.2f} %")

    if on_value is not None:
        on_value({
            "value": float(temp),
            "temperature": float(temp),
            "humidity": float(hum),
            "code": code
        })


def run_dht2(settings, threads, stop_event, on_value=None):
    # Allow overriding from settings, but keep old default behavior
    delay = settings.get("poll_delay", 3)

    if settings.get("simulated", True):
        print("Starting DHT2 simulator")
        th = threading.Thread(
            target=run_dht2_simulator,
            args=(delay, lambda t, h, code: dht2_callback(t, h, code, on_value), stop_event),
            daemon=True,
        )
        th.start()
        threads.append(th)
        print("DHT2 simulator started")
        return

    # REAL SENSOR IMPLEMENTATION (uses simulation/sensors/dht.py)
    from sensors.dht import DHT, parseCheckCode

    pin = settings.get("pin")
    if pin is None:
        raise ValueError("DHT2 real mode requires settings['pin'] to be set (GPIO pin number).")

    def run_dht2_loop():
        print(f"Starting real DHT2 sensor on GPIO pin {pin} (delay={delay}s)")
        dht = DHT(pin)

        while not stop_event.is_set():
            check = dht.readDHT11()
            code = parseCheckCode(check)

            # Driver updates these on readDHT11()
            hum = float(dht.humidity)
            temp = float(dht.temperature)

            # Skip invalid readings (driver uses -999 for invalid)
            if hum == -999 or temp == -999:
                time.sleep(delay)
                continue

            dht2_callback(temp, hum, code, on_value)
            time.sleep(delay)

        print("DHT2 real sensor stopped")

    th = threading.Thread(target=run_dht2_loop, daemon=True)
    th.start()
    threads.append(th)
    print("DHT2 real sensor thread started")