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
        "blink_on": True
    }
    lock = threading.Lock()

    def set_time(seconds: int):
        with lock:
            state["seconds"] = int(seconds)
            state["blink"] = False
            state["blink_on"] = True
        print(f"[4SD] set to {_format_mmss(seconds)}")

    def add_seconds(n: int):
        with lock:
            state["seconds"] += int(n)
        print(f"[4SD] +{int(n)} => {_format_mmss(state['seconds'])}")

    def start_blink():
        with lock:
            state["blink"] = True
            state["blink_on"] = True
        print("[4SD] BLINK 00:00")

    def stop_blink():
        with lock:
            state["blink"] = False
            state["blink_on"] = True
        print("[4SD] BLINK STOP")

    # simulirani “render” loop da se vidi na konzoli
    def run_render_loop(stop_event):
        while not stop_event.is_set():
            with lock:
                sec = state["seconds"]
                blink = state["blink"]
                blink_on = state["blink_on"]

                if blink:
                    # treperi 00:00 / prazno
                    out = "00:00" if blink_on else "    "
                    state["blink_on"] = not state["blink_on"]
                else:
                    out = _format_mmss(sec)

            print(f"[4SD] {out}")
            time.sleep(1)

    return set_time, add_seconds, start_blink, stop_blink, run_render_loop