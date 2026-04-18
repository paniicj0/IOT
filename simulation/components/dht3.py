from simulators.dht3 import run_dht3_simulator
import threading
import time


def dht3_callback(temp, hum, code, on_value=None):
    t = time.localtime()
    print("=" * 20)
    print(f"Timestamp: {time.strftime('%H:%M:%S', t)}")
    print("Sensor: DHT3 (Temperature/Humidity)")
    print(f"Code: {code}")
    print(f"Temperature: {temp:.2f} C")
    print(f"Humidity: {hum:.2f} %")

    if on_value is not None:
        on_value({
            "value": float(temp),   # glavna vrednost za grafanu
            "temperature": float(temp),
            "humidity": float(hum),
            "code": code
        })


def run_dht3(settings, threads, stop_event, on_value=None):
    delay = settings.get("poll_delay", 3)

    if settings.get("simulated", True):
        print("Starting DHT3 simulator")
        th = threading.Thread(
            target=run_dht3_simulator,
            args=(delay, lambda t, h, code: dht3_callback(t, h, code, on_value), stop_event),
            daemon=True,
        )
        th.start()
        threads.append(th)
        print("DHT3 simulator started")
        return

    # REAL SENSOR IMPLEMENTATION
    try:
        from sensors.dht import DHT, parseCheckCode
    except Exception:
        from simulation.sensors.dht import DHT, parseCheckCode

    pin = settings.get("pin")
    if pin is None:
        raise ValueError("DHT3 real mode requires settings['pin'] to be set (GPIO pin number).")

    def run_dht3_loop():
        print(f"Starting real DHT3 sensor on GPIO pin {pin} (delay={delay}s)")
        dht = DHT(pin)

        while not stop_event.is_set():
            check = dht.readDHT11()
            code = parseCheckCode(check)

            hum = float(dht.humidity)
            temp = float(dht.temperature)

            # Skip invalid readings (driver uses -999 for invalid)
            if hum == -999 or temp == -999:
                time.sleep(delay)
                continue

            dht3_callback(temp, hum, code, on_value)
            time.sleep(delay)

        print("DHT3 real sensor stopped")

    th = threading.Thread(target=run_dht3_loop, daemon=True)
    th.start()
    threads.append(th)
    print("DHT3 real sensor thread started")