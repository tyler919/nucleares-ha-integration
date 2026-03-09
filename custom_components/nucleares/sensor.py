"""Sensor platform for Nucleares.

Entities are created dynamically based on whatever variables the bridge
is currently polling. Known variables get proper metadata (unit, device class,
icon). Unknown variables get a generic fallback so they still show up.
"""

from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import NuclearesCoordinator

_LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Metadata for known variables
# Each entry: friendly_name, unit, device_class, state_class, icon
# ---------------------------------------------------------------------------
_KNOWN: dict[str, tuple] = {
    # Core
    "CORE_TEMP":                  ("Core Temperature",          UnitOfTemperature.CELSIUS,    SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, None),
    "CORE_TEMP_MAX":              ("Core Max Temperature",       UnitOfTemperature.CELSIUS,    SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, None),
    "CORE_TEMP_MIN":              ("Core Min Temperature",       UnitOfTemperature.CELSIUS,    SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, None),
    "CORE_TEMP_OPERATIVE":        ("Core Operative Temperature", UnitOfTemperature.CELSIUS,    SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, None),
    "CORE_TEMP_RESIDUAL":         ("Core Residual Temperature",  UnitOfTemperature.CELSIUS,    SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, None),
    "CORE_PRESSURE":              ("Core Pressure",              "bar",                        SensorDeviceClass.PRESSURE,    SensorStateClass.MEASUREMENT, None),
    "CORE_PRESSURE_MAX":          ("Core Max Pressure",          "bar",                        SensorDeviceClass.PRESSURE,    SensorStateClass.MEASUREMENT, None),
    "CORE_PRESSURE_OPERATIVE":    ("Core Operative Pressure",    "bar",                        SensorDeviceClass.PRESSURE,    SensorStateClass.MEASUREMENT, None),
    "CORE_INTEGRITY":             ("Core Integrity",             "%",                          None,                          SensorStateClass.MEASUREMENT, "mdi:shield-check"),
    "CORE_WEAR":                  ("Core Wear",                  "%",                          None,                          SensorStateClass.MEASUREMENT, "mdi:wrench"),
    "CORE_STATE":                 ("Core State",                 None,                         None,                          None,                         "mdi:atom"),
    "CORE_STATE_CRITICALITY":     ("Criticality State",          None,                         None,                          None,                         "mdi:radioactive"),
    "CORE_CRITICAL_MASS_REACHED": ("Critical Mass Reached",      None,                         None,                          None,                         "mdi:alert-circle"),
    "CORE_CRITICAL_MASS_REACHED_COUNTER": ("Critical Mass Counter", None,                      None,                          SensorStateClass.TOTAL,       "mdi:counter"),
    "CORE_IMMINENT_FUSION":       ("Imminent Fusion Warning",    None,                         None,                          None,                         "mdi:fire-alert"),
    "CORE_READY_FOR_START":       ("Core Ready for Start",       None,                         None,                          None,                         "mdi:check-circle"),
    "CORE_STEAM_PRESENT":         ("Steam Present",              None,                         None,                          None,                         "mdi:cloud"),
    "CORE_HIGH_STEAM_PRESENT":    ("High Steam Present",         None,                         None,                          None,                         "mdi:cloud-alert"),

    # Control Rods
    "RODS_STATUS":          ("Rod Status",           None,  None, None,                         "mdi:format-list-bulleted"),
    "RODS_POS_ACTUAL":      ("Rod Position (Actual)","%",   None, SensorStateClass.MEASUREMENT, "mdi:arrow-collapse-down"),
    "RODS_POS_ORDERED":     ("Rod Position (Ordered)","%",  None, SensorStateClass.MEASUREMENT, "mdi:arrow-expand-down"),
    "RODS_POS_REACHED":     ("Rod Position Reached", None,  None, None,                         "mdi:check"),
    "RODS_TEMPERATURE":     ("Rod Temperature",      UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, None),
    "RODS_MAX_TEMPERATURE": ("Rod Max Temperature",  UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, None),
    "RODS_MOVEMENT_SPEED":  ("Rod Movement Speed",   None,  None, SensorStateClass.MEASUREMENT, "mdi:speedometer"),
    "RODS_DEFORMED":        ("Rods Deformed",        None,  None, None,                         "mdi:alert"),
    "RODS_QUANTITY":        ("Rod Quantity",          None,  None, SensorStateClass.MEASUREMENT, "mdi:counter"),
    "RODS_ALIGNED":         ("Rods Aligned",          None,  None, None,                         "mdi:align-vertical-center"),

    # Coolant — Core
    "COOLANT_CORE_STATE":                ("Coolant State",             None,  None,                       None,                         "mdi:water"),
    "COOLANT_CORE_PRESSURE":             ("Coolant Pressure",           "bar", SensorDeviceClass.PRESSURE, SensorStateClass.MEASUREMENT, None),
    "COOLANT_CORE_MAX_PRESSURE":         ("Coolant Max Pressure",       "bar", SensorDeviceClass.PRESSURE, SensorStateClass.MEASUREMENT, None),
    "COOLANT_CORE_VESSEL_TEMPERATURE":   ("Coolant Vessel Temperature", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, None),
    "COOLANT_CORE_QUANTITY_IN_VESSEL":   ("Coolant Quantity in Vessel", None,  None,                       SensorStateClass.MEASUREMENT, "mdi:water-percent"),
    "COOLANT_CORE_PRIMARY_LOOP_LEVEL":   ("Primary Loop Level",         "%",   None,                       SensorStateClass.MEASUREMENT, "mdi:water"),
    "COOLANT_CORE_FLOW_SPEED":           ("Coolant Flow Speed",         None,  None,                       SensorStateClass.MEASUREMENT, "mdi:pump"),
    "COOLANT_CORE_FLOW_ORDERED_SPEED":   ("Coolant Ordered Flow Speed", None,  None,                       SensorStateClass.MEASUREMENT, "mdi:pump"),
    "COOLANT_CORE_FLOW_REACHED_SPEED":   ("Coolant Reached Flow Speed", None,  None,                       SensorStateClass.MEASUREMENT, "mdi:pump-off"),

    # Time
    "TIME":       ("Game Time",      None, None, None, "mdi:clock-outline"),
    "TIME_STAMP": ("Game Timestamp", None, None, None, "mdi:clock-digital"),
}

