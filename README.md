# IoT Smart Home Device Simulation

![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)
![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-4B-red.svg)
![IoT](https://img.shields.io/badge/IoT-Smart%20Home-green.svg)
![License](https://img.shields.io/badge/License-Educational-yellow.svg)

This project implements a comprehensive IoT simulation for smart home devices using Raspberry Pi. It provides both hardware-based implementations and software simulators for various sensors and actuators commonly used in smart home applications. The system includes a complete data pipeline with MQTT messaging, InfluxDB time-series data storage, and Grafana visualization dashboards.

## Features

### Sensors and Actuators

**Sensors:**
- **DHT11**: Temperature and humidity sensor
- **LCD1602**: 16x2 character LCD display with I2C interface
- **DS1**: Door button sensor
- **DPIR1**: PIR motion sensor
- **DMS**: Membrane switch sensor
- **DUS1**: Ultrasonic distance sensor

**Actuators:**
- **DL**: Door light (LED indicator)
- **DB**: Door buzzer (active buzzer)

### Simulation Mode
The project includes full simulation capabilities, allowing development and testing without physical hardware. Each sensor has a corresponding simulator that mimics real-world behavior.

### Data Pipeline and Visualization
- **MQTT Broker**: Eclipse Mosquitto for reliable message queuing
- **InfluxDB**: Time-series database for storing sensor telemetry
- **Grafana**: Real-time visualization and monitoring dashboards
- **Flask Server**: REST API for actuator control and data ingestion
- **Batch Processing**: Efficient telemetry buffering and batch transmission

## Project Structure

```
├── dht/                    # DHT11 temperature/humidity sensor
│   ├── DHT11.py           # Main DHT11 implementation
│   └── LA_DHT.py          # DHT library wrapper
├── lcd/                    # LCD display components
│   ├── Adafruit_LCD1602.py # LCD driver
│   ├── LCD1602.py         # LCD implementation with CPU temp/time display
│   └── PCF8574.py         # I2C GPIO expander
├── infrastructure/         # Docker infrastructure
│   ├── docker-compose.yml # Container orchestration (MQTT, InfluxDB, Grafana)
│   ├── .env               # Environment configuration
│   ├── broker-config/     # Mosquitto MQTT broker configuration
│   └── broker-data/       # MQTT broker persistent data
├── server/                 # Backend server application
│   ├── app.py             # Flask REST API server
│   ├── mqtt_listener.py   # MQTT subscriber for sensor data
│   ├── mqtt_publisher.py  # MQTT publisher for actuator commands
│   ├── influx_writer.py   # InfluxDB data writer
│   ├── config.json        # Server configuration
│   └── test_influx.py     # InfluxDB connection test
├── simulation/             # Main simulation application
│   ├── main.py            # Entry point for the simulation
│   ├── settings.json      # Configuration file
│   ├── settings.py        # Settings loader
│   ├── batch_sender.py    # Batch telemetry transmission
│   ├── telemetry_buffer.py # Telemetry queue management
│   ├── mqtt_client.py     # MQTT client wrapper
│   ├── mqtt_actuator_listener.py # MQTT listener for actuator commands
│   ├── actuator_menu.py   # Interactive actuator control menu
│   ├── components/        # Component implementations
│   │   ├── ds1.py         # Door button component
│   │   ├── dpir1.py       # PIR motion sensor component
│   │   ├── dms.py         # Membrane switch component
│   │   ├── dus1.py        # Ultrasonic sensor component
│   │   ├── dht.py         # DHT sensor component
│   │   ├── door_light.py  # Door light actuator
│   │   └── buzzer.py      # Buzzer actuator
│   ├── sensors/           # Hardware sensor implementations
│   ├── simulators/        # Software simulators
│   └── actuators/         # Hardware actuator implementations
└── uds/                    # Ultrasonic distance sensor
    └── uds.py             # UDS implementation
```

## Installation

### Prerequisites

- Python 3.7 or higher
- Docker and Docker Compose (for infrastructure services)
- Raspberry Pi (for hardware mode) or any Linux/macOS system (for simulation mode)

### 1. Clone the Repository

```bash
git clone https://github.com/paniicj0/IOT.git
cd IOT
```

### 2. Install Python Dependencies

```bash
pip install RPi.GPIO paho-mqtt influxdb-client flask
```

### 3. Set Up Infrastructure (Docker)

The infrastructure includes MQTT broker, InfluxDB, and Grafana:

```bash
cd infrastructure
docker-compose up -d
```

This will start:
- **Mosquitto MQTT Broker**: Port 1883 (MQTT), 9001 (WebSocket)
- **InfluxDB**: Port 8086 (API)
- **Grafana**: Port 3000 (Web UI)

Default credentials (configured in `.env`):
- **InfluxDB**: admin / admin_password
- **Grafana**: admin / admin_password

### 4. Configure InfluxDB

After starting the infrastructure, configure InfluxDB:

1. Access InfluxDB UI at http://localhost:8086
2. Log in with credentials from `.env`
3. Create a bucket named `ftn-iot` (or use the one specified in `server/config.json`)
4. Generate an API token and update it in `server/config.json`

### 5. For LCD Functionality

Ensure I2C is enabled on your Raspberry Pi:

```bash
sudo raspi-config
# Navigate to Interface Options > I2C > Enable
```

## Technologies Used

- **Python 3**: Primary programming language
- **RPi.GPIO**: Raspberry Pi GPIO control library
- **MQTT (Paho)**: Message queuing for IoT communication
- **InfluxDB**: Time-series database for sensor data storage
- **Grafana**: Data visualization and monitoring dashboards
- **Flask**: Web framework for REST API server
- **Docker & Docker Compose**: Container orchestration
- **Eclipse Mosquitto**: MQTT broker
- **Threading**: Multi-threaded sensor monitoring
- **JSON**: Configuration file handling
- **I2C Communication**: LCD display interface
- **Ultrasonic Sensing**: Distance measurement
- **DHT Protocol**: Temperature/humidity sensing

## Configuration

### Simulation Settings (`simulation/settings.json`)

The simulation behavior is controlled by `simulation/settings.json`:

```json
{
  "device": { "pi_id": "PI1", "device_name": "DoorModule" },
  
  "mqtt": {
    "host": "localhost",
    "port": 1883,
    "topic_sensors": "iot/pi1/sensors",
    "topic_actuators": "iot/pi1/actuators"
  },
  
  "batch": { "size": 10, "interval_sec": 5 },
  
  "DS1": { "simulated": true, "pin": 5, "pull": "UP" },
  "DPIR1": { "simulated": true, "pin": 6 },
  "DMS": { "simulated": true, "pin": 13, "pull": "UP" },
  "DUS1": { "simulated": true, "trigger_pin": 23, "echo_pin": 24 },
  "DL": { "simulated": true, "pin": 18 },
  "DB": { "simulated": true, "pin": 19 }
}
```

- Set `"simulated": true` to use software simulators
- Set `"simulated": false` to use actual hardware sensors
- Configure GPIO pins according to your hardware setup
- `batch.size`: Number of telemetry records to batch before sending
- `batch.interval_sec`: Maximum time interval before flushing batch

### Server Configuration (`server/config.json`)

Configure the Flask server and connections:

```json
{
  "mqtt": {
    "host": "localhost",
    "port": 1883,
    "topic": "iot/pi1/sensors",
    "topic_actuators": "iot/pi1/actuators"
  },
  "influx": {
    "url": "http://localhost:8086",
    "token": "YOUR_INFLUXDB_TOKEN",
    "org": "FTN",
    "bucket": "ftn-iot"
  }
}
```

Update the `token` field with your InfluxDB API token.

## Usage

### Complete System Workflow

1. **Start Infrastructure Services**:
   ```bash
   cd infrastructure
   docker-compose up -d
   ```

2. **Start the Flask Server**:
   ```bash
   cd server
   python app.py
   ```
   
   The server will:
   - Listen for MQTT messages on `iot/pi1/sensors`
   - Write sensor data to InfluxDB
   - Provide REST API endpoints for actuator control
   - Serve a control panel at http://localhost:5000/control

3. **Start the Simulation/Sensors**:
   ```bash
   cd simulation
   python main.py
   ```
   
   The simulation will:
   - Start all configured sensors (DS1, DPIR1, DMS, DUS1)
   - Batch telemetry data and publish to MQTT
   - Listen for actuator commands from MQTT
   - Provide an interactive menu for manual actuator control

4. **Access Grafana Dashboard**:
   - Open http://localhost:3000
   - Log in with credentials (admin / admin_password)
   - Add InfluxDB as a data source
   - Create dashboards to visualize sensor data
   - Add the control panel iframe: http://localhost:5000/control

### Running the Simulation

Navigate to the simulation directory and run:

```bash
cd simulation
python main.py
```

The application will start all configured sensors in separate threads and begin monitoring for events. Sensor data is batched and sent to MQTT every 5 seconds or when 10 records accumulate.

### Server API Endpoints

The Flask server provides the following endpoints:

- **POST `/actuators/<device>/<action>`**: Control actuators
  - `device`: `DL` (door light) or `DB` (buzzer)
  - `action`: `on` or `off`
  - Example: `curl -X POST http://localhost:5000/actuators/DL/on`

- **GET `/control`**: Web-based control panel
  - Interactive UI for controlling actuators
  - Can be embedded in Grafana as an iframe

### Individual Components

Each sensor can be run independently:

- **DHT11**: `python ../dht/DHT11.py`
- **LCD1602**: `python ../lcd/LCD1602.py`
- **Ultrasonic Sensor**: `python ../uds/uds.py`

## Hardware Requirements

For hardware mode, you'll need:
- Raspberry Pi (any model with GPIO)
- DHT11 temperature/humidity sensor
- LCD1602 display with PCF8574 I2C backpack
- PIR motion sensor
- Push button switches
- Membrane switches
- HC-SR04 ultrasonic sensor
- Door light LED
- Active buzzer
- Appropriate wiring and resistors

## System Architecture

### Data Flow

```
Sensors (Physical/Simulated)
    ↓
Sensor Components (simulation/components/)
    ↓
Telemetry Buffer (telemetry_buffer.py)
    ↓
Batch Sender (batch_sender.py)
    ↓
MQTT Publisher → Mosquitto Broker (port 1883)
    ↓
Flask Server (MQTT Listener)
    ↓
InfluxDB (Time-series Database)
    ↓
Grafana (Visualization Dashboard)
```

### Actuator Control Flow

```
Grafana Control Panel / API Request
    ↓
Flask Server REST API (/actuators/<device>/<action>)
    ↓
MQTT Publisher → Mosquitto Broker
    ↓
Simulation MQTT Actuator Listener
    ↓
Actuator Components (LED, Buzzer)
```

### Key Components

- **Simulation App**: Reads sensors, batches telemetry, publishes to MQTT, controls actuators
- **MQTT Broker**: Message queue for decoupling data producers and consumers
- **Flask Server**: API gateway, MQTT-to-InfluxDB bridge, actuator command publisher
- **InfluxDB**: Persistent storage for time-series sensor data
- **Grafana**: Real-time visualization, historical analysis, and actuator control UI

## GPIO Pin Configuration

Default pin assignments:

**Sensors:**
- DS1 (Door Button): GPIO 5
- DPIR1 (PIR Sensor): GPIO 6
- DMS (Membrane Switch): GPIO 13
- DUS1 (Ultrasonic): Trigger GPIO 23, Echo GPIO 24
- DHT11: GPIO 17
- LCD I2C: Address 0x27 or 0x3F

**Actuators:**
- DL (Door Light): GPIO 18
- DB (Door Buzzer): GPIO 19

## Authors

- **[teodora525](https://github.com/teodora525)** - Teodora Nikolic
- **[paniicj0](https://github.com/paniicj0)** - Jovana Panic

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with both simulated and hardware modes
5. Submit a pull request

## License

This project is part of an IoT course implementation and is intended for educational purposes.
