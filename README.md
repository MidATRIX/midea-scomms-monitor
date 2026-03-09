# Midea / Senville S-Comms (S1S2) Monitor

Reverse engineering and monitoring tools for the S-Comms (S1S2) communication bus used by some Midea-based inverter HVAC systems (including Senville central air units).

This project focuses on passive monitoring and protocol documentation of the communication between the indoor air handler and outdoor inverter unit.

The goal is to expose internal system telemetry such as compressor behavior, temperatures, voltages, and expansion valve position and make those metrics available for monitoring.


## How to run
PYTHONPATH=. python3  src/main.py 


## Project Goals
* Document the S-Comms (S1S2) protocol structure.
* Capture and analyze RS485 traffic.
* Validate CRC-16/MODBUS frame integrity.
* Identify sensor fields and scaling.
* Monitor real inverter performance metrics.
* Integrate telemetry into Home Assistant.

> **Note:** This project currently focuses on observing and decoding system behavior rather than controlling the HVAC system.


## Current Capabilities
* [x] RS485 frame capture
* [x] CRC-16/MODBUS validation
* [x] Frame structure identification
* [x] Traffic pattern analysis
* [x] Sensor field correlation


### Identified Telemetry Fields

**Indoor Unit (IDU)**
* Mode
* Capacity demand
* Setpoint
* Blower speed
* Room temperature
* Coil temperature
* ...

**Outdoor Unit (ODU)**
* Mode
* Actual demand
* Coil temperature
* Outdoor ambient temperature
* Outdoor temperature with quarter-degree temperature value
* Discharge temperature
* Compressor frequency (Hz)
* Fan speed (target and actual)
* DC bus voltage (target and actual)
* Inverter DC bus voltage
* AC input voltage
* Current draw (Amps)
* EXV steps
* Runtime minutes
* Runtime hours
* ...

*These values were derived through traffic observation and calculated scaling, not official documentation. Interpretations may evolve as additional frames are analyzed.*


## Protocol Specification


### Example Frame Structure
`[A0] [01 00 20] [0C] [........PAYLOAD........] [E7 B4]`

| Byte(s) | Field | Description |
| :--- | :--- | :--- |
| `0` | Header | Frame synchronization byte |
| `1–3` | Frame ID | Message type |
| `4` | Length | Payload length |
| `5–16` | Data | Sensor payload |
| `17–18` | CRC | CRC-16/MODBUS checksum |


### Communication Characteristics

**Observed bus parameters:**
* **Baud Rate:** 4800
* **Data Bits:** 8
* **Parity:** None
* **Stop Bits:** 1
* **Protocol:** RS485


**Checksum algorithm:**
* **Type:** CRC-16 / MODBUS
* **Reversed Polynomial:** `0xA001`
* **Initial Value:** `0xFFFF`
* **Bit Order:** Reflected


## Traffic Pattern

Captured traffic shows a repeating exchange between the outdoor inverter and indoor air handler. 

**Observed message cycle:**
`20 → 21 → 20 → 50 → 20 → 51 → 20 → 52 → 20 → 53 → 20 → 91`

Message ID `20` appears to act as a high-frequency synchronization and telemetry frame, while the `50`-series messages rotate through additional data fields.


### Example Frame Capture

```text
13:51:42.853  Inverter (0001)     ID:20  A00001200C120F000077742604B5010001001D51
13:51:42.946  Air Handler (0100)  ID:20  A00100200C11010F000000170F6C60190000E7B400
```


## Home Assistant Integration

Parsed telemetry is being streamed into Home Assistant to provide real-time monitoring of inverter behavior. 

**Example metrics include:**
* Compressor frequency
* EXV position
* Bus voltage
* Capacity demand vs actual
* Temperature sensors
* Runtime tracking

The goal is to provide deep system visibility beyond thermostat-level data.


## Hardware Used

**Example hardware used during testing:**
* Waveshare RS485-to-Ethernet adapter
* Passive bus monitoring of S1/S2 lines
* Python capture and decoding scripts
* SQLite database for frame logging


## ⚠ Safety Notice

HVAC inverter systems may expose mains voltage on communication terminals depending on system design. Improper probing of HVAC control boards can result in:
* Serious injury
* Equipment damage
* Voided manufacturer warranties

This repository documents observational research on a specific system configuration. **Always verify electrical conditions before connecting any hardware.**


## Contributing

If you are working with Midea / Senville inverter systems and have additional frame captures or sensor mappings, contributions and observations are welcome.

## License

MIT License
