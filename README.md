# IoT Smart Home Device Simulation

![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)
![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-4B-red.svg)
![IoT](https://img.shields.io/badge/IoT-Smart%20Home-green.svg)
![License](https://img.shields.io/badge/License-Educational-yellow.svg)

This project implements a comprehensive IoT simulation for smart home devices using Raspberry Pi. It provides both hardware-based implementations and software simulators for various sensors and actuators commonly used in smart home applications.

## Features

### Sensors and Actuators
- **DHT11**: Temperature and humidity sensor
- **LCD1602**: 16x2 character LCD display with I2C interface
- **DS1**: Door button sensor
- **DPIR1**: PIR motion sensor
- **DMS**: Membrane switch sensor
- **DUS1**: Ultrasonic distance sensor

### Simulation Mode
The project includes full simulation capabilities, allowing development and testing without physical hardware. Each sensor has a corresponding simulator that mimics real-world behavior.

## Project Structure

```
├── dht/                    # DHT11 temperature/humidity sensor
│   ├── DHT11.py           # Main DHT11 implementation
│   └── LA_DHT.py          # DHT library wrapper
├── lcd/                    # LCD display components
│   ├── Adafruit_LCD1602.py # LCD driver
│   ├── LCD1602.py         # LCD implementation with CPU temp/time display
│   └── PCF8574.py         # I2C GPIO expander
├── simulation/             # Main simulation application
│   ├── main.py            # Entry point for the simulation
│   ├── settings.json      # Configuration file
│   ├── settings.py        # Settings loader
│   ├── components/        # Component implementations
│   │   ├── ds1.py         # Door button component
│   │   ├── dpir1.py       # PIR motion sensor component
│   │   ├── dms.py         # Membrane switch component
│   │   ├── dus1.py        # Ultrasonic sensor component
│   │   └── dht.py         # DHT sensor component
│   ├── sensors/           # Hardware sensor implementations
│   └── simulators/        # Software simulators
└── uds/                    # Ultrasonic distance sensor
    └── uds.py             # UDS implementation
```

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/paniicj0/IOT.git
   cd IOT
   ```

2. Install required dependencies:
   ```bash
   pip install RPi.GPIO
   ```

3. For LCD functionality, ensure I2C is enabled on your Raspberry Pi.

## Technologies Used

- **Python 3**: Primary programming language
- **RPi.GPIO**: Raspberry Pi GPIO control library
- **Threading**: Multi-threaded sensor monitoring
- **JSON**: Configuration file handling
- **I2C Communication**: LCD display interface
- **Ultrasonic Sensing**: Distance measurement
- **DHT Protocol**: Temperature/humidity sensing

## Configuration

The simulation behavior is controlled by `simulation/settings.json`:

```json
{
  "DS1": { "simulated": true, "pin": 5, "pull": "UP" },
  "DPIR1": { "simulated": true, "pin": 6 },
  "DMS": { "simulated": true, "pin": 13, "pull": "UP" },
  "DUS1": { "simulated": true, "trigger_pin": 23, "echo_pin": 24 }
}
```

- Set `"simulated": true` to use software simulators
- Set `"simulated": false` to use actual hardware sensors
- Configure GPIO pins according to your hardware setup

## Usage

### Running the Simulation

Navigate to the simulation directory and run:

```bash
cd simulation
python main.py
```

The application will start all configured sensors in separate threads and begin monitoring for events.

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
- Appropriate wiring and resistors

## GPIO Pin Configuration

Default pin assignments:
- DS1 (Door Button): GPIO 5
- DPIR1 (PIR Sensor): GPIO 6
- DMS (Membrane Switch): GPIO 13
- DUS1 (Ultrasonic): Trigger GPIO 23, Echo GPIO 24
- DHT11: GPIO 17
- LCD I2C: Address 0x27 or 0x3F

## Authors

- **[teodora525](https://github.com/teodora525)** - Teodora Nikolic
- **paniicj0** - Jovana Panic

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with both simulated and hardware modes
5. Submit a pull request

## License

This project is part of an IoT course implementation and is intended for educational purposes.
