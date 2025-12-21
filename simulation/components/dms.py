from simulators.dms import run_dms_simulator
import threading
import time

def dms_callback(pressed, code):
    t = time.localtime()
    print("=" * 20)
    print(f"Timestamp: {time.strftime('%H:%M:%S', t)}")
    print("Sensor: DMS (Membrane Switch)")
    print(f"Code: {code}")
    print(f"Pressed: {pressed}")

def run_dms(settings, threads, stop_event):
    delay = 2
    if settings["simulated"]:
        print("Starting DMS simulator")
        th = threading.Thread(target=run_dms_simulator, args=(delay, dms_callback, stop_event))
        th.start()
        threads.append(th)
        print("DMS simulator started")
    else:
        from sensors.dms import run_dms_loop, DMS
        print("Starting DMS loop")
        sensor = DMS(settings["pin"], settings.get("pull", "UP"))
        th = threading.Thread(target=run_dms_loop, args=(sensor, delay, dms_callback, stop_event))
        th.start()
        threads.append(th)
        print("DMS loop started")
