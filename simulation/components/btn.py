from simulators.btn import run_btn_simulator
import threading
import time

def btn_callback(pressed, code, on_value=None):
    t = time.localtime()
    print("=" * 20)
    print(f"Timestamp: {time.strftime('%H:%M:%S', t)}")
    print("Sensor: BTN (Kitchen Button)")
    print(f"Code: {code}")
    print(f"Pressed: {pressed}")

    if on_value is not None:
        value = 1 if pressed else 0
        on_value({"value": value, "code": code, "pressed": bool(pressed)})

def run_btn(settings, threads, stop_event, on_value=None):
    delay = 2
    if settings["simulated"]:
        print("Starting BTN simulator")
        th = threading.Thread(
            target=run_btn_simulator,
            args=(delay, lambda pressed, code: btn_callback(pressed, code, on_value), stop_event)
        )
        th.start()
        threads.append(th)
        print("BTN simulator started")
    else:
        print("Real BTN not implemented yet")