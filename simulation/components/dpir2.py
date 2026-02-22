from simulators.dpir2 import run_dpir2_simulator
import threading
import time

def dpir2_callback(motion, code, on_value=None):
    t = time.localtime()
    print("=" * 20)
    print(f"Timestamp: {time.strftime('%H:%M:%S', t)}")
    print("Sensor: DPIR2 (Motion)")
    print(f"Code: {code}")
    print(f"Motion: {motion}")

    if on_value is not None:
        value = 1 if motion else 0
        on_value({"value": value, "code": code, "motion": bool(motion)})

def run_dpir2(settings, threads, stop_event, on_value=None):
    delay = 2
    if settings["simulated"]:
        print("Starting DPIR2 simulator")
        th = threading.Thread(
            target=run_dpir2_simulator,
            args=(delay, lambda motion, code: dpir2_callback(motion, code, on_value), stop_event)
        )
        th.start()
        threads.append(th)
        print("DPIR2 simulator started")
    else:
        from sensors.dpir2 import run_dpir2_loop, DPIR2
        print("Starting DPIR2 loop")
        sensor = DPIR2(settings["pin"])
        th = threading.Thread(
            target=run_dpir2_loop,
            args=(sensor, delay, lambda motion, code: dpir2_callback(motion, code, on_value), stop_event)
        )
        th.start()
        threads.append(th)
        print("DPIR2 loop started")