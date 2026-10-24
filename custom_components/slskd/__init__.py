from datetime import timedelta
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from .const import DOMAIN, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, CONF_API_KEY_ROLE, ROLE_ADMINISTRATOR, ROLE_READWRITE
from .binary_sensor import SlskdDataUpdateCoordinator
from .helpers import detect_role, get_role
import logging

_LOGGER = logging.getLogger(__name__)

SEARCH_SERVICE = "search"
SEARCH_SERVICE_SCHEMA = vol.Schema({
    vol.Required("search_text"): cv.string,
})

DOWNLOAD_SERVICE = "download"
DOWNLOAD_SERVICE_SCHEMA = vol.Schema({
    vol.Required("username"): cv.string,
    vol.Required("filename"): cv.string,
    vol.Optional("size"): vol.Coerce(int),
})

PLATFORMS = ["binary_sensor", "switch", "sensor"]


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the integration (nothing to do for YAML)."""
    return True

async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old config entries."""
    if entry.version == 1 and entry.minor_version < 2:
        # 1.1 saved "readwrite" only for keys that could read GET /api/v0/server,
        # which slskd restricts to administrator keys
        def _fix(d):
            if d.get(CONF_API_KEY_ROLE) == ROLE_READWRITE:
                return {**d, CONF_API_KEY_ROLE: ROLE_ADMINISTRATOR}
            return d

        hass.config_entries.async_update_entry(
            entry, data=_fix(entry.data), options=_fix(entry.options), minor_version=2
        )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up slskd from a config entry."""

    try:
        # Create coordinator (includes client)
        coordinator = SlskdDataUpdateCoordinator(hass, entry)

        # Test connection first
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        _LOGGER.error("Failed to connect to slskd server: %s", err)
        raise ConfigEntryNotReady from err

    # Entries created before the role option existed: probe the key once and save it
    role = get_role(entry)
    if role is None:
        try:
            role = await hass.async_add_executor_job(detect_role, coordinator.client)
        except Exception as err:
            _LOGGER.error("Failed to detect slskd API key role: %s", err)
            raise ConfigEntryNotReady from err
        _LOGGER.info("Detected slskd API key role: %s", role)
        hass.config_entries.async_update_entry(
            entry, data={**entry.data, CONF_API_KEY_ROLE: role}
        )

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Update coordinator interval when options change
    async def _async_options_updated(hass, entry):
        # Entities depend on the role, so reload when it changes
        if get_role(entry) != role:
            await hass.config_entries.async_reload(entry.entry_id)
            return
        scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        coordinator.update_interval = timedelta(seconds=scan_interval)
        await coordinator.async_request_refresh()

    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

    # Forward to platforms (awaited)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def handle_search(call: ServiceCall) -> None:
        """Initiate a search on the slskd server."""
        search_text = call.data["search_text"]
        _LOGGER.debug("Initiating slskd search for: %s", search_text)
        try:
            result = await hass.async_add_executor_job(
                coordinator.client.searches.search_text, search_text
            )
            search_id = result.get("id")
            coordinator.last_search_id = search_id
            coordinator.last_search_results = None
            coordinator.last_search_state = None
            _LOGGER.info("Search started: '%s' (id=%s)", search_text, search_id)
        except Exception as err:
            _LOGGER.error("Failed to initiate slskd search: %s", err)

    if not hass.services.has_service(DOMAIN, SEARCH_SERVICE):
        hass.services.async_register(
            DOMAIN, SEARCH_SERVICE, handle_search, schema=SEARCH_SERVICE_SCHEMA
        )

    async def handle_download(call: ServiceCall) -> None:
        """Enqueue a download on the slskd server."""
        username = call.data["username"]
        filename = call.data["filename"]
        size = call.data.get("size")
        _LOGGER.debug("Enqueueing download: %s from %s (size=%s)", filename, username, size)
        file_entry = {"filename": filename}
        if size is not None:
            file_entry["size"] = size
        try:
            await hass.async_add_executor_job(
                coordinator.client.transfers.enqueue,
                username,
                [file_entry],
            )
            coordinator.last_download_username = username
            coordinator.last_download_filename = filename
            coordinator.last_download_state = "Queued"
            coordinator.last_download_bytes_transferred = 0
            coordinator.last_download_size = None
            coordinator.last_download_average_speed = None
            _LOGGER.info("Download enqueued: %s from %s", filename, username)
        except Exception as err:
            _LOGGER.error("Failed to enqueue download: %s", err)

    if not hass.services.has_service(DOMAIN, DOWNLOAD_SERVICE):
        hass.services.async_register(
            DOMAIN, DOWNLOAD_SERVICE, handle_download, schema=DOWNLOAD_SERVICE_SCHEMA
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        # Services capture this entry's coordinator; drop them so a reload re-registers fresh ones
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, SEARCH_SERVICE)
            hass.services.async_remove(DOMAIN, DOWNLOAD_SERVICE)
    return unload_ok
