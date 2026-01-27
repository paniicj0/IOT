# telemetry_buffer.py
from queue import Queue

telemetry_q = Queue()  # thread-safe

def push(record: dict):
    telemetry_q.put(record)
