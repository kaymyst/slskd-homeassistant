from datetime import timedelta
import logging
from slskd_api import SlskdClient

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, CONF_HOST, CONF_API_KEY, DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class SlskdDataUpdateCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch slskd server state with automatic polling and debug logging."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        self.client = SlskdClient(
            host=entry.data[CONF_HOST],
            api_key=entry.data[CONF_API_KEY],
        )
        super().__init__(
            hass,
            _LOGGER,
            name="slskd server state",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
            update_method=self.async_update_data,
        )

    async def async_update_data(self):
        """Fetch data from slskd and log each poll."""
        _LOGGER.debug("Fetching slskd server state...")
        try:
            return await self.hass.async_add_executor_job(self.client.server.state)
        except Exception as err:
            _LOGGER.error("Error fetching slskd server state: %s", err)
            raise UpdateFailed from err


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Set up the binary sensor."""
    coordinator: SlskdDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SlskdConnectionBinarySensor(coordinator)])


class SlskdConnectionBinarySensor(BinarySensorEntity):
    """Binary sensor for slskd connection status."""

    _attr_name = "slskd Connected"
    _attr_device_class = "connectivity"

    def __init__(self, coordinator: SlskdDataUpdateCoordinator):
        self.coordinator = coordinator
        self._attr_unique_id = "slskd_connected"

    async def async_added_to_hass(self):
        """Register entity with coordinator to receive updates automatically."""
        self.coordinator.async_add_listener(self.async_write_ha_state)
        # Ensure first poll happens immediately if coordinator hasn't run yet
        if self.coordinator.last_update_success is None:
            await self.coordinator.async_request_refresh()

    @property
    def is_on(self) -> bool:
        """Return True if server is connected."""
        if not self.coordinator.data:
            return False
        return self.coordinator.data.get("isConnected", False)

    @property
    def extra_state_attributes(self):
        """Additional attributes."""
        if not self.coordinator.data:
            return {}
        return {
            "username": self.coordinator.data.get("username"),
            "listen_port": self.coordinator.data.get("listenPort"),
            "uptime": self.coordinator.data.get("uptime"),
        }

    @property
    def available(self) -> bool:
        """Return True if the coordinator data is valid."""
        return self.coordinator.last_update_success
