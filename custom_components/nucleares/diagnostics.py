"""Diagnostics support for the Nucleares integration.

Accessible in HA via:
  Settings → Integrations → Nucleares → ··· → Download Diagnostics

The API key is automatically redacted from the output.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_API_KEY, DOMAIN
from .coordinator import NuclearesCoordinator

# Fields that must never appear in a diagnostics dump
_REDACT = {CONF_API_KEY}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: NuclearesCoordinator = hass.data[DOMAIN][entry.entry_id]

    data = coordinator.data or {}
    sensors = data.get("sensors", {})

    # Summarise null vs live sensors so the dump stays readable
    null_vars  = [k for k, v in sensors.items() if v.get("value") is None]
    live_count = len(sensors) - len(null_vars)

    return {
        "config_entry": async_redact_data(dict(entry.data), _REDACT),
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "last_exception":      str(coordinator.last_exception)
                                   if coordinator.last_exception else None,
            "game_connected":      data.get("game_connected"),
            "last_poll":           data.get("last_poll"),
            "poll_count":          data.get("poll_count"),
            "error_count":         data.get("error_count"),
            "total_variables":     len(sensors),
            "live_variables":      live_count,
            "null_variables":      null_vars,
        },
        "sensors": sensors,
    }
