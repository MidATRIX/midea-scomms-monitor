# Midea / Senville S-Comms (S1S2) Monitor

Reverse engineering and monitoring tools for the S-Comms (S1S2) communication bus used by Midea-based inverter HVAC systems (including Senville central air units).

This project passively monitors and decodes the communication between the indoor air handler and outdoor inverter unit, exposing internal telemetry — compressor behavior, temperatures, voltages, EXV position, and more — and streams those metrics into Home Assistant via MQTT.

> **Note:** This project is observation-only. It does not send commands or control the HVAC system.

[Home Assistant Discussion Thread](https://community.home-assistant.io/t/reverse-engineering-senville-midea-scomms/992233?u=midatrix)

---

## Requirements

- Python 3.10+
- Waveshare RS485-to-Ethernet adapter (or equivalent RS485 bridge)
- Passive tap on the S1/S2 communication lines
- Home Assistant with an MQTT broker (optional)

Install Python dependencies inside a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate        # Linux / macOS
# venv\Scripts\activate         # Windows

pip install -r requirements.txt
```

---

## Configuration

Edit `src/config.py` before running:

```python
# Network bridge IP/port (Waveshare adapter)
WAVESHARE_IP   = "192.168.x.x"
WAVESHARE_PORT = 8888

# Home Assistant MQTT broker
MQTT_IP          = "192.168.x.x"
MQTT_PORT_NUMBER = 1883
MQTT_USER        = "your_mqtt_username"
MQTT_PASS        = "your_mqtt_password"

# SQLite output directory
SQLITE_DB_DIR = "/var/lib/midea_telemetry"
```

---

## How to Run

```bash
# From the project root
python3 -m src.main
```

---

## Project Structure

```
src/
├── main.py                  # Main event loop — TCP connection, frame dispatch
├── config.py                # All user configuration (IPs, credentials, paths)
├── serial/
│   └── frame_buffer.py      # RS485 byte stream → validated frame slices
├── protocol/
│   └── validator.py         # CRC-16/MODBUS frame validation
├── decode/
│   └── sensors.py           # Frame payload → decoded sensor values
├── ha/
│   └── discovery.py         # Home Assistant MQTT discovery + state publishing
└── database/
    └── db_handler.py        # SQLite frame logging with daily rotation
data/
└── bus_noise.log            # Bytes that didn't match any known frame signature
```

---

## Project Goals

- Document the S-Comms (S1S2) protocol structure
- Capture and analyze RS485 traffic
- Validate CRC-16/MODBUS frame integrity
- Identify sensor fields and scaling factors
- Monitor real inverter performance metrics
- Integrate telemetry into Home Assistant

---

## Identified Telemetry Fields

**Indoor Unit (IDU) — frame `0100_20`**

| Field | Description |
|---|---|
| `IDU_Mode` | Operating mode (Off / Cool / Heat / Fan / Dry) |
| `IDU_Demand_Hz` | Requested compressor frequency |
| `Target_Setpoint` | Thermostat setpoint (°C) |
| `IDU_Blower_Speed` | Fan speed (Low / Medium / High / Boost / Auto) |
| `T1_Room_Temp` | Room air temperature (°C) |
| `T2_IDU_Coil_Temp` | Indoor coil temperature (°C) |

**Outdoor Unit (ODU) — frames `0001_20`, `0001_50`–`0001_53`**

| Field | Description |
|---|---|
| `ODU_Mode` | Operating mode (Off / Cool / Heat / Fan / Dry / Defrost) |
| `Compressor_Actual_Hz` | Live compressor frequency (Hz) |
| `ODU_Target_Hz` | PID target compressor frequency (Hz) |
| `T3_ODU_Coil_Temp` | Outdoor coil temperature (°C) |
| `T4_Outdoor_Temp` | Outdoor ambient temperature (°C) |
| `TP_Discharge_Temp` | Discharge line temperature (°C) |
| `Compressor_Actual_Amps` | Compressor current draw (A) |
| `ODU_Fan_Speed_Target_RPM` | Fan speed target (RPM) |
| `ODU_Fan_Speed_Actual_RPM` | Fan speed actual (RPM) |
| `ODU_Fan_Speed_Step` | Fan gear index |
| `ODU_DC_Bus_Voltage_Target` | DC bus voltage target (V) |
| `ODU_DC_Bus_Voltage_Actual` | DC bus voltage actual (V) |
| `Inverter_DC_Bus_Voltage_V` | Inverter DC bus voltage (V) |
| `AC_Input_Voltage_V` | AC input voltage (V) |
| `EXV_Position_Steps` | Expansion valve position (steps) |
| `PID_Step_Delta` | PID output step delta (signed) |
| `PID_P_Error` | PID proportional error term |
| `PID_I_Error` | PID integral error term |
| `Routine_Phase_Step` | Startup/idle routine phase (0–4 idle, 5–9 active ramp) |
| `Active_Ramp_Routine` | Active ramp flag (oil return / high load) |
| `Run_Minutes_Clock` | Runtime minutes counter |
| `Run_Hours_Clock` | Runtime hours counter |
| `VAC` | Byte 6 of frame 53 (under investigation) |

*Sensor values were derived through traffic observation and reverse-engineered scaling — not from official documentation. Interpretations may and will evolve as more frames are analyzed.*

---

## Protocol Specification

### Bus Parameters

| Parameter | Value |
|---|---|
| Baud Rate | 4800 |
| Data Bits | 8 |
| Parity | None |
| Stop Bits | 1 |
| Interface | RS485 half-duplex |

### Frame Structure (A0 frames)

```
[A0] [DD DD] [CC] [LL] [ ... PAYLOAD ... ] [CR CR] ([00])
  0    1  2    3    4     5 .. 5+LL-1        -3  -2    -1
```

| Bytes | Field | Notes |
|---|---|---|
| 0 | Header | `0xA0` |
| 1–2 | Device address | `0x0001` = ODU, `0x0100` = IDU |
| 3 | Message ID | `0x20`, `0x50`–`0x53`, etc. |
| 4 | Payload length | Number of data bytes that follow |
| 5..N | Payload | Sensor data |
| N+1–N+2 | CRC | CRC-16/MODBUS, little-endian |
| N+3 | Padding | `0x00` — present only on `direction 01` frames |

### Checksum

| Parameter | Value |
|---|---|
| Algorithm | CRC-16/MODBUS |
| Polynomial (reflected) | `0xA001` |
| Initial value | `0xFFFF` |
| Bit order | LSB-first (reflected) |
| Output | 2 bytes, little-endian |

### Message Cycle

Captured traffic shows a repeating exchange between ODU and IDU:

```
20 → 21 → 20 → 50 → 20 → 51 → 20 → 52 → 20 → 53 → 20 → 91
```

Message `20` is a high-frequency core telemetry frame. The `50`–`53` series rotates through extended diagnostic data.

### Example Captures

```
13:51:42.853  ODU (0001)  ID:20  A00001200C120F000077742604B5010001001D51
13:51:42.946  IDU (0100)  ID:20  A00100200C11010F000000170F6C60190000E7B400
```

---

## Home Assistant Integration

Parsed telemetry is published to Home Assistant via MQTT discovery. Sensors appear automatically under a `Senville Heat Pump` device in the HA device registry.

The publisher uses send-on-change logic with a 60-second heartbeat to keep values fresh without flooding the broker.

**Example metrics visible in HA:**

- Compressor Hz (actual vs. target)
- EXV position
- Bus voltage (AC in, DC bus, inverter)
- All temperature sensors
- Fan RPM (actual vs. target)
- PID error terms
- Runtime clock

---

## Database Logging

Frames are logged to a daily-rotating SQLite database under `SQLITE_DB_DIR`. A `latest.db` symlink is maintained for easy Grafana integration.

Each row captures a complete message cycle — one snapshot of all six frame types combined — timestamped at the moment the cycle completes.

---

## Hardware

| Component | Purpose |
|---|---|
| Waveshare RS485-to-Ethernet | Passive bus tap via TCP stream |
| S1/S2 HVAC wires | RS485 differential pair |

> **⚡ Bus Voltage — Important:** On this system the S1/S2 lines run at **5V**. This is specific to central air configurations where the indoor and outdoor units have **separate mains power supplies**. Most mini-split and single-power-supply units run their S-Comms bus at significantly higher voltages. Do not assume 5V — always measure before connecting any interface hardware.

![Waveshare Setup](images/Waveshare_Setup.png)

---

## ⚠️ Safety Notice

HVAC inverter systems may expose mains voltage on communication terminals depending on system design. Improper probing of HVAC control boards can result in serious injury, equipment damage, or voided warranties.

This project was developed on a **central air unit where the indoor and outdoor units are on separate mains circuits**. This is why the S1/S2 bus on this system measures at **5V**. Many other Midea-based systems — particularly mini-splits where both units share a single power supply — run their S-Comms bus at much higher voltages and may present hazardous potentials on those same terminals.

**Always measure bus voltage and verify electrical conditions before connecting any interface hardware.**

---

## Contributing

If you're working with Midea or Senville inverter systems and have additional frame captures, sensor mappings, or scaling corrections, contributions are welcome. Open an issue or pull request.

---

## License

MIT License
