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
    delay = 3

    if settings["simulated"]:
        print("Starting DHT3 simulator")
        th = threading.Thread(
            target=run_dht3_simulator,
            args=(delay, lambda t, h, code: dht3_callback(t, h, code, on_value), stop_event)
        )
        th.start()
        threads.append(th)
        print("DHT3 simulator started")

    else:
        # Skeleton za realni DHT 
        print("Real DHT3 not implemented yet")