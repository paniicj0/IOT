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
    delay = settings.get("poll_delay", 3)

    if settings.get("simulated", True):
        print("Starting IR simulator")
        th = threading.Thread(
            target=run_ir_simulator,
            args=(delay, lambda command, code: ir_callback(command, code, on_value), stop_event),
            daemon=True,
        )
        th.start()
        threads.append(th)
        print("IR simulator started")
        return

    # -------- REAL IR IMPLEMENTATION (Raspberry Pi) --------
    # Requirements on Pi:
    #   sudo apt-get install pigpio python3-pigpio
    #   sudo systemctl enable --now pigpiod
    #   pip install py-irrecv
    #
    # settings:
    #   pin: BCM GPIO for IR receiver data pin (e.g. 12)
    #   codes: optional mapping from hex strings to commands, e.g.
    #     "codes": {"0xFFA25D": "ON", "0xFFE21D": "OFF"}
    #
    pin = settings.get("pin")
    if pin is None:
        raise ValueError("IR real mode requires settings['pin'] to be set (BCM GPIO number).")

    codes_map = settings.get("codes", {}) or {}

    def _normalize_code_hex(value) -> str:
        """
        Return code as '0x...' uppercase string.
        """
        try:
            if isinstance(value, str):
                s = value.strip()
                if s.lower().startswith("0x"):
                    return "0x" + s[2:].upper()
                # allow raw hex without 0x
                return "0x" + s.upper()
            if isinstance(value, int):
                return hex(value).upper().replace("X", "x")  # keep '0x' prefix
        except Exception:
            pass
        return str(value)

    def _command_from_code(code_hex: str) -> str:
        # codes_map keys might be "0xFFA25D" or "FFA25D" or ints
        if not codes_map:
            return code_hex

        # Try multiple key formats
        candidates = [
            code_hex,
            code_hex.upper(),
            code_hex.lower(),
            code_hex[2:] if code_hex.lower().startswith("0x") else code_hex,
            (code_hex[2:] if code_hex.lower().startswith("0x") else code_hex).upper(),
            (code_hex[2:] if code_hex.lower().startswith("0x") else code_hex).lower(),
        ]

        for k in candidates:
            if k in codes_map:
                return str(codes_map[k])

        # Also try int key if possible
        try:
            as_int = int(code_hex, 16) if code_hex.lower().startswith("0x") else int("0x" + code_hex, 16)
            if as_int in codes_map:
                return str(codes_map[as_int])
        except Exception:
            pass

        return code_hex

    def run_ir_loop():
        print(f"Starting real IR receiver on BCM GPIO {pin}")

        try:
            import pigpio  # type: ignore
        except Exception as e:
            raise RuntimeError(
                "pigpio is required for real IR mode. Install and start pigpiod:\n"
                "  sudo apt-get install pigpio python3-pigpio\n"
                "  sudo systemctl enable --now pigpiod\n"
                f"Import error: {e}"
            )

        try:
            # py-irrecv package API
            from py_irrecv.irrecv import IRRecv  # type: ignore
        except Exception as e:
            raise RuntimeError(
                "py-irrecv is required for real IR mode.\n"
                "Install: pip install py-irrecv\n"
                f"Import error: {e}"
            )

        pi = pigpio.pi()
        if not pi.connected:
            raise RuntimeError("Cannot connect to pigpiod. Is it running? Try: sudo systemctl start pigpiod")

        # py-irrecv gives codes through a callback. We'll push them into a local variable.
        last = {"code": None, "ts": 0.0}

        def on_code(code_int):
            last["code"] = code_int
            last["ts"] = time.time()

        ir = IRRecv(pi, pin, on_code)

        # Optional debounce to avoid repeats
        repeat_window_sec = float(settings.get("repeat_window_sec", 0.30))
        last_sent = {"code": None, "ts": 0.0}

        try:
            while not stop_event.is_set():
                code_int = last["code"]
                if code_int is not None:
                    code_hex = _normalize_code_hex(code_int)

                    now = time.time()
                    if last_sent["code"] != code_hex or (now - last_sent["ts"]) >= repeat_window_sec:
                        command = _command_from_code(code_hex)
                        ir_callback(command, "REAL", on_value)
                        last_sent["code"] = code_hex
                        last_sent["ts"] = now

                    # clear after processing
                    last["code"] = None

                time.sleep(0.01)
        finally:
            try:
                ir.cancel()
            except Exception:
                pass
            try:
                pi.stop()
            except Exception:
                pass

        print("IR real sensor stopped")

    th = threading.Thread(target=run_ir_loop, daemon=True)
    th.start()
    threads.append(th)
    print("IR real sensor thread started")