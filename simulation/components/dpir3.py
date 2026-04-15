from simulators.dpir3 import run_dpir3_simulator
import threading
import time


def dpir3_callback(motion, code, on_value=None):
    t = time.localtime()
    print("=" * 20)
    print(f"Timestamp: {time.strftime('%H:%M:%S', t)}")
    print("Sensor: DPIR3 (Living room Motion)")
    print(f"Code: {code}")
    print(f"Motion: {motion}")

    if on_value is not None:
        value = 1 if motion else 0
        on_value({
            "value": value,
            "code": code,
            "motion": bool(motion)
        })


def run_dpir3(settings, threads, stop_event, on_value=None):
    delay = 2

    if settings["simulated"]:
        print("Starting DPIR3 simulator")
        th = threading.Thread(
            target=run_dpir3_simulator,
            args=(delay, lambda motion, code: dpir3_callback(motion, code, on_value), stop_event)
        )
        th.start()
        threads.append(th)
        print("DPIR3 simulator started")
    else:
        from sensors.dpir3 import run_dpir3_loop, DPIR3
        print("Starting DPIR3 loop")
        sensor = DPIR3(settings["pin"])
        th = threading.Thread(
            target=run_dpir3_loop,
            args=(sensor, delay, lambda motion, code: dpir3_callback(motion, code, on_value), stop_event)
        )
        th.start()
        threads.append(th)
        print("DPIR3 loop started")