# Generate pump entries dynamically for pumps 0-2
for _i in range(3):
    _n = _i + 1
    _KNOWN[f"COOLANT_CORE_CIRCULATION_PUMP_{_i}_STATUS"]        = (f"Circulation Pump {_n} Status",        None,  None, None,                         "mdi:pump")
    _KNOWN[f"COOLANT_CORE_CIRCULATION_PUMP_{_i}_DRY_STATUS"]    = (f"Circulation Pump {_n} Dry Status",    None,  None, None,                         "mdi:water-off")
    _KNOWN[f"COOLANT_CORE_CIRCULATION_PUMP_{_i}_OVERLOAD_STATUS"]=(f"Circulation Pump {_n} Overload",      None,  None, None,                         "mdi:alert")
    _KNOWN[f"COOLANT_CORE_CIRCULATION_PUMP_{_i}_SPEED"]         = (f"Circulation Pump {_n} Speed",         "%",   None, SensorStateClass.MEASUREMENT, "mdi:speedometer")
    _KNOWN[f"COOLANT_CORE_CIRCULATION_PUMP_{_i}_ORDERED_SPEED"] = (f"Circulation Pump {_n} Ordered Speed", "%",   None, SensorStateClass.MEASUREMENT, "mdi:speedometer-slow")

# Generate turbine entries dynamically for turbines 0-2
for _i in range(3):
    _n = _i + 1
    _KNOWN[f"STEAM_TURBINE_{_i}_RPM"]            = (f"Turbine {_n} RPM",         "RPM",                     None,                          SensorStateClass.MEASUREMENT, "mdi:turbine")
    _KNOWN[f"STEAM_TURBINE_{_i}_TEMPERATURE"]    = (f"Turbine {_n} Temperature", UnitOfTemperature.CELSIUS,  SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, None)
    _KNOWN[f"STEAM_TURBINE_{_i}_PRESSURE"]       = (f"Turbine {_n} Pressure",    "bar",                     SensorDeviceClass.PRESSURE,    SensorStateClass.MEASUREMENT, None)
    _KNOWN[f"STEAM_TURBINE_{_i}_BYPASS_ORDERED"] = (f"Turbine {_n} Bypass",      "%",                       None,                          SensorStateClass.MEASUREMENT, "mdi:valve")

