# slskd Home Assistant Integration

Binary sensor for monitoring the slskd server (Soulseek daemon).

## Features

- Binary sensor `binary_sensor.slskd_connected` (`on` when server is online)
- Attributes: username, listen_port, uptime
- Automatic polling every 30 seconds
- Config Flow UI for easy setup
- Service `slskd.search` to initiate a search on the Soulseek network

## Services

### `slskd.search`

Initiates a file search on the slskd server.

| Field | Required | Description |
|-------|----------|-------------|
| `search_text` | Yes | The search term to look for on the Soulseek network |

Example automation action:

```yaml
service: slskd.search
data:
  search_text: "Pink Floyd - The Wall"
```

> **Note:** The API key requires write access (not `readonly`) to initiate searches.

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
- role: `readonly` is sufficient for monitoring only; use `readwrite` to also use the `slskd.search` service
- and cidr: 0.0.0.0/0,::/0