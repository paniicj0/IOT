from simulators.ds1 import run_ds1_simulator
import threading
import time

def ds1_callback(pressed, code):
    t = time.localtime()
    print("=" * 20)
    print(f"Timestamp: {time.strftime('%H:%M:%S', t)}")
    print("Sensor: DS1 (Door Button)")
    print(f"Code: {code}")
    print(f"Pressed: {pressed}")

def run_ds1(settings, threads, stop_event):
    delay = 2
    if settings["simulated"]:
        print("Starting DS1 simulator")
        th = threading.Thread(target=run_ds1_simulator, args=(delay, ds1_callback, stop_event))
        th.start()
        threads.append(th)
        print("DS1 simulator started")
    else:
        from sensors.ds1 import run_ds1_loop, DS1Button
        print("Starting DS1 loop")
        sensor = DS1Button(settings["pin"], settings.get("pull", "UP"))
        th = threading.Thread(target=run_ds1_loop, args=(sensor, delay, ds1_callback, stop_event))
        th.start()
        threads.append(th)
        print("DS1 loop started")
