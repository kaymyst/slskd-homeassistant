# CLAUDE.md — AI Assistant Guide for slskd-homeassistant

## Project Overview

Home Assistant custom integration for monitoring and controlling a [slskd](https://github.com/slskd/slskd) server (Soulseek daemon). Version 0.6.0, licensed MIT.

- **Domain:** `slskd`
- **Platforms:** `binary_sensor`, `switch`
- **External dependency:** `slskd-api>=0.1.5` (declared in `manifest.json`)
- **Minimum Home Assistant:** 2023.10.0
- **IoT class:** `local_polling` (polls every 30 seconds by default)

## Repository Structure

```
custom_components/slskd/
├── __init__.py        # Integration entry point: creates coordinator, forwards platforms
├── const.py           # Constants: DOMAIN, CONF_HOST, CONF_API_KEY, DEFAULT_SCAN_INTERVAL
├── config_flow.py     # Config flow (UI setup) and options flow (scan_interval)
├── binary_sensor.py   # SlskdDataUpdateCoordinator + SlskdConnectionBinarySensor
├── switch.py          # SlskdConnectionSwitch (connect/disconnect control)
└── manifest.json      # Integration metadata, requirements, platforms
```

Other notable files:
- `hacs.json` — HACS custom repository metadata
- `.github/copilot-instructions.md` — AI guidance (overlaps with this file)
- `README.md` — User-facing installation and configuration docs
- `logo.svg` — Integration logo

## Architecture and Data Flow

```
SlskdClient (slskd_api)
    │
    ▼
SlskdDataUpdateCoordinator  ← polls client.server.state() every 30s
    │                          via hass.async_add_executor_job()
    │
    ├──▶ SlskdConnectionBinarySensor  (reads coordinator.data)
    │      is_on: data["isConnected"]
    │      attrs: username, listenPort, uptime
    │
    └──▶ SlskdConnectionSwitch  (reads coordinator.data, writes via client)
           is_on: data["isConnected"]
           turn_on: client.server.connect()
           turn_off: client.server.disconnect()
```

### Startup sequence

1. User adds integration via UI → `config_flow.py` validates connection
2. `__init__.py:async_setup_entry()` creates `SlskdDataUpdateCoordinator`
3. Coordinator runs first refresh (`async_config_entry_first_refresh`)
4. On failure → `ConfigEntryNotReady` (HA retries later)
5. On success → coordinator stored in `hass.data[DOMAIN][entry.entry_id]`
6. Platforms forwarded: `binary_sensor`, `switch`
7. Each platform's `async_setup_entry()` retrieves the shared coordinator

## Key Classes

| Class | File | Role |
|---|---|---|
| `SlskdDataUpdateCoordinator` | `binary_sensor.py:16` | Owns `SlskdClient`, polls `server.state()`, stores result in `self.data` |
| `SlskdConnectionBinarySensor` | `binary_sensor.py:50` | Read-only entity showing connection status and attributes |
| `SlskdConnectionSwitch` | `switch.py:18` | Read/write entity for connecting and disconnecting the server |
| `SlskdConfigFlow` | `config_flow.py:7` | Config entry creation with connection validation |
| `SlskdOptionsFlowHandler` | `config_flow.py:54` | Post-setup options (scan_interval) |

## Conventions and Patterns

### Always use constants from `const.py`
- `DOMAIN = "slskd"`
- `CONF_HOST = "host"`, `CONF_API_KEY = "api_key"`, `CONF_SCAN_INTERVAL = "scan_interval"`
- `DEFAULT_SCAN_INTERVAL = 30`

### Coordinator pattern
- All network I/O goes through `SlskdDataUpdateCoordinator`
- Entities must read from `coordinator.data` only — never make direct network calls from entity properties
- Synchronous `slskd_api` calls must be wrapped: `await hass.async_add_executor_job(sync_call)`
- After write operations (connect/disconnect), call `await coordinator.async_request_refresh()`

### Multi-entry support
- Coordinator is stored per entry: `hass.data[DOMAIN][entry.entry_id]`
- Always use `hass.data.setdefault(DOMAIN, {})` before storing

### Entity conventions
- Unique IDs follow pattern: `slskd_<descriptive_name>` (e.g., `slskd_connected`, `slskd_connection_switch`)
- Set `_attr_name`, `_attr_unique_id`, `_attr_device_class` as class/instance attributes
- Use `CoordinatorEntity` base class for new entities that need automatic coordinator subscription (see `switch.py`)
- The binary sensor manually subscribes via `async_add_listener` (older pattern; `CoordinatorEntity` is preferred for new entities)

### Config flow
- Validate connectivity by creating a temporary `SlskdClient` and calling `client.server.state()`
- Default host: `http://localhost:5030`
- Return `errors["base"] = "cannot_connect"` on failure

## Adding a New Platform

1. Create `custom_components/slskd/<platform>.py` with `async_setup_entry()` function
2. Retrieve the shared coordinator: `coordinator = hass.data[DOMAIN][entry.entry_id]`
3. Create entity class extending `CoordinatorEntity` and the appropriate HA entity base
4. Read state from `coordinator.data` in properties
5. Add the platform name to `manifest.json` `"platforms"` array
6. Add the platform name to the forwarding list in `__init__.py:async_setup_entry()`

## Adding New Data to the Coordinator

The coordinator fetches the full server state dict from `client.server.state()`. If additional API endpoints are needed:

1. Extend `async_update_data()` in `SlskdDataUpdateCoordinator` (`binary_sensor.py:32`)
2. Call additional `slskd_api` methods via `hass.async_add_executor_job()`
3. Merge results into the returned dict
4. Access new data in entities via `coordinator.data["new_key"]`

## Development and Testing

### No automated test suite
This project has no pytest/tox setup and no CI/CD workflows. Testing is done manually in a Home Assistant instance.

### Manual testing workflow
1. Copy `custom_components/slskd/` into a Home Assistant dev instance's `custom_components/` directory
2. Restart Home Assistant
3. Add integration via Settings > Devices & Services > Add Integration > slskd
4. Provide slskd server host and API key
5. Verify entities appear and update correctly

### HACS installation (end users)
1. Add repository as custom integration in HACS
2. Install, restart Home Assistant
3. Add integration via UI

### No linting/formatting tools configured
The repository has no `.flake8`, `.pylintrc`, `pyproject.toml`, or pre-commit hooks. Follow standard Python/Home Assistant conventions when making changes.

## Common `slskd_api` Methods

The integration uses the `SlskdClient` class from `slskd-api`:

- `client.server.state()` — Returns server state dict with keys: `isConnected`, `username`, `listenPort`, `uptime`, etc.
- `client.server.connect()` — Connect the server to Soulseek
- `client.server.disconnect()` — Disconnect the server from Soulseek

## Important Notes

- The `slskd_api` library is **synchronous** — all calls must be wrapped in `hass.async_add_executor_job()`
- The coordinator class lives in `binary_sensor.py` (not in a separate file) — this is the project's convention
- `hacs.json` `"domains"` array currently lists only `["binary_sensor"]` — update if adding platforms that HACS needs to track
- The integration is config-entry only (no YAML configuration)
