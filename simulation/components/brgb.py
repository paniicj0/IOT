import threading


def create_brgb(settings):
    state = {
        "is_on": False,
        "color": "OFF"
    }
    lock = threading.Lock()

    def print_state():
        with lock:
            print(f"[BRGB] ON={state['is_on']} COLOR={state['color']}")

    def rgb_on():
        with lock:
            state["is_on"] = True
            if state["color"] == "OFF":
                state["color"] = "WHITE"
        print("[BRGB] ON")
        print_state()

    def rgb_off():
        with lock:
            state["is_on"] = False
            state["color"] = "OFF"
        print("[BRGB] OFF")
        print_state()

    def rgb_set_color(color: str):
        color = str(color).upper()

        with lock:
            state["is_on"] = True
            state["color"] = color

        print(f"[BRGB] COLOR -> {color}")
        print_state()

    def rgb_get_state():
        with lock:
            return {
                "is_on": bool(state["is_on"]),
                "color": str(state["color"])
            }

    return rgb_on, rgb_off, rgb_set_color, rgb_get_state