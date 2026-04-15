from simulators.dpir1 import run_dpir1_simulator
import threading
import time

def dpir1_callback(motion, code, on_value=None):
    t = time.localtime()
    print("=" * 20)
    print(f"Timestamp: {time.strftime('%H:%M:%S', t)}")
    print("Sensor: DPIR1 (Motion)")
    print(f"Code: {code}")
    print(f"Motion: {motion}")

    # KT2: push u telemetry buffer (ako je prosleđeno)
    if on_value is not None:
        value = 1 if motion else 0
        on_value({"value": value, "code": code, "motion": bool(motion)})

def run_dpir1(settings, threads, stop_event, on_value=None):
    delay = 2
    if settings["simulated"]:
        print("Starting DPIR1 simulator")
        th = threading.Thread(
            target=run_dpir1_simulator,
            args=(delay, lambda motion, code: dpir1_callback(motion, code, on_value), stop_event)
        )
        th.start()
        threads.append(th)
        print("DPIR1 simulator started")
    else:
        from sensors.dpir1 import run_dpir1_loop, DPIR1
        print("Starting DPIR1 loop")
        sensor = DPIR1(settings["pin"])
        th = threading.Thread(
            target=run_dpir1_loop,
            args=(sensor, delay, lambda motion, code: dpir1_callback(motion, code, on_value), stop_event)
        )
        th.start()
        threads.append(th)
        print("DPIR1 loop started")
