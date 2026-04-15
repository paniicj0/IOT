# IoT Smart Home System

![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)
![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-4B-red.svg)
![IoT](https://img.shields.io/badge/IoT-Smart%20Home-green.svg)
![License](https://img.shields.io/badge/License-Educational-yellow.svg)

A multi-device IoT smart home platform built with three Raspberry Pi units, each dedicated to a specific area of the home. The system provides security alarm management, occupancy tracking, climate monitoring, kitchen timer control, RGB lighting, and live camera streaming — all integrated through MQTT messaging, InfluxDB telemetry storage, Grafana dashboards, and a Flask web control panel.

## System Overview

The project is organized around three Raspberry Pi modules that communicate via MQTT through a central server:

| Device | Name | Area | Purpose |
|--------|------|------|---------|
| **PI1** | DoorModule | Entry | Door security, motion-based lighting, people counting |
| **PI2** | KitchenModule | Kitchen | Entry detection, climate monitoring, timer display, vibration alarm |
| **PI3** | LivingBedroomModule | Living Room / Bedroom | Climate monitoring, IR-controlled RGB lighting, LCD status display |

Each Pi runs sensor and actuator components (physical or simulated), batches telemetry data, and publishes it to an MQTT broker. A central Flask server subscribes to all telemetry topics, persists data to InfluxDB, and provides a web-based control panel with REST API endpoints.

## Features

### Security and Alarm System

- **Arm / Disarm** via membrane switch (DMS) or web panel with PIN code verification
- **10-second countdown** before the system transitions from pending to fully armed
- **Alarm triggers** (when armed):
  - Door entry detection (DS1 / DS2 press)
  - Motion with no occupants (DPIR1 / DPIR2 / DPIR3 when `people_count == 0`)
  - Vibration detection (GSG magnitude ≥ 0.7)
  - Button hold (DS1 / DS2 held for 2+ seconds)
- **Disarm**: Enter PIN via the web panel; command is broadcast to all Pis
- **10-second cooldown** after disarm before the system can be re-armed

### Occupancy Tracking

- PIR motion sensors (DPIR1 / DPIR2) trigger ultrasonic distance readings (DUS1 / DUS2)
- Entry: distance ≤ 50 cm → `people_count++`
- Exit: distance > 50 cm → `people_count--` (minimum 0)
- Empty room + armed system = alarm trigger

### Climate Monitoring

- Three DHT temperature/humidity sensors (DHT1, DHT2, DHT3) across rooms
- LCD display on PI3 auto-rotates readings from all three sensors every 3 seconds

### Kitchen Timer (PI2)

- 4-segment display (4SD) shows a countdown in `MM:SS` format
- Add time via the physical button (BTN, +30 s per press) or the web API
- Display blinks `00:00` when the timer finishes; stop blinking via BTN press or API

### RGB Lighting (PI3)

- BRGB RGB LED controlled via IR remote or web API
- Supported colors: RED, GREEN, BLUE, WHITE, YELLOW, PURPLE
- Commands: ON, OFF, and color selection

### Camera Streaming

- Live MJPEG video feed served at `/video_feed` via OpenCV
- Embedded in the web control panel

### Data Pipeline

- **MQTT (Eclipse Mosquitto)**: Message broker for sensor telemetry and actuator commands
- **InfluxDB 2.7**: Time-series database for persistent telemetry storage
- **Grafana**: Real-time visualization dashboards
- **Flask**: REST API, web control panel, and MQTT-to-InfluxDB bridge
- **Batch Processing**: Telemetry is buffered and sent in batches of 10 records or every 5 seconds

## Sensors and Actuators

### PI1 — Door Module

| Component | Type | Description |
|-----------|------|-------------|
| **DS1** | Sensor (Button) | Door entry button (GPIO 5, pull-up) |
| **DPIR1** | Sensor (PIR) | Entry motion detection (GPIO 6) |
| **DMS** | Sensor (Membrane Switch) | Arm/disarm trigger (GPIO 13, pull-up) |
| **DUS1** | Sensor (Ultrasonic) | Distance / people counting (Trigger GPIO 23, Echo GPIO 24) |
| **DL** | Actuator (LED) | Door light — turns on for 10 s on motion (GPIO 18) |
| **DB** | Actuator (Buzzer) | Alarm buzzer (GPIO 19) |

### PI2 — Kitchen Module

| Component | Type | Description |
|-----------|------|-------------|
| **DS2** | Sensor (Button) | Kitchen entry button (GPIO 17, pull-up) |
| **DPIR2** | Sensor (PIR) | Kitchen motion detection (GPIO 27) |
| **DUS2** | Sensor (Ultrasonic) | Kitchen people counting (Trigger GPIO 22, Echo GPIO 23) |
| **DHT3** | Sensor (Temp/Humidity) | Kitchen climate (GPIO 4) |
| **BTN** | Sensor (Button) | Timer add button — +30 s per press (GPIO 25, pull-up) |
| **GSG** | Sensor (Gyroscope) | Vibration / shake detection (magnitude 0.0–1.0) |
| **4SD** | Actuator (Display) | 4-segment timer display (MM:SS countdown) |

### PI3 — Living / Bedroom Module

| Component | Type | Description |
|-----------|------|-------------|
| **DHT1** | Sensor (Temp/Humidity) | Bedroom 1 climate (GPIO 16) |
| **DHT2** | Sensor (Temp/Humidity) | Bedroom 2 climate (GPIO 20) |
| **DPIR3** | Sensor (PIR) | Living room motion detection (GPIO 21) |
| **IR** | Sensor (Infrared) | IR remote receiver for RGB control (GPIO 12) |
| **BRGB** | Actuator (RGB LED) | Color-controlled LED (R: GPIO 18, G: GPIO 23, B: GPIO 24) |
| **LCD** | Actuator (Display) | 16×2 character LCD — rotates DHT readings |

## Project Structure

```
├── dht/                        # DHT11 hardware driver
│   ├── DHT11.py                # Main DHT11 implementation
│   └── LA_DHT.py               # DHT library wrapper
├── lcd/                        # LCD hardware driver
│   ├── Adafruit_LCD1602.py     # LCD driver
│   ├── LCD1602.py              # LCD with CPU temp/time display
│   └── PCF8574.py              # I2C GPIO expander
├── uds/                        # Ultrasonic distance sensor driver
│   └── uds.py                  # UDS implementation
├── infrastructure/             # Docker infrastructure
│   ├── docker-compose.yml      # MQTT, InfluxDB, Grafana orchestration
│   ├── .env                    # Environment variables
│   ├── broker-config/          # Mosquitto configuration
│   └── broker-data/            # Mosquitto persistent data
├── server/                     # Central Flask server
│   ├── app.py                  # REST API, web control panel, camera feed
│   ├── mqtt_listener.py        # MQTT subscriber (sensor telemetry)
│   ├── mqtt_publisher.py       # MQTT publisher (actuator commands)
│   ├── influx_writer.py        # InfluxDB data writer
│   ├── config.json             # Server/MQTT/InfluxDB configuration
│   └── test_influx.py          # InfluxDB connection test
├── simulation/                 # Multi-Pi simulation application
│   ├── main.py                 # Entry point — component wiring & event logic
│   ├── system_state.py         # Thread-safe alarm/arm/people state
│   ├── settings.json           # PI1 configuration
│   ├── settings_pi2.json       # PI2 configuration
│   ├── settings_pi3.json       # PI3 configuration
│   ├── settings.py             # Settings loader
│   ├── batch_sender.py         # Batch telemetry transmission
│   ├── telemetry_buffer.py     # Telemetry queue management
│   ├── mqtt_client.py          # MQTT client wrapper
│   ├── mqtt_actuator_listener.py # MQTT listener for actuator commands
│   ├── actuator_menu.py        # CLI menu for manual actuator control
│   ├── components/             # Component logic (sensor/actuator wrappers)
│   │   ├── ds1.py, ds2.py      # Door button sensors
│   │   ├── dpir1.py, dpir2.py, dpir3.py  # PIR motion sensors
│   │   ├── dus1.py, dus2.py    # Ultrasonic distance sensors
│   │   ├── dms.py              # Membrane switch
│   │   ├── dht1.py, dht2.py, dht3.py  # Temperature/humidity sensors
│   │   ├── btn.py              # Timer add button
│   │   ├── gsg.py              # Gyroscope vibration sensor
│   │   ├── ir.py               # Infrared remote receiver
│   │   ├── brgb.py             # RGB LED actuator
│   │   ├── display_4sd.py      # 4-segment timer display
│   │   ├── lcd.py              # LCD display actuator
│   │   ├── door_light.py       # Door light actuator
│   │   └── buzzer.py           # Buzzer actuator
│   ├── simulators/             # Software simulators for all sensors
│   ├── sensors/                # Hardware GPIO sensor implementations
│   └── actuators/              # Hardware GPIO actuator implementations
```

## Installation

### Prerequisites

- Python 3.7 or higher
- Docker and Docker Compose (for infrastructure services)
- Raspberry Pi (for hardware mode) or any Linux/macOS/Windows system (for simulation mode)

### 1. Clone the Repository

```bash
git clone https://github.com/paniicj0/IOT.git
cd IOT
```

### 2. Install Python Dependencies

```bash
pip install RPi.GPIO paho-mqtt influxdb-client flask opencv-python
```

> **Note:** `RPi.GPIO` is only needed when running on a Raspberry Pi. `opencv-python` is required for the camera feed on the server. For simulation-only mode on a desktop, `RPi.GPIO` can be omitted.

### 3. Start Infrastructure (Docker)

```bash
cd infrastructure
docker-compose up -d
```

This starts:
- **Mosquitto MQTT Broker** — Port 1883 (MQTT), 9001 (WebSocket)
- **InfluxDB 2.7** — Port 8086 (Web UI & API)
- **Grafana** — Port 3000 (Dashboards)

Default credentials (configured in `.env`):
- **InfluxDB**: admin / admin_password
- **Grafana**: admin / admin_password

### 4. Configure InfluxDB

1. Open http://localhost:8086 and log in
2. The Docker setup auto-creates org `FTN` and bucket `telemetry`
3. Generate an API token: **Data → API Tokens → Generate API Token**
4. Update `server/config.json` with the generated token under `influx.token`

### 5. For LCD / I2C (Raspberry Pi only)

```bash
sudo raspi-config
# Interface Options → I2C → Enable
```

## Configuration

### Simulation Settings

Each Pi has its own settings file that defines which components are active and whether they run in simulated or hardware mode:

| File | Device | Components |
|------|--------|------------|
| `simulation/settings.json` | PI1 (DoorModule) | DS1, DPIR1, DMS, DUS1, DL, DB |
| `simulation/settings_pi2.json` | PI2 (KitchenModule) | DS2, DPIR2, DUS2, DHT3, BTN, 4SD, GSG |
| `simulation/settings_pi3.json` | PI3 (LivingBedroomModule) | DHT1, DHT2, DPIR3, IR, BRGB, LCD |

Key settings:
- `"simulated": true/false` — toggle between software simulator and real GPIO hardware
- `"security.pin_code"` — PIN for alarm arm/disarm (default: `"1234"`)
- `"batch.size"` / `"batch.interval_sec"` — telemetry batching (default: 10 records / 5 seconds)
- `"timer.button_add_seconds"` — seconds added per BTN press on PI2 (default: 30)

### Server Configuration (`server/config.json`)

```json
{
  "mqtt": {
    "host": "localhost",
    "port": 1883,
    "topic": "iot/+/sensors",
    "topic_actuators": "iot/pi1/actuators"
  },
  "influx": {
    "url": "http://localhost:8086",
    "token": "YOUR_INFLUXDB_TOKEN",
    "org": "FTN",
    "bucket": "telemetry"
  }
}
```

The server subscribes to `iot/+/sensors` (wildcard) to receive telemetry from all Pis.

## Usage

### 1. Start Infrastructure

```bash
cd infrastructure
docker-compose up -d
```

### 2. Start the Server

```bash
cd server
python app.py
```

The server will:
- Subscribe to `iot/+/sensors` for telemetry from all Pis
- Write telemetry to InfluxDB
- Serve the web control panel at http://localhost:5000/control
- Stream the camera feed at http://localhost:5000/video_feed
- Expose REST API endpoints for actuator control

### 3. Start a Simulation

Run any Pi simulation by specifying its settings file:

```bash
cd simulation
python main.py                          # PI1 (default — settings.json)
python main.py settings_pi2.json        # PI2
python main.py settings_pi3.json        # PI3
```

Each simulation instance:
- Initializes all sensors and actuators defined in its settings
- Batches and publishes telemetry to MQTT
- Listens for actuator commands from the server
- Provides a CLI menu for manual actuator control (PI1)

### 4. Access Dashboards

- **Grafana**: http://localhost:3000 — Add InfluxDB as a data source and create dashboards
- **Control Panel**: http://localhost:5000/control — Real-time system status, actuator controls, and camera feed

### Server API Endpoints

#### System Status
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/status` | Current system state (alarm, armed, people count, timer, BRGB) |
| GET | `/control` | Web control panel |
| GET | `/video_feed` | Live MJPEG camera stream |

#### PI1 — Door Module Actuators
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/actuators/DL/on` | Turn on door light |
| POST | `/actuators/DL/off` | Turn off door light |
| POST | `/actuators/DB/on` | Activate buzzer |
| POST | `/actuators/DB/off` | Deactivate buzzer |

#### Alarm Control
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/alarm/off` | Send PIN to disarm alarm |
| POST | `/alarm/pin?pin=XXXX` | Broadcast PIN to all Pis |

#### PI2 — Kitchen Timer
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/timer/set/{seconds}` | Set timer to specific value |
| POST | `/timer/add/{seconds}` | Add seconds to current timer |
| POST | `/timer/stop-blink` | Stop blink animation |

#### PI3 — RGB LED
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/brgb/on` | Turn on RGB LED |
| POST | `/brgb/off` | Turn off RGB LED |
| POST | `/brgb/color/{color}` | Set color (RED, GREEN, BLUE, WHITE, YELLOW, PURPLE) |

### Standalone Hardware Modules

Individual hardware drivers can be tested independently:

```bash
python dht/DHT11.py      # DHT11 temperature/humidity sensor
python lcd/LCD1602.py     # LCD1602 display
python uds/uds.py         # Ultrasonic distance sensor
```

## System Architecture

### Data Flow

```
Sensors (Physical / Simulated)
    │
    ▼
Sensor Components (simulation/components/)
    │
    ▼
Telemetry Buffer → Batch Sender (10 records or 5 sec)
    │
    ▼
MQTT Publisher ──→ Mosquitto Broker (port 1883)
    │
    ▼
Flask Server (MQTT Listener)
    │
    ├──→ InfluxDB (Time-series Storage)
    │         │
    │         ▼
    │     Grafana (Dashboards)
    │
    └──→ Web Control Panel (/control)
              │
              ▼
         Camera Feed (/video_feed)
```

### Actuator Control Flow

```
Web Control Panel / REST API / Grafana
    │
    ▼
Flask Server ──→ MQTT Publisher
    │
    ▼
Mosquitto Broker ──→ iot/pi{N}/actuators
    │
    ▼
Simulation MQTT Actuator Listener
    │
    ▼
Actuator Components (DL, DB, 4SD, BRGB, LCD)
```

### System Topology

```
┌──────────────────────────────────────────────────────────────────┐
│                    IoT Smart Home Network                        │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  PI1 (DoorModule)          MQTT Broker          Central Server   │
│  ├ DS1, DPIR1, DMS, DUS1   (Mosquitto)          ├ Flask API     │
│  ├ DL, DB                  Port 1883            ├ InfluxDB      │
│  └ iot/pi1/*          ◄──────────────►          ├ Grafana       │
│                                                  └ Camera Feed   │
│  PI2 (KitchenModule)                                             │
│  ├ DS2, DPIR2, DUS2, DHT3                                       │
│  ├ BTN, GSG, 4SD                                                 │
│  └ iot/pi2/*          ◄──────────────►                           │
│                                                                  │
│  PI3 (LivingBedroomModule)                                       │
│  ├ DHT1, DHT2, DPIR3, IR                                        │
│  ├ BRGB, LCD                                                     │
│  └ iot/pi3/*          ◄──────────────►                           │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

## Technologies Used

- **Python 3** — Primary programming language
- **RPi.GPIO** — Raspberry Pi GPIO control
- **MQTT (Paho)** — IoT messaging protocol
- **Eclipse Mosquitto** — MQTT broker
- **InfluxDB 2.7** — Time-series telemetry database
- **Grafana** — Data visualization dashboards
- **Flask** — REST API and web control panel
- **OpenCV** — Camera video capture and MJPEG streaming
- **Docker & Docker Compose** — Infrastructure orchestration
- **Threading** — Multi-threaded sensor monitoring and event handling
- **I2C** — LCD display communication protocol

## Authors

- **[teodora525](https://github.com/teodora525)** — Teodora Nikolic
- **[paniicj0](https://github.com/paniicj0)** — Jovana Panic

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with both simulated and hardware modes
5. Submit a pull request

## License

This project is part of an IoT course implementation and is intended for educational purposes.
