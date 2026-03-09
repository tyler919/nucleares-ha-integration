"""Config flow — sets up the Nucleares integration via the HA UI."""

import logging

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant

from .const import CONF_API_KEY, CONF_BRIDGE_URL, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_BRIDGE_URL, default="http://192.168.1.x:8765"): str,
        vol.Required(CONF_API_KEY): str,
    }
)


async def _test_connection(hass: HomeAssistant, bridge_url: str, api_key: str) -> str | None:
    """
    Try to reach the bridge /health endpoint.
    Returns an error key string on failure, or None on success.
    """
    url     = bridge_url.rstrip("/") + "/health"
    headers = {"X-API-Key": api_key}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status == 401:
                    return "invalid_auth"
                if resp.status == 403:
                    return "invalid_auth"
                if resp.status != 200:
                    return "cannot_connect"
                return None

    except aiohttp.ClientConnectorError:
        return "cannot_connect"
    except Exception:
        _LOGGER.exception("Unexpected error testing Nucleares bridge connection")
        return "unknown"


class NuclearesConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the initial setup flow for Nucleares."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None):
        errors: dict[str, str] = {}

        if user_input is not None:
            error = await _test_connection(
                self.hass,
                user_input[CONF_BRIDGE_URL],
                user_input[CONF_API_KEY],
            )

            if error:
                errors["base"] = error
            else:
                # Prevent setting up the same bridge twice
                await self.async_set_unique_id(user_input[CONF_BRIDGE_URL].rstrip("/"))
                self._abort_if_unique_id_configured()

                return self.async_create_entry(title="Nucleares", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_SCHEMA,
            errors=errors,
        )
