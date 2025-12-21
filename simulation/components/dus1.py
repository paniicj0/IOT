from simulators.dus1 import run_dus1_simulator
import threading
import time

def dus1_callback(distance_cm, code):
    t = time.localtime()
    print("=" * 20)
    print(f"Timestamp: {time.strftime('%H:%M:%S', t)}")
    print("Sensor: DUS1 (Ultrasonic)")
    print(f"Code: {code}")
    print(f"Distance: {distance_cm:.2f} cm")

def run_dus1(settings, threads, stop_event):
    delay = 2
    if settings["simulated"]:
        print("Starting DUS1 simulator")
        th = threading.Thread(target=run_dus1_simulator, args=(delay, dus1_callback, stop_event))
        th.start()
        threads.append(th)
        print("DUS1 simulator started")
    else:
        from sensors.dus1 import run_dus1_loop, DUS1
        print("Starting DUS1 loop")
        sensor = DUS1(settings["trigger_pin"], settings["echo_pin"])
        th = threading.Thread(target=run_dus1_loop, args=(sensor, delay, dus1_callback, stop_event))
        th.start()
        threads.append(th)
        print("DUS1 loop started")
