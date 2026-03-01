import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .binary_sensor import SlskdDataUpdateCoordinator
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Set up slskd sensors."""
    coordinator: SlskdDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SlskdSearchResultSensor(coordinator)])


class SlskdSearchResultSensor(SensorEntity):
    """Sensor reporting the total file count of the last slskd search."""

    _attr_name = "slskd Last Search Result Total"
    _attr_native_unit_of_measurement = "files"
    _attr_unique_id = "slskd_last_search_result_total"

    def __init__(self, coordinator: SlskdDataUpdateCoordinator):
        self.coordinator = coordinator

    async def async_added_to_hass(self):
        self.coordinator.async_add_listener(self.async_write_ha_state)

    @property
    def native_value(self):
        return self.coordinator.last_search_result_count

    @property
    def extra_state_attributes(self):
        return {
            "search_id": self.coordinator.last_search_id,
            "search_state": self.coordinator.last_search_state,
            "results": self.coordinator.last_search_results,
        }

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success
