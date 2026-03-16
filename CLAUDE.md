# CLAUDE.md — AI Assistant Guide for slskd-homeassistant

## Project Overview

This is a **Home Assistant custom integration** for [slskd](https://github.com/slskd/slskd), a Soulseek daemon. It provides entities and services so Home Assistant can monitor and control a running slskd instance over its REST API.

- **HACS-installable** integration (see `hacs.json`)
- **Minimum HA version**: 2023.10.0
- **External dependency**: `slskd-api>=0.1.5` (Python client for the slskd REST API)
- **IoT class**: `local_polling` — polls slskd on a configurable interval (default: 10 s)

---

## Repository Layout

```
slskd-homeassistant/
├── custom_components/slskd/     # The entire integration lives here
│   ├── __init__.py              # Entry point: setup, service registration
│   ├── manifest.json            # Integration metadata and requirements
│   ├── const.py                 # All shared constants
│   ├── config_flow.py           # UI config and options flows
│   ├── binary_sensor.py         # Coordinator + connection binary sensor
│   ├── sensor.py                # Search result and download status sensors
│   ├── switch.py                # Connection control switch
│   └── services.yaml            # Service schema definitions (UI metadata)
├── hacs.json                    # HACS repository configuration
├── logo.svg                     # Integration logo
├── README.md                    # End-user documentation
└── .github/
    └── copilot-instructions.md  # Legacy AI assistant notes (superseded by this file)
```

---

## Architecture & Data Flow

```
Config Entry (UI)
      │
      ▼
async_setup_entry() — __init__.py
      │  Creates SlskdDataUpdateCoordinator
      │  Stores it in hass.data[DOMAIN][entry.entry_id]
      │  Registers services: slskd.search, slskd.download
      │  Forwards platform setup →
      ├── binary_sensor.py  →  SlskdConnectionBinarySensor
      ├── sensor.py         →  SlskdSearchResultSensor, SlskdLastDownloadSensor
      └── switch.py         →  SlskdConnectionSwitch

SlskdDataUpdateCoordinator (binary_sensor.py)
      │  Owns SlskdClient instance
      │  Polls client.server.state() every <scan_interval> seconds
      │  On each poll also checks active search / download state
      └── coordinator.data  →  Raw server state dict from slskd API
          coordinator.last_search_*   →  Search state fields
          coordinator.last_download_* →  Download state fields
```

**Key rule**: All network I/O goes through the coordinator. Entities read only from `coordinator.data` or coordinator state fields — they never call the API directly.

---

## Entities

| Entity | Type | Unique ID | What it shows |
|---|---|---|---|
| `slskd Connected` | `binary_sensor` | `slskd_connected` | `is_on` = `isConnected` from server state; attrs: username, listen_port, uptime |
| `slskd Last Search Result Total` | `sensor` | `slskd_last_search_result_total` | File count from last search; attrs: search_id, search_state, top-10 results list |
| `slskd Last Download Status` | `sensor` | `slskd_last_download_status` | Transfer state string; attrs: username, filename, full_path, bytes_transferred, size, average_speed_bps, progress_pct |
| `slskd Connection` | `switch` | `slskd_connection` | Calls `client.server.connect()` / `client.server.disconnect()` |

---

## Services

### `slskd.search`
Initiates a search on the slskd server.

```yaml
service: slskd.search
data:
  search_text: "Pink Floyd"
```

- Sets `coordinator.last_search_id` to the returned search ID
- Clears previous results; subsequent polls update `last_search_state` and, once completed, populate `last_search_results` (top 10 files, sorted by upload speed → bitrate → size)

### `slskd.download`
Enqueues a file download.

```yaml
service: slskd.download
data:
  username: "some_user"
  filename: "\\path\\to\\file.mp3"
  size: 12345678   # optional
```

- Stores username/filename in coordinator; subsequent polls update download state

---

## Constants (`const.py`)

```python
DOMAIN = "slskd"
CONF_HOST = "host"
CONF_API_KEY = "api_key"
CONF_SCAN_INTERVAL = "scan_interval"
DEFAULT_SCAN_INTERVAL = 10  # seconds
```

Always import and use these constants. Never hardcode domain strings or config keys.

---

## Conventions & Patterns

### Async & executor jobs
The `slskd-api` Python client is **synchronous**. All calls must be wrapped:

```python
result = await hass.async_add_executor_job(coordinator.client.some_method, arg1, arg2)
```

Never `await` a slskd client method directly.

### Coordinator state storage
The coordinator is stored per config entry:

```python
hass.data.setdefault(DOMAIN, {})
hass.data[DOMAIN][entry.entry_id] = coordinator
```

Retrieve it in platform `async_setup_entry`:

```python
coordinator: SlskdDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
```

### Adding a new entity
1. Create a class in the appropriate platform file inheriting from the HA entity base and (optionally) `CoordinatorEntity`.
2. Set `_attr_unique_id`, `_attr_name`, and relevant `_attr_device_class`.
3. Read state from `self.coordinator.data` or coordinator state fields.
4. Register listener in `async_added_to_hass`:
   ```python
   async def async_added_to_hass(self):
       self.coordinator.async_add_listener(self.async_write_ha_state)
   ```
5. Add the entity class to `async_setup_entry` in the same file.
6. If it's a new platform, add it to the `async_forward_entry_setups` call in `__init__.py` and list it in `manifest.json` under `"platforms"`.

### Adding a new service
1. Define a voluptuous schema constant in `__init__.py`.
2. Write an `async def handle_<service>()` function inside `async_setup_entry`.
3. Register with `hass.services.async_register(DOMAIN, SERVICE_NAME, handler, schema=SCHEMA)` guarded by `if not hass.services.has_service(...)`.
4. Add the service definition to `services.yaml` for UI metadata.

### Error handling
- Config entry setup: raise `ConfigEntryNotReady` on connection failure.
- Coordinator poll: raise `UpdateFailed` on exception.
- Service handlers: log with `_LOGGER.error` and swallow exceptions (do not crash HA).
- Search/download sub-fetches: log with `_LOGGER.warning` and continue.

### Path normalisation
slskd returns Windows-style backslash paths. Use the helper when comparing filenames:

```python
from .binary_sensor import _normalise_path
```

`_normalise_path` strips leading backslashes and normalises double-backslash sequences.

---

## Config & Options Flow

- **Config flow** (`SlskdConfigFlow`): collects `host` (default `http://localhost:5030`) and `api_key`; validates by calling `client.server.state`.
- **Options flow** (`SlskdOptionsFlowHandler`): allows changing `scan_interval` (integer seconds). Changes trigger `_async_options_updated` which updates `coordinator.update_interval` live.

---

## Development Workflow

### Testing
There are **no automated tests** in this repo. Validation requires a live Home Assistant instance or the HA development container.

To test changes:
1. Copy `custom_components/slskd/` into your HA `config/custom_components/` directory.
2. Restart Home Assistant.
3. Add or reload the integration via **Settings → Devices & Services**.
4. Check **Developer Tools → Logs** for debug output (`_LOGGER.debug`).

### When modifying
- Update `manifest.json` `"version"` when releasing.
- Update `manifest.json` `"requirements"` if you add/change external packages.
- Keep `services.yaml` in sync with service schemas in `__init__.py`.
- Do not add `strings.json` / `translations/` unless full i18n support is intended.

### Branch convention
Active development branches follow the pattern `claude/<description>-<id>`.

---

## External API Reference

The `slskd-api` Python package wraps the slskd REST API. Key methods used:

| Method | Used in |
|---|---|
| `client.server.state()` | Coordinator poll, config flow validation |
| `client.server.connect()` | Switch `turn_on` |
| `client.server.disconnect()` | Switch `turn_off` |
| `client.searches.search_text(text)` | `handle_search` service |
| `client.searches.state(search_id)` | Coordinator poll (active search) |
| `client.searches.search_responses(search_id)` | Coordinator poll (completed search) |
| `client.transfers.enqueue(username, files)` | `handle_download` service |
| `client.transfers.get_downloads(username)` | Coordinator poll (active download) |

All methods are **synchronous** — always wrap with `async_add_executor_job`.
