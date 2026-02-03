import json
from influx_writer import InfluxWriter

with open("config.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)

inf = cfg["influx"]

writer = InfluxWriter(
    url=inf["url"],
    token=inf["token"],
    org=inf["org"],
    bucket=inf["bucket"]
)

writer.write_record({
    "pi_id": "TEST_PI",
    "device_name": "TEST_DEVICE",
    "sensor": "TEST_SENSOR",
    "value": 1,
    "simulated": True,
    "timestamp": "2026-02-01T12:00:00Z"
})

print("OK: wrote one point")
