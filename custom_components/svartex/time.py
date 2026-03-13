import logging
from homeassistant.components.time import TimeEntity
from homeassistant.core import callback
import datetime

from .const import DOMAIN, get_device_info

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Svartex time entities for schedule control."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    time_entities = [
        SvartexScheduleTime(coordinator, entry, 1, "start"),
        SvartexScheduleTime(coordinator, entry, 1, "stop"), 
        SvartexScheduleTime(coordinator, entry, 2, "start"),
        SvartexScheduleTime(coordinator, entry, 2, "stop"),
    ]
    
    async_add_entities(time_entities)

class SvartexScheduleTime(TimeEntity):
    """Time entity to control schedule start/stop times."""
    
    _attr_has_entity_name = True
    _attr_icon = "mdi:clock"

    def __init__(self, coordinator, entry, schedule_number, time_type):
        self.coordinator = coordinator
        self.entry = entry
        self.schedule_number = schedule_number
        self.time_type = time_type  # "start" or "stop"
        
        self._attr_name = f"Schedule {schedule_number} {time_type.title()}"
        self._attr_unique_id = f"{entry.entry_id}_schedule_{schedule_number}_{time_type}"
        self._attr_device_info = get_device_info(entry)

    @property
    def available(self):
        """Return if entity is available."""
        return self.coordinator.last_update_success

    @property
    def native_value(self) -> datetime.time | None:
        """Convert minutes from midnight to time object."""
        schedule_data = self.coordinator.data.get("schedule", {})
        
        if self.schedule_number == 1:
            minutes = schedule_data.get(f"schedule1{self.time_type.title()}", 0)
        else:
            minutes = schedule_data.get(f"schedule2{self.time_type.title()}", 0)
        
        return self._minutes_to_time(minutes)
    async def async_set_value(self, value: datetime.time):
        """Set time value for schedule."""
        minutes = self._time_to_minutes(value)
        schedule_data = {}
        
        # Отправляем ТОЛЬКО изменяемое поле времени
        if self.schedule_number == 1:
            if self.time_type == "start":
                schedule_data["schedule1Start"] = minutes
            else:
                schedule_data["schedule1Stop"] = minutes
        else:
            if self.time_type == "start":
                schedule_data["schedule2Start"] = minutes
            else:
                schedule_data["schedule2Stop"] = minutes

        _LOGGER.debug("Time data to send: %s", schedule_data)
        await self.coordinator.update_station_data({"schedule": schedule_data})
    def _minutes_to_time(self, minutes: int) -> datetime.time:
        """Convert minutes from midnight to time object."""
        hours = minutes // 60
        mins = minutes % 60
        return datetime.time(hour=hours, minute=mins)

    def _time_to_minutes(self, time_obj: datetime.time) -> int:
        """Convert time object to minutes from midnight."""
        return time_obj.hour * 60 + time_obj.minute

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self._handle_coordinator_update)
        )

    @callback
    def _handle_coordinator_update(self):
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()