from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from datetime import datetime, timezone

class InfluxWriter:
    def __init__(self, url: str, token: str, org: str, bucket: str):
        self.client = InfluxDBClient(url=url, token=token, org=org)
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
        self.bucket = bucket
        self.org = org

    def write_record(self, rec: dict):
        ts = rec.get("timestamp")

        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        except Exception:
            dt = datetime.now(timezone.utc)

        raw = rec.get("value", 0)
        if isinstance(raw, dict):
            raw = raw.get("value", 0)

        value_num = float(raw)

        p = (
            Point("sensor_data")
            .tag("pi_id", str(rec.get("pi_id", "")))
            .tag("device_name", str(rec.get("device_name", "")))
            .tag("sensor", str(rec.get("sensor", "")))
            .tag("simulated", str(rec.get("simulated", False)).lower())
            .field("value", value_num)
            .time(dt, WritePrecision.NS)
        )

        self.write_api.write(bucket=self.bucket, org=self.org, record=p)

    def close(self):
        try:
            self.client.close()
        except:
            pass
