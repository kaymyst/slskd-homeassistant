from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from .const import DOMAIN
from .binary_sensor import SlskdDataUpdateCoordinator
import logging

_LOGGER = logging.getLogger(__name__)

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
    await hass.config_entries.async_forward_entry_setups(entry, ["binary_sensor", "switch"])

    return True
