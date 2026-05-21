# Svartex EV Charger Integration for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub release](https://img.shields.io/github/release/deidonum/svartex-ha.svg)](https://github.com/deidonum/svartex-ha/releases)

Home Assistant integration for [Svartex](https://svartex.ua) EV chargers.

## Features

- Real-time monitoring of charger status, power, voltage and current
- Charging session tracking (energy, cost, time)
- Two independent charging schedules with full control
- WiFi signal and temperature monitoring
- Device diagnostic information

## Requirements

- Svartex EV Charger connected to the internet
- Account email registered at [my.svartex.com](https://my.svartex.com)
- Account password

## Installation

### HACS (recommended)

1. Open HACS in Home Assistant
2. Click **Custom repositories**
3. Add `https://github.com/deidonum/svartex-ha` with category **Integration**
4. Find **Svartex EV Charger** and click **Download**
5. Restart Home Assistant
6. Go to **Settings → Devices & Services → Add Integration**
7. Search for **Svartex** and follow the setup steps

### Manual

1. Copy `custom_components/svartex` to your Home Assistant `custom_components` folder
2. Restart Home Assistant
3. Go to **Settings → Devices & Services → Add Integration**
4. Search for **Svartex** and follow the setup steps

## Configuration

Enter your **my.svartex.com** account credentials:

| Field | Description |
|-------|-------------|
| Email | Your account email (e.g. `user@example.com`) |
| Password | Your account password |

> **Note:** Starting from firmware `2.0.8`, Svartex switched to account-based authentication via `direct-access.ladergy.com`. The old Station ID + password login is no longer supported. Make sure you have a registered account at [my.svartex.com](https://my.svartex.com) before adding the integration.

## Entities

### Sensors
| Entity | Description |
|--------|-------------|
| Status | Charger state (Available, Charging, Finished, Error) |
| Power | Current charging power (kW) |
| Voltage L1/L2/L3 | Phase voltages (V) |
| Current L1/L2/L3 | Phase currents (A) |
| Total Energy | Total energy delivered (kWh) |
| Session Energy | Current session energy (kWh) |
| Session Cost | Current session cost (UAH) |
| Temperature 1 | Internal temperature (°C) |
| WiFi Signal | WiFi signal strength (dBm) |

### Binary Sensors
| Entity | Description |
|--------|-------------|
| Charging | True if charging is in progress |
| Online | True if charger is online |
| Session Active | True if charging session is active |

### Switches
| Entity | Description |
|--------|-------------|
| Schedule 1 | Enable/disable charging schedule 1 |
| Schedule 2 | Enable/disable charging schedule 2 |

### Number Controls
| Entity | Description |
|--------|-------------|
| Charging Current | Set station charging current (A) |
| Schedule 1 Current | Set schedule 1 current limit (A) |
| Schedule 2 Current | Set schedule 2 current limit (A) |

### Time Controls
| Entity | Description |
|--------|-------------|
| Schedule 1 Start | Set schedule 1 start time |
| Schedule 1 Stop | Set schedule 1 stop time |
| Schedule 2 Start | Set schedule 2 start time |
| Schedule 2 Stop | Set schedule 2 stop time |

### Diagnostic
| Entity | Description |
|--------|-------------|
| Serial Number | Device serial number |
| Firmware | Main firmware version |
| WiFi Firmware | WiFi module firmware version |
| IP Address | Device IP address |

## Tested devices

- Svartex single-phase EV Charger (1ph), firmware `2.0.8`

## Upgrading from v1.x

Version 2.0.0 introduces a breaking change in authentication. After updating:

1. Go to **Settings → Devices & Services**
2. Remove the existing Svartex integration
3. Add it again and enter your **email and password** from [my.svartex.com](https://my.svartex.com)

## Contributing

Pull requests are welcome! If you have a Svartex charger and want to contribute, please open an issue or PR.

## License

MIT License
