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
        self._prev_game_connected: bool | None = None

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
                        raise UpdateFailed(
                            "Bridge rejected the API key (401). "
                            "Check HA_API_KEY in the bridge .env file matches the key "
                            "entered during integration setup."
                        )
                    if resp.status == 403:
                        raise UpdateFailed(
                            "Bridge rejected this HA server's IP address (403). "
                            "Check ALLOWED_IP in the bridge .env file."
                        )
                    if resp.status != 200:
                        raise UpdateFailed(
                            f"Bridge returned unexpected HTTP {resp.status}. "
                            f"URL: {url}"
                        )

                    data = await resp.json()

        except aiohttp.ClientConnectorError as exc:
            raise UpdateFailed(
                f"Cannot reach bridge at {self.bridge_url} — is the bridge script running? ({exc})"
            ) from exc
        except aiohttp.ServerTimeoutError as exc:
            raise UpdateFailed(
                f"Bridge at {self.bridge_url} timed out after 5s — bridge may be overloaded."
            ) from exc
        except aiohttp.ClientError as exc:
            raise UpdateFailed(f"Bridge request failed: {exc}") from exc

        # Log game connection state changes
        game_connected = data.get("game_connected", False)
        if self._prev_game_connected != game_connected:
            if game_connected:
                sensors = data.get("sensors", {})
                live = sum(1 for v in sensors.values() if v.get("value") is not None)
                _LOGGER.info(
                    "Nucleares game connection established — "
                    "%d/%d variables live (last poll: %s)",
                    live, len(sensors), data.get("last_poll"),
                )
            else:
                _LOGGER.warning(
                    "Nucleares game went offline or webserver was stopped. "
                    "All entities will show unavailable until the game reconnects."
                )
            self._prev_game_connected = game_connected

        # Debug-level detail every cycle (visible when HA log level = debug)
        if game_connected:
            sensors = data.get("sensors", {})
            null_count = sum(1 for v in sensors.values() if v.get("value") is None)
            if null_count:
                _LOGGER.debug(
                    "%d variable(s) returned null this cycle", null_count
                )

        return data
