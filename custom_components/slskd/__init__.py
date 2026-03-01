from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from .const import DOMAIN
from .binary_sensor import SlskdDataUpdateCoordinator
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
})


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the integration (nothing to do for YAML)."""
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

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Forward to binary_sensor platform (awaited)
    await hass.config_entries.async_forward_entry_setups(entry, ["binary_sensor", "switch", "sensor"])

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
        _LOGGER.debug("Enqueueing download: %s from %s", filename, username)
        try:
            await hass.async_add_executor_job(
                coordinator.client.transfers.enqueue,
                username,
                [{"filename": filename}],
            )
            _LOGGER.info("Download enqueued: %s from %s", filename, username)
        except Exception as err:
            _LOGGER.error("Failed to enqueue download: %s", err)

    if not hass.services.has_service(DOMAIN, DOWNLOAD_SERVICE):
        hass.services.async_register(
            DOMAIN, DOWNLOAD_SERVICE, handle_download, schema=DOWNLOAD_SERVICE_SCHEMA
        )

    return True
