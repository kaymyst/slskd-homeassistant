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
        self.last_search_id: str | None = None
        self.last_search_result_count: int | None = None
        self.last_search_state: str | None = None
        self.last_search_results: list | None = None
        self.last_download_username: str | None = None
        self.last_download_filename: str | None = None
        self.last_download_state: str | None = None
        self.last_download_bytes_transferred: int | None = None
        self.last_download_size: int | None = None
        self.last_download_average_speed: float | None = None
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
            data = await self.hass.async_add_executor_job(self.client.server.state)
        except Exception as err:
            _LOGGER.error("Error fetching slskd server state: %s", err)
            raise UpdateFailed from err

        if self.last_search_id:
            try:
                search_state = await self.hass.async_add_executor_job(
                    self.client.searches.state, self.last_search_id
                )
                self.last_search_result_count = search_state.get("fileCount")
                self.last_search_state = search_state.get("state")
                _LOGGER.debug(
                    "Search %s state=%s file_count=%s",
                    self.last_search_id,
                    self.last_search_state,
                    self.last_search_result_count,
                )

                if self.last_search_state == "Completed" and self.last_search_results is None:
                    responses = await self.hass.async_add_executor_job(
                        self.client.searches.search_responses, self.last_search_id
                    )
                    self.last_search_results = _extract_top_results(responses)
                    _LOGGER.debug("Stored %d top results", len(self.last_search_results))
            except Exception as err:
                _LOGGER.warning(
                    "Could not fetch search results for %s: %s", self.last_search_id, err
                )

        if self.last_download_username and self.last_download_filename:
            try:
                downloads = await self.hass.async_add_executor_job(
                    self.client.transfers.get_downloads, self.last_download_username
                )
                transfer = _find_download(downloads, self.last_download_filename)
                if transfer:
                    self.last_download_state = transfer.get("state")
                    self.last_download_bytes_transferred = transfer.get("bytesTransferred")
                    self.last_download_size = transfer.get("size")
                    self.last_download_average_speed = transfer.get("averageSpeed")
                    _LOGGER.debug(
                        "Download %s state=%s bytes=%s/%s",
                        self.last_download_filename,
                        self.last_download_state,
                        self.last_download_bytes_transferred,
                        self.last_download_size,
                    )
            except Exception as err:
                _LOGGER.warning("Could not fetch download status: %s", err)

        return data


def _find_download(downloads, filename: str) -> dict | None:
    """Find a specific file transfer in the downloads response."""
    for entry in downloads or []:
        # Response may be a flat list of transfer objects or nested under directories
        if "filename" in entry:
            if entry["filename"] == filename:
                return entry
        for directory in entry.get("directories", []):
            for f in directory.get("files", []):
                if f.get("filename") == filename:
                    return f
    return None


def _extract_top_results(responses, limit: int = 10) -> list:
    """Flatten search responses into a sorted top-N file list."""
    files = []
    for response in responses or []:
        username = response.get("username", "")
        for f in response.get("files", []):
            bitrate = next(
                (a["value"] for a in f.get("attributes", []) if a.get("attribute") == 0),
                0,
            )
            files.append({
                "username": username,
                "filename": f.get("filename", ""),
                "size": f.get("size", 0),
                "bitrate": bitrate,
            })
    files.sort(key=lambda x: (x["bitrate"], x["size"]), reverse=True)
    return files[:limit]


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
