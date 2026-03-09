"""DataUpdateCoordinator for Nucleares — polls the bridge /sensors endpoint."""

import logging
from datetime import timedelta

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_API_KEY, CONF_BRIDGE_URL, DEFAULT_POLL_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class NuclearesCoordinator(DataUpdateCoordinator):
    """Polls the Nucleares bridge and distributes data to all sensor entities."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.bridge_url = entry.data[CONF_BRIDGE_URL].rstrip("/")
        self.api_key    = entry.data[CONF_API_KEY]

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_POLL_INTERVAL),
        )

    async def _async_update_data(self) -> dict:
        """Fetch all sensor values from the bridge in a single request."""
        headers = {"X-API-Key": self.api_key}
        url     = f"{self.bridge_url}/sensors"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    if resp.status == 401:
                        raise UpdateFailed("Bridge rejected the API key (401). Check HA_API_KEY in your .env file.")
                    if resp.status == 403:
                        raise UpdateFailed("Bridge rejected the HA IP address (403). Check ALLOWED_IP in your .env file.")
                    if resp.status != 200:
                        raise UpdateFailed(f"Bridge returned unexpected status {resp.status}.")

                    return await resp.json()

        except aiohttp.ClientConnectorError as exc:
            raise UpdateFailed(f"Cannot reach bridge at {self.bridge_url}: {exc}") from exc
        except aiohttp.ClientError as exc:
            raise UpdateFailed(f"Bridge request failed: {exc}") from exc
