from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, ROLE_ADMINISTRATOR
from .binary_sensor import SlskdDataUpdateCoordinator
from .helpers import get_role

UNIQUE_ID = "slskd_connection_switch"

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Set up the switch."""
    coordinator: SlskdDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    # Connect/disconnect needs an administrator key on slskd 0.26.2+
    if get_role(entry) == ROLE_ADMINISTRATOR:
        async_add_entities([SlskdConnectionSwitch(coordinator)])
        return
    # Drop a switch left over from when the key was administrator
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id("switch", DOMAIN, UNIQUE_ID)
    if entity_id:
        registry.async_remove(entity_id)


class SlskdConnectionSwitch(CoordinatorEntity, SwitchEntity):
    """Switch for slskd connection status."""

    def __init__(self, coordinator: SlskdDataUpdateCoordinator):
        super().__init__(coordinator)
        self._attr_name = "slskd Connection"
        self._attr_unique_id = UNIQUE_ID
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
