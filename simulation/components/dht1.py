from simulators.dht1 import run_dht1_simulator
import threading
import time

try:
    import board  # type: ignore
    import adafruit_dht  # type: ignore
except Exception:
    board = None
    adafruit_dht = None


def dht1_callback(temp, hum, code, on_value=None):
    t = time.localtime()
    print("=" * 20)
    print(f"Timestamp: {time.strftime('%H:%M:%S', t)}")
    print("Sensor: DHT1 (Bedroom Temperature/Humidity)")
    print(f"Code: {code}")
    print(f"Temperature: {temp:.2f} C")
    print(f"Humidity: {hum:.2f} %")

    if on_value is not None:
        on_value({
            "value": float(temp),
            "temperature": float(temp),
            "humidity": float(hum),
            "code": code
        })


def _resolve_board_pin(pin_name: str):
    if board is None:
        return None
    return getattr(board, pin_name, None)


def _run_dht1_real_loop(delay, callback, stop_event, pin_name: str, sensor_type: str):
    if adafruit_dht is None or board is None:
        raise RuntimeError(
            "Real DHT1 requires 'adafruit-circuitpython-dht' and 'board' to be installed "
            "and run on compatible hardware."
        )

    pin = _resolve_board_pin(pin_name)
    if pin is None:
        raise ValueError(f"Invalid board pin '{pin_name}'. Example values: D4, D17, D22, etc.")

    sensor_type_upper = str(sensor_type).upper()
    if sensor_type_upper in ("DHT11",):
        dht_device = adafruit_dht.DHT11(pin)
    elif sensor_type_upper in ("DHT22", "AM2302", "DHT21"):
        dht_device = adafruit_dht.DHT22(pin)
    else:
        raise ValueError("Unsupported DHT type. Use 'DHT11' or 'DHT22'/'AM2302'.")

    try:
        while True:
            try:
                temp = dht_device.temperature
                hum = dht_device.humidity

                if temp is not None and hum is not None:
                    callback(float(temp), float(hum), "REAL")
            except Exception:
                # DHT sensors frequently throw intermittent read errors; ignore and retry.
                pass

            if stop_event.is_set():
                break

            time.sleep(delay)
    finally:
        try:
            dht_device.exit()
        except Exception:
            pass


def run_dht1(settings, threads, stop_event, on_value=None):
    delay = 3

    if settings["simulated"]:
        print("Starting DHT1 simulator")
        th = threading.Thread(
            target=run_dht1_simulator,
            args=(delay, lambda t, h, code: dht1_callback(t, h, code, on_value), stop_event)
        )
        th.start()
        threads.append(th)
        print("DHT1 simulator started")
    else:
        pin_name = settings.get("pin", "D4")
        sensor_type = settings.get("type", "DHT22")

        print(f"Starting real DHT1 (type={sensor_type}, pin={pin_name})")
        th = threading.Thread(
            target=_run_dht1_real_loop,
            args=(delay, lambda t, h, code: dht1_callback(t, h, code, on_value), stop_event, pin_name, sensor_type)
        )
        th.start()
        threads.append(th)
        print("Real DHT1 started")