# slskd Home Assistant Integration

Binary sensor for monitoring the slskd server (Soulseek daemon).

## Features

- Binary sensor `binary_sensor.slskd_connected` (`on` when server is online)
  - Attributes: `username`, `listen_port`, `uptime`
- Sensor `sensor.slskd_last_search_result_total` — live file count for the active search
  - Attributes: `search_id`, `search_state`, `results` (top 10 files sorted by bitrate)
- Sensor `sensor.slskd_last_download_status` — live transfer status for the last enqueued download
  - Attributes: `username`, `filename`, `full_path`, `bytes_transferred`, `size`, `average_speed_bps`, `progress_pct`
- Service `slskd.search` — initiate a search on the Soulseek network
- Service `slskd.download` — enqueue a file download from a peer
- Automatic polling every 30 seconds
- Config Flow UI for easy setup

## Entities

### `binary_sensor.slskd_connected`

Reports whether slskd is connected to the Soulseek network.

| Attribute | Description |
|-----------|-------------|
| `username` | Soulseek username |
| `listen_port` | Configured listen port |
| `uptime` | Server uptime |

### `sensor.slskd_last_search_result_total`

Tracks the result count and top results of the most recent search. The state value is the total number of files found. Once the search reaches `Completed`, the `results` attribute is populated with the top 10 files sorted by bitrate (highest first), then by size.

| Attribute | Description |
|-----------|-------------|
| `search_id` | UUID of the active search |
| `search_state` | `InProgress` or `Completed` |
| `results` | List of up to 10 files, each with `username`, `filename`, `size`, `bitrate` |

Example `results` entry:
```yaml
username: "some_peer"
filename: "\\Music\\Artist\\Album\\song.mp3"
size: 12345678
bitrate: 320
```

### `sensor.slskd_last_download_status`

Tracks the transfer state of the most recently enqueued download. The state value reflects the slskd transfer lifecycle. The sensor is seeded with `Queued` immediately after `slskd.download` is called, then updates every 30 seconds until the transfer finishes.

| State | Meaning |
|-------|---------|
| `Queued` | Waiting in the peer's upload queue |
| `InProgress` | Actively transferring |
| `Completed` | Transfer finished successfully |
| `Errored` | Transfer failed |
| `Cancelled` | Transfer was cancelled |

| Attribute | Description |
|-----------|-------------|
| `username` | Peer the file is from |
| `filename` | Short filename (leaf only) |
| `full_path` | Full remote file path |
| `bytes_transferred` | Bytes downloaded so far |
| `size` | Total file size in bytes |
| `average_speed_bps` | Current average transfer speed in bytes/sec |
| `progress_pct` | Percentage complete (0–100), present when `size` is known |

## Services

### `slskd.search`

Initiates a file search on the slskd server. Results are available via `sensor.slskd_last_search_result_total` once the search completes.

| Field | Required | Description |
|-------|----------|-------------|
| `search_text` | Yes | The search term to look for on the Soulseek network |

Example:

```yaml
action: slskd.search
data:
  search_text: "Pink Floyd - The Wall mp3"
```

### `slskd.download`

Enqueues a file download from a specific peer. Use the `username` and `filename` values from the `results` attribute of `sensor.slskd_last_search_result_total`.

| Field | Required | Description |
|-------|----------|-------------|
| `username` | Yes | Soulseek username of the peer |
| `filename` | Yes | Full remote file path |

Example — download the top result automatically:

```yaml
action: slskd.download
data:
  username: "{{ state_attr('sensor.slskd_last_search_result_total', 'results')[0].username }}"
  filename: "{{ state_attr('sensor.slskd_last_search_result_total', 'results')[0].filename }}"
```

> **Note:** The API key requires `readwrite` access to use `slskd.search` and `slskd.download`.

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