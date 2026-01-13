# slskd Home Assistant Integration

Binary sensor for monitoring the slskd server (Soulseek daemon).

## Features

- Binary sensor `binary_sensor.slskd_connected` (`on` when server is online)
- Attributes: username, listen_port, uptime
- Automatic polling every 30 seconds
- Config Flow UI for easy setup

## Installation via HACS

1. Add this repository in HACS → Integrations → Custom Repositories
2. Select type **Integration**
3. Install and restart Home Assistant
4. Add the integration via **Settings → Devices & Services → Add Integration → slskd**

## Configuration

- Enter **host** (e.g., `http://192.168.0.156:5030`)
- Enter **API key**
- The binary sensor will appear automatically
