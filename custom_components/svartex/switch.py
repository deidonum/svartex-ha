import logging
from homeassistant.components.switch import SwitchEntity
from homeassistant.core import callback

from .const import DOMAIN, get_device_info

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Svartex schedule switches."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    switches = [
        SvartexScheduleSwitch(coordinator, entry, 1),
        SvartexScheduleSwitch(coordinator, entry, 2),
    ]

    async_add_entities(switches)


class SvartexBaseSwitch(SwitchEntity):
    """Base class for all Svartex switch entities."""

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


class SvartexScheduleSwitch(SvartexBaseSwitch):
    """Switch to enable/disable charging schedule."""

    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator, entry, schedule_number):
        super().__init__(coordinator, entry, f"schedule_{schedule_number}")
        self.schedule_number = schedule_number
        self._attr_name = f"Schedule {schedule_number}"

    @property
    def is_on(self):
        """Return true if schedule is enabled."""
        schedule_data = self.coordinator.data.get("schedule", {})
        if self.schedule_number == 1:
            return schedule_data.get("schedule1Enabled", False)
        else:
            return schedule_data.get("schedule2Enabled", False)

    async def async_turn_on(self, **kwargs):
        """Enable the schedule."""
        await self._update_schedule_state(True)

    async def async_turn_off(self, **kwargs):
        """Disable the schedule."""
        await self._update_schedule_state(False)

    async def _update_schedule_state(self, enabled):
        """Update schedule state via API."""
        schedule_data = {}
        if self.schedule_number == 1:
            schedule_data["schedule1Enabled"] = enabled
        else:
            schedule_data["schedule2Enabled"] = enabled

        try:
            success = await self.coordinator.update_station_data({"schedule": schedule_data})
            if success:
                self._attr_is_on = enabled
                self.async_write_ha_state()
            else:
                _LOGGER.error("Failed to update schedule %s", self.schedule_number)
        except Exception as err:
            _LOGGER.error("Error updating schedule %s: %s", self.schedule_number, err)