from simulators.ds2 import run_ds2_simulator
import threading
import time

def ds2_callback(pressed, code, on_value=None):
    t = time.localtime()
    print("=" * 20)
    print(f"Timestamp: {time.strftime('%H:%M:%S', t)}")
    print("Sensor: DS2 (Door Button)")
    print(f"Code: {code}")
    print(f"Pressed: {pressed}")

    if on_value is not None:
        value = 1 if pressed else 0
        on_value({"value": value, "code": code, "pressed": bool(pressed)})

def run_ds2(settings, threads, stop_event, on_value=None):
    delay = 2
    if settings["simulated"]:
        print("Starting DS2 simulator")
        th = threading.Thread(
            target=run_ds2_simulator,
            args=(delay, lambda pressed, code: ds2_callback(pressed, code, on_value), stop_event)
        )
        th.start()
        threads.append(th)
        print("DS2 simulator started")
    else:
        from sensors.ds2 import run_ds2_loop, DS2Button
        print("Starting DS2 loop")
        sensor = DS2Button(settings["pin"], settings.get("pull", "UP"))
        th = threading.Thread(
            target=run_ds2_loop,
            args=(sensor, delay, lambda pressed, code: ds2_callback(pressed, code, on_value), stop_event)
        )
        th.start()
        threads.append(th)
        print("DS2 loop started")