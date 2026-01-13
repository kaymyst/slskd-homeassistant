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

- Enter **host** (e.g., `http://[yourserverIP]:5030`)
- Enter **API key**
- The binary sensor will appear automatically

## slskd api key

- Edit slskd.yml and enter a key (16-255 character string) in web → authentication → api_keys → my_api_key → key
- for now the role is readonly → role: readonly 
- and cidr: 0.0.0.0/0,::/0