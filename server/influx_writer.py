from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from datetime import datetime, timezone


class InfluxWriter:
    def __init__(self, url: str, token: str, org: str, bucket: str):
        self.client = InfluxDBClient(url=url, token=token, org=org)
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
        self.bucket = bucket
        self.org = org

    def _parse_timestamp(self, ts):
        try:
            dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            return datetime.now(timezone.utc)

    def _add_field_or_tag(self, point: Point, key: str, value):
        if value is None:
            return point

        if isinstance(value, bool):
            return point.field(key, value)

        # polja koja moraju uvek biti float
        if key in {"value", "distance_cm", "temperature", "humidity", "magnitude"} and isinstance(value, (int, float)) and not isinstance(value, bool):
            return point.field(key, float(value))

        if isinstance(value, int) and not isinstance(value, bool):
            return point.field(key, value)

        if isinstance(value, float):
            return point.field(key, value)

        if isinstance(value, str):
            return point.tag(key, value)

        return point.tag(key, str(value))

    def write_record(self, rec: dict):
        dt = self._parse_timestamp(rec.get("timestamp"))

        point = (
            Point("sensor_data_v2")
            .tag("pi_id", str(rec.get("pi_id", "")))
            .tag("device_name", str(rec.get("device_name", "")))
            .tag("sensor", str(rec.get("sensor", "")))
            .tag("simulated", str(rec.get("simulated", False)).lower())
            .time(dt, WritePrecision.NS)
        )

        raw = rec.get("value", 0)

        if isinstance(raw, dict):
            for key, value in raw.items():
                point = self._add_field_or_tag(point, key, value)
        else:
            point = self._add_field_or_tag(point, "value", raw)

        self.write_api.write(bucket=self.bucket, org=self.org, record=point)

    def close(self):
        try:
            self.client.close()
        except Exception:
            pass