from simulators.gsg import run_gsg_simulator
import threading
import time

def gsg_callback(magnitude, code, on_value=None):
    t = time.localtime()
    print("=" * 20)
    print(f"Timestamp: {time.strftime('%H:%M:%S', t)}")
    print("Sensor: GSG (Gyroscope)")
    print(f"Code: {code}")
    print(f"Movement magnitude: {magnitude:.3f}")

    if on_value is not None:
        on_value({
            "value": float(magnitude),
            "code": code,
            "magnitude": float(magnitude)
        })

def run_gsg(settings, threads, stop_event, on_value=None):
    delay = 2
    if settings["simulated"]:
        print("Starting GSG simulator")
        th = threading.Thread(
            target=run_gsg_simulator,
            args=(delay, lambda mag, code: gsg_callback(mag, code, on_value), stop_event)
        )
        th.start()
        threads.append(th)
        print("GSG simulator started")
    else:
        print("Real GSG not implemented yet")