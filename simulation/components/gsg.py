from simulators.gsg import run_gsg_simulator
import threading
import time
import math


def gsg_callback(magnitude, code, on_value=None):
    t = time.localtime()
    print("=" * 20)
    print(f"Timestamp: {time.strftime('%H:%M:%S', t)}")
    print("Sensor: GSG (Gyroscope)")
    print(f"Code: {code}")
    print(f"Movement magnitude: {magnitude:.3f}")

    if on_value is not None:
        on_value({
            "value": float(magnitude),
            "code": code,
            "magnitude": float(magnitude)
        })


# ---------- REAL SENSOR (MPU6050 over I2C) ----------
class _MPU6050:
    # Minimal MPU6050 reader using smbus/smbus2
    PWR_MGMT_1 = 0x6B
    ACCEL_XOUT_H = 0x3B

    def __init__(self, bus, address=0x68):
        self.bus = bus
        self.address = address

        # Wake up the MPU6050 (clear sleep bit)
        self.bus.write_byte_data(self.address, self.PWR_MGMT_1, 0x00)
        time.sleep(0.05)

    def _read_word(self, reg):
        high = self.bus.read_byte_data(self.address, reg)
        low = self.bus.read_byte_data(self.address, reg + 1)
        val = (high << 8) | low
        # convert to signed 16-bit
        if val >= 0x8000:
            val = -((65535 - val) + 1)
        return val

    def read_accel_g(self):
        # For default accel range ±2g => 16384 LSB/g
        ax = self._read_word(self.ACCEL_XOUT_H) / 16384.0
        ay = self._read_word(self.ACCEL_XOUT_H + 2) / 16384.0
        az = self._read_word(self.ACCEL_XOUT_H + 4) / 16384.0
        return ax, ay, az


def run_gsg(settings, threads, stop_event, on_value=None):
    delay = settings.get("poll_delay", 2)

    if settings.get("simulated", True):
        print("Starting GSG simulator")
        th = threading.Thread(
            target=run_gsg_simulator,
            args=(delay, lambda mag, code: gsg_callback(mag, code, on_value), stop_event),
            daemon=True,
        )
        th.start()
        threads.append(th)
        print("GSG simulator started")
        return

    # REAL mode: MPU6050 via I2C
    # settings supported:
    # - address (default 0x68)
    # - i2c_bus (default 1)
    address = int(settings.get("address", 0x68))
    i2c_bus = int(settings.get("i2c_bus", 1))

    # Prefer smbus2, fallback smbus
    try:
        from smbus2 import SMBus  # type: ignore
    except Exception:
        from smbus import SMBus  # type: ignore

    def run_gsg_loop():
        print(f"Starting real GSG (MPU6050) on I2C bus {i2c_bus}, address 0x{address:02X} (delay={delay}s)")

        with SMBus(i2c_bus) as bus:
            mpu = _MPU6050(bus, address=address)

            # Initial accel sample
            prev_ax, prev_ay, prev_az = mpu.read_accel_g()

            while not stop_event.is_set():
                ax, ay, az = mpu.read_accel_g()

                # magnitude = size of change vector since last sample
                dx = ax - prev_ax
                dy = ay - prev_ay
                dz = az - prev_az
                magnitude = math.sqrt(dx * dx + dy * dy + dz * dz)

                prev_ax, prev_ay, prev_az = ax, ay, az

                gsg_callback(magnitude, "REAL", on_value)
                time.sleep(delay)

        print("GSG real sensor stopped")

    th = threading.Thread(target=run_gsg_loop, daemon=True)
    th.start()
    threads.append(th)
    print("GSG real sensor thread started")