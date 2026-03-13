import logging
from homeassistant.components.number import NumberEntity
from homeassistant.core import callback
from homeassistant.const import UnitOfElectricCurrent,  UnitOfElectricPotential, EntityCategory

from .const import DOMAIN, get_device_info

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Svartex number entities for current control."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    numbers = [
        SvartexCurrentNumber(coordinator, entry, 1),
        SvartexCurrentNumber(coordinator, entry, 2),
        SvartexStationCurrentNumber(coordinator, entry),
        #SvartexMinVoltageNumber(coordinator, entry), # Temporary removal of voltage control until developers confirmation
    ]
    
    async_add_entities(numbers)


class SvartexBaseNumber(NumberEntity):
    """Base class for all Svartex number entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, unique_suffix):
        self.coordinator = coordinator
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{unique_suffix}"
        self._attr_device_info = get_device_info(entry)

    @property
    def available(self):
        """Return if entity is available."""
        return self.coordinator.last_update_success

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self._handle_coordinator_update)
        )

    @callback
    def _handle_coordinator_update(self):
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()


class SvartexCurrentNumber(SvartexBaseNumber):
    """Number entity to control charging current for schedules."""

    _attr_icon = "mdi:current-ac"
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE

    def __init__(self, coordinator, entry, schedule_number):
        super().__init__(coordinator, entry, f"schedule_{schedule_number}_current")
        self.schedule_number = schedule_number

        self._attr_name = f"Schedule {schedule_number} Current"
        self._attr_native_min_value = coordinator.data.get("minCurrent", 6)
        self._attr_native_max_value = coordinator.data.get("designedCurrent", 32)
        self._attr_native_step = 1

    @property
    def native_value(self):
        """Return current value for the schedule."""
        schedule_data = self.coordinator.data.get("schedule", {})
        if self.schedule_number == 1:
            return schedule_data.get("schedule1CurrentValue", 0)
        else:
            return schedule_data.get("schedule2CurrentValue", 0)

    async def async_set_native_value(self, value):
        """Set new current value for the schedule."""
        schedule_data = {}
        if self.schedule_number == 1:
            schedule_data["schedule1CurrentValue"] = int(value)
        else:
            schedule_data["schedule2CurrentValue"] = int(value)

        _LOGGER.debug("Current data to send: %s", schedule_data)
        await self.coordinator.update_station_data({"schedule": schedule_data})


class SvartexStationCurrentNumber(SvartexBaseNumber):
    """Number entity to control station charging current."""

    _attr_icon = "mdi:current-ac"
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "station_current")

        self._attr_name = "Charging Current"
        self._attr_native_min_value = coordinator.data.get("minCurrent", 6)
        self._attr_native_max_value = coordinator.data.get("designedCurrent", 32)
        self._attr_native_step = 1

    @property
    def native_value(self):
        """Return current station charging current."""
        return self.coordinator.data.get("stationCurrent")

    async def async_set_native_value(self, value):
        """Set new station charging current."""
        await self.coordinator.update_station_data({"stationCurrent": int(value)})

class SvartexMinVoltageNumber(SvartexBaseNumber):
    """Number entity to control minimum voltage threshold."""

    _attr_icon = "mdi:lightning-bolt"
    _attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
    _attr_entity_registry_enabled_default = False
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "min_voltage")
        self._attr_name = "Low Voltage Limit (⚠️Experimental⚠️)"
        self._attr_native_min_value = 160
        self._attr_native_max_value = 230
        self._attr_native_step = 1

    @property
    def native_value(self):
        return self.coordinator.data.get("minVoltage")

    async def async_set_native_value(self, value):
        await self.coordinator.update_station_data({"minVoltage": int(value)})