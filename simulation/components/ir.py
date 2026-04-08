from simulators.ir import run_ir_simulator
import threading
import time


def ir_callback(command, code, on_value=None):
    t = time.localtime()
    print("=" * 20)
    print(f"Timestamp: {time.strftime('%H:%M:%S', t)}")
    print("Sensor: IR (Bedroom Infrared)")
    print(f"Code: {code}")
    print(f"Command: {command}")

    if on_value is not None:
        on_value({
            "value": str(command),
            "command": str(command),
            "code": code
        })


def run_ir(settings, threads, stop_event, on_value=None):
    delay = 3

    if settings["simulated"]:
        print("Starting IR simulator")
        th = threading.Thread(
            target=run_ir_simulator,
            args=(delay, lambda command, code: ir_callback(command, code, on_value), stop_event)
        )
        th.start()
        threads.append(th)
        print("IR simulator started")
    else:
        print("Real IR not implemented yet")