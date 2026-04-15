import threading
import time


def _format_mmss(seconds: int) -> str:
    seconds = max(0, int(seconds))
    mm = seconds // 60
    ss = seconds % 60
    return f"{mm:02d}:{ss:02d}"


def create_4sd(settings):
    state = {
        "seconds": 0,
        "blink": False,
        "blink_on": True,
        "running": False,
        "last_tick": time.time()
    }
    lock = threading.Lock()

    def set_time(seconds: int):
        with lock:
            state["seconds"] = max(0, int(seconds))
            state["blink"] = False
            state["blink_on"] = True
            state["running"] = state["seconds"] > 0
            state["last_tick"] = time.time()
        print(f"[4SD] set to {_format_mmss(seconds)}")

    def add_seconds(n: int):
        with lock:
            state["seconds"] = max(0, state["seconds"] + int(n))
            state["blink"] = False
            state["blink_on"] = True
            if state["seconds"] > 0:
                state["running"] = True
            state["last_tick"] = time.time()
            current = state["seconds"]
        print(f"[4SD] +{int(n)} => {_format_mmss(current)}")

    def start_blink():
        with lock:
            state["seconds"] = 0
            state["running"] = False
            state["blink"] = True
            state["blink_on"] = True
        print("[4SD] BLINK 00:00")

    def stop_blink():
        with lock:
            state["blink"] = False
            state["blink_on"] = True
            state["running"] = False
        print("[4SD] BLINK STOP")

    def is_blinking():
        with lock:
            return bool(state["blink"])

    def get_seconds():
        with lock:
            return int(state["seconds"])

    def run_render_loop(stop_event):
        last_render = None

        while not stop_event.is_set():
            with lock:
                now = time.time()

                if state["running"] and not state["blink"] and state["seconds"] > 0:
                    elapsed = now - state["last_tick"]
                    if elapsed >= 1.0:
                        ticks = int(elapsed)
                        state["seconds"] = max(0, state["seconds"] - ticks)
                        state["last_tick"] += ticks

                        if state["seconds"] == 0:
                            state["running"] = False
                            state["blink"] = True
                            state["blink_on"] = True
                            print("[4SD] TIMER FINISHED -> BLINK")

                if state["blink"]:
                    out = "00:00" if state["blink_on"] else "     "
                    state["blink_on"] = not state["blink_on"]
                else:
                    out = _format_mmss(state["seconds"])

            if out != last_render:
                print(f"[4SD] {out}")
                last_render = out

            time.sleep(1)

    return (
        set_time,
        add_seconds,
        start_blink,
        stop_blink,
        run_render_loop,
        is_blinking,
        get_seconds
    )