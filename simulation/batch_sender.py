import time
from queue import Empty

def start_batch_sender_daemon(telemetry_q, publisher, topic: str, batch_size: int, interval_sec: int, stop_event):
    def worker():
        batch = []
        last_flush = time.time()

        while not stop_event.is_set():
            timeout = max(0.1, interval_sec - (time.time() - last_flush))
            try:
                item = telemetry_q.get(timeout=timeout)
                batch.append(item)
            except Empty:
                pass

            # flush uslovi
            if batch and (len(batch) >= batch_size or (time.time() - last_flush) >= interval_sec):
                publisher.publish_json(topic, batch)
                print(f"[BATCH] Sent {len(batch)} records to {topic}")
                batch.clear()
                last_flush = time.time()

        # final flush
        if batch:
            publisher.publish_json(topic, batch)
            print(f"[BATCH] Final sent {len(batch)} records to {topic}")

    import threading
    t = threading.Thread(target=worker, daemon=True)
    t.start()
    return t
