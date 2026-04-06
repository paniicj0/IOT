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
    delay = 3

    if settings["simulated"]:
        print("Starting DHT2 simulator")
        th = threading.Thread(
            target=run_dht2_simulator,
            args=(delay, lambda t, h, code: dht2_callback(t, h, code, on_value), stop_event)
        )
        th.start()
        threads.append(th)
        print("DHT2 simulator started")
    else:
        print("Real DHT2 not implemented yet")