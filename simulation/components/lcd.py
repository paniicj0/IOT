import threading
import time


def create_lcd(settings):
    state = {
        "line1": "",
        "line2": ""
    }
    lock = threading.Lock()

    def lcd_write(line1: str, line2: str = ""):
        with lock:
            state["line1"] = str(line1)[:16]
            state["line2"] = str(line2)[:16]

        print("[LCD]")
        print(state["line1"])
        print(state["line2"])
        print("-" * 20)

    def lcd_clear():
        with lock:
            state["line1"] = ""
            state["line2"] = ""

        print("[LCD CLEAR]")

    def run_lcd_loop(stop_event):
        while not stop_event.is_set():
            time.sleep(0.2)

    return lcd_write, lcd_clear, run_lcd_loop