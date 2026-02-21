from simulators.dus2 import run_dus2_simulator
import threading
import time

def dus2_callback(distance_cm, code, on_value=None):
    t = time.localtime()
    print("=" * 20)
    print(f"Timestamp: {time.strftime('%H:%M:%S', t)}")
    print("Sensor: DUS2 (Ultrasonic)")
    print(f"Code: {code}")
    print(f"Distance: {distance_cm:.2f} cm")

    if on_value is not None:
        on_value({
            "value": float(distance_cm),
            "code": code,
            "distance_cm": float(distance_cm)
        })

def run_dus2(settings, threads, stop_event, on_value=None):
    delay = 2
    if settings["simulated"]:
        print("Starting DUS2 simulator")
        th = threading.Thread(
            target=run_dus2_simulator,
            args=(delay, lambda distance, code: dus2_callback(distance, code, on_value), stop_event)
        )
        th.start()
        threads.append(th)
        print("DUS2 simulator started")
    else:
        from sensors.dus2 import run_dus2_loop, DUS2
        print("Starting DUS2 loop")
        sensor = DUS2(settings["trigger_pin"], settings["echo_pin"])
        th = threading.Thread(
            target=run_dus2_loop,
            args=(sensor, delay, lambda distance, code: dus2_callback(distance, code, on_value), stop_event)
        )
        th.start()
        threads.append(th)
        print("DUS2 loop started")