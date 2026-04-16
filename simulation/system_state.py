import threading


class SystemState:
    def __init__(self, pin_code="1234"):
        self.lock = threading.Lock()

        self.pin_code = str(pin_code)

        self.system_armed = False
        self.pending_arm = False
        self.alarm_active = False
        self.pending_entry_pin = False
        self.entry_source = None

        self.people_count = 0

    def arm_pending(self):
        with self.lock:
            self.pending_arm = True

    def arm_now(self):
        with self.lock:
            self.pending_arm = False
            self.system_armed = True

    def disarm(self):
        with self.lock:
            self.pending_arm = False
            self.system_armed = False
            self.alarm_active = False
            self.pending_entry_pin = False
            self.entry_source = None

    def activate_alarm(self):
        with self.lock:
            self.alarm_active = True

    def deactivate_alarm(self):
        with self.lock:
            self.alarm_active = False

    def is_armed(self):
        with self.lock:
            return self.system_armed

    def is_pending_arm(self):
        with self.lock:
            return self.pending_arm

    def is_alarm_active(self):
        with self.lock:
            return self.alarm_active

    def check_pin(self, entered_pin: str):
        with self.lock:
            return str(entered_pin) == self.pin_code

    def get_people_count(self):
        with self.lock:
            return self.people_count

    def set_people_count(self, value: int):
        with self.lock:
            self.people_count = max(0, int(value))

    def add_person(self):
        with self.lock:
            self.people_count += 1

    def remove_person(self):
        with self.lock:
            self.people_count = max(0, self.people_count - 1)

    def start_entry_delay(self, source: str):
        with self.lock:
            self.pending_entry_pin = True
            self.entry_source = source

    def clear_entry_delay(self):
        with self.lock:
            self.pending_entry_pin = False
            self.entry_source = None

    def is_entry_delay_active(self):
        with self.lock:
            return self.pending_entry_pin

    def get_entry_source(self):
        with self.lock:
            return self.entry_source