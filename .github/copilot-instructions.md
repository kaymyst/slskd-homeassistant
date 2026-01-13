# Guidance for AI coding agents working on this repo

This file contains concise, actionable notes to help an AI code assistant be productive in this Home Assistant custom integration.

- **Project purpose:** Home Assistant integration `slskd` that exposes a single binary sensor for the Soulseek daemon (slskd) and polls the server periodically.

- **Key files:**
  - [custom_components/slskd/manifest.json](custom_components/slskd/manifest.json) — integration metadata and external requirement (`slskd-api>=0.1.5`).
  - [custom_components/slskd/__init__.py](custom_components/slskd/__init__.py) — config entry setup; creates coordinator and stores it in `hass.data[DOMAIN][entry.entry_id]`.
  - [custom_components/slskd/binary_sensor.py](custom_components/slskd/binary_sensor.py) — coordinator (`SlskdDataUpdateCoordinator`), entity (`SlskdConnectionBinarySensor`), polling and attribute mapping.
  - [custom_components/slskd/config_flow.py](custom_components/slskd/config_flow.py) — config flow and options flow; validates connectivity using `SlskdClient.server.state`.
  - [custom_components/slskd/const.py](custom_components/slskd/const.py) — domain and configuration keys (use these constants when modifying code).

- **Big-picture architecture & data flow:**
  - Integration registers as a config entry (no YAML). On `async_setup_entry` in `__init__.py` a `SlskdDataUpdateCoordinator` is constructed.
  - The coordinator (defined in `binary_sensor.py`) owns the `SlskdClient` (from `slskd_api`) and performs periodic polling via `DataUpdateCoordinator`.
  - Entities (currently a single binary sensor) reference the coordinator to read `coordinator.data` and subscribe via `async_add_listener` for state updates.
  - Coordinator results come from `client.server.state` and are used for `is_on`, `extra_state_attributes`, and `available`.

- **Patterns and conventions to follow (project-specific):**
  - Use `const.py` constants (`DOMAIN`, `CONF_HOST`, `CONF_API_KEY`, `DEFAULT_SCAN_INTERVAL`) rather than hard-coded strings.
  - Prefer `DataUpdateCoordinator` for polling and centralizing network calls. Example: `SlskdDataUpdateCoordinator` in `binary_sensor.py`.
  - Place coordinator class in the platform module (here `binary_sensor.py`) and create it from `async_setup_entry` in `__init__.py`.
  - Test network calls in config flows and setup using `self.hass.async_add_executor_job` when calling synchronous client methods.
  - Use `hass.data.setdefault(DOMAIN, {})` and store coordinator by `entry.entry_id` so multiple entries are supported.
  - Forward platform setups using `hass.config_entries.async_forward_entry_setups(entry, ["binary_sensor"])`.

- **Notable implementation details / examples to reuse:**
  - Unique ID: the entity sets `_attr_unique_id = "slskd_connected"` — reuse the `unique_id` pattern when adding entities.
  - Device class: `_attr_device_class = "connectivity"` for connection sensors.
  - Poll interval: `DEFAULT_SCAN_INTERVAL` (30s) defined in `const.py` and used as `update_interval` for the coordinator.
  - Connection test: `config_flow` imports `SlskdClient` and calls `client.server.state` inside `hass.async_add_executor_job`.

- **Developer workflows & quick commands (discoverable from codebase):**
  - Installation/test in Home Assistant: install via HACS (this repo includes `hacs.json`) or place under `custom_components/slskd` and restart Home Assistant, then add integration via UI (Settings → Devices & Services → Add Integration → slskd).
  - There are no repo-level automated tests in this project; run Home Assistant dev environment or use an instance to validate behavior.

- **Integration points & dependencies:**
  - External dependency: `slskd-api` (declared in `manifest.json`) — network client used to query server state.
  - Platform: `binary_sensor` only. If adding other platforms, follow the same pattern of coordinator creation and forwarding from `async_setup_entry`.

- **When modifying this integration:**
  - Update `manifest.json` requirements if you add external packages.
  - Keep network logic inside the coordinator; entities should read only from `coordinator.data` and not perform network I/O directly.
  - Use the existing config flow pattern to validate connectivity and create entries.

If anything here is unclear or you want more detail (examples for adding a new platform or expanding the coordinator), tell me which area to expand.