# Generate generator entries dynamically for generators 0-2
for _i in range(3):
    _n = _i + 1
    _KNOWN[f"GENERATOR_{_i}_KW"]      = (f"Generator {_n} Power",     UnitOfPower.KILO_WATT,          SensorDeviceClass.POWER,     SensorStateClass.MEASUREMENT, None)
    _KNOWN[f"GENERATOR_{_i}_V"]       = (f"Generator {_n} Voltage",   UnitOfElectricPotential.VOLT,   SensorDeviceClass.VOLTAGE,   SensorStateClass.MEASUREMENT, None)
    _KNOWN[f"GENERATOR_{_i}_A"]       = (f"Generator {_n} Current",   UnitOfElectricCurrent.AMPERE,   SensorDeviceClass.CURRENT,   SensorStateClass.MEASUREMENT, None)
    _KNOWN[f"GENERATOR_{_i}_HERTZ"]   = (f"Generator {_n} Frequency", UnitOfFrequency.HERTZ,          SensorDeviceClass.FREQUENCY, SensorStateClass.MEASUREMENT, None)
    _KNOWN[f"GENERATOR_{_i}_BREAKER"] = (f"Generator {_n} Breaker",   None,                           None,                        None,                         "mdi:electric-switch")


# ---------------------------------------------------------------------------
# Platform setup
# ---------------------------------------------------------------------------
async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: NuclearesCoordinator = hass.data[DOMAIN][entry.entry_id]

    sensors_data: dict = coordinator.data.get("sensors", {}) if coordinator.data else {}

    entities = [
        NuclearesSensor(coordinator, entry, variable)
        for variable in sensors_data
    ]

    _LOGGER.info("Creating %d Nucleares sensor entities", len(entities))
    async_add_entities(entities)


# ---------------------------------------------------------------------------
# Entity
# ---------------------------------------------------------------------------
class NuclearesSensor(CoordinatorEntity[NuclearesCoordinator], SensorEntity):
    """A single sensor entity backed by a Nucleares variable."""

    def __init__(
        self,
        coordinator: NuclearesCoordinator,
        entry: ConfigEntry,
        variable: str,
    ) -> None:
        super().__init__(coordinator)

        self._variable = variable
        self._entry_id = entry.entry_id

        meta = _KNOWN.get(variable)
        if meta:
            friendly, unit, device_class, state_class, icon = meta
        else:
            # Generic fallback for variables not in the known list
            friendly    = variable.replace("_", " ").title()
            unit        = None
            device_class = None
            state_class = SensorStateClass.MEASUREMENT
            icon        = "mdi:gauge"

        self._attr_name                       = f"Nucleares {friendly}"
        self._attr_unique_id                  = f"nucleares_{entry.entry_id}_{variable.lower()}"
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class               = device_class
        self._attr_state_class                = state_class
        self._attr_icon                       = icon

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Nucleares Reactor",
            manufacturer="Nucleares",
            model="Nuclear Power Plant Simulator",
        )

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        sensor_data = self.coordinator.data.get("sensors", {}).get(self._variable)
        if sensor_data is None:
            return None
        return sensor_data.get("value")

    @property
    def available(self) -> bool:
        """Unavailable when bridge is down or game is not running."""
        if not self.coordinator.last_update_success:
            return False
        if not self.coordinator.data:
            return False
        return self.coordinator.data.get("game_connected", False)

    @property
    def extra_state_attributes(self) -> dict:
        if not self.coordinator.data:
            return {}
        sensor_data = self.coordinator.data.get("sensors", {}).get(self._variable, {})
        return {
            "variable":  self._variable,
            "value_str": sensor_data.get("value_str"),
        }
