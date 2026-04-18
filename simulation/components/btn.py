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
    delay = settings.get("poll_delay", 0.02)  # only used for loop sleep in real mode

    if settings.get("simulated", True):
        print("Starting BTN simulator")
        th = threading.Thread(
            target=run_btn_simulator,
            args=(settings.get("sim_poll_delay", 2), lambda pressed, code: btn_callback(pressed, code, on_value), stop_event),
            daemon=True,
        )
        th.start()
        threads.append(th)
        print("BTN simulator started")
        return

    # -------- REAL BUTTON IMPLEMENTATION (Raspberry Pi GPIO) --------
    try:
        import RPi.GPIO as GPIO  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "Real BTN requires RPi.GPIO (run on Raspberry Pi). "
            f"Import error: {e}"
        )

    pin = settings.get("pin")
    if pin is None:
        raise ValueError("BTN real mode requires settings['pin'] to be set (BCM GPIO number).")

    pull = str(settings.get("pull", "UP")).upper()  # UP or DOWN
    debounce_ms = int(settings.get("debounce_ms", 80))
    active_level = int(settings.get("active_level", 0))  # for pull-up wiring, pressed => 0

    def run_btn_loop():
        # Setup GPIO (assumes main.py already did GPIO.setmode(GPIO.BCM))
        pud = GPIO.PUD_UP if pull == "UP" else GPIO.PUD_DOWN
        GPIO.setup(pin, GPIO.IN, pull_up_down=pud)

        print(
            f"Starting real BTN on BCM GPIO {pin} "
            f"(pull={pull}, active_level={active_level}, debounce_ms={debounce_ms})"
        )

        last_state = GPIO.input(pin)
        last_change = time.monotonic()

        # Emit initial state (optional; comment out if you don't want it)
        btn_callback(last_state == active_level, "REAL", on_value)

        while not stop_event.is_set():
            state = GPIO.input(pin)
            now = time.monotonic()

            if state != last_state:
                # state changed; start debounce timer
                last_change = now
                last_state = state

            # If stable for debounce_ms, consider it a valid new state and emit
            # We need to re-read and ensure stable:
            if (now - last_change) * 1000.0 >= debounce_ms:
                stable_state = GPIO.input(pin)
                pressed = (stable_state == active_level)

                # To avoid spamming, only emit when stable state differs from what we last emitted.
                # Track emitted state separately:
                # We'll store it in a local variable using function attribute.
                if not hasattr(run_btn_loop, "_emitted"):
                    run_btn_loop._emitted = stable_state  # type: ignore

                if stable_state != run_btn_loop._emitted:  # type: ignore
                    run_btn_loop._emitted = stable_state  # type: ignore
                    btn_callback(pressed, "REAL", on_value)

            time.sleep(delay)

        print("BTN real sensor stopped")

    th = threading.Thread(target=run_btn_loop, daemon=True)
    th.start()
    threads.append(th)
    print("BTN real sensor thread started")