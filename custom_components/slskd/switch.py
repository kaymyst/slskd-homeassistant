from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .binary_sensor import SlskdDataUpdateCoordinator

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Set up the switch."""
    coordinator: SlskdDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SlskdConnectionSwitch(coordinator)])


class SlskdConnectionSwitch(CoordinatorEntity, SwitchEntity):
    """Switch for slskd connection status."""

    def __init__(self, coordinator: SlskdDataUpdateCoordinator):
        super().__init__(coordinator)
        self._attr_name = "slskd Connection"
        self._attr_unique_id = "slskd_connection_switch"
        self._attr_icon = "mdi:connection"

    @property
    def is_on(self) -> bool:
        """Return True if server is connected."""
        if not self.coordinator.data:
            return False
        return self.coordinator.data.get("isConnected", False)

    async def async_turn_on(self, **kwargs) -> None:
        """Turn on the switch."""
        await self.hass.async_add_executor_job(self.coordinator.client.server.connect)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off the switch."""
        await self.hass.async_add_executor_job(self.coordinator.client.server.disconnect)
        await self.coordinator.async_request_refresh()
