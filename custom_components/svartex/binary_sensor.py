import logging
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import callback

from .const import DOMAIN, get_device_info

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Svartex binary sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    binary_sensors = [
        SvartexChargingBinarySensor(coordinator, entry),
        SvartexOnlineBinarySensor(coordinator, entry),
        SvartexSessionActiveBinarySensor(coordinator, entry),
    ]
    
    async_add_entities(binary_sensors)

class SvartexBaseBinarySensor(BinarySensorEntity):
    """Base class for Svartex binary sensors."""
    
    def __init__(self, coordinator, entry, unique_suffix):
        self.coordinator = coordinator
        self.entry = entry
        self._attr_has_entity_name = True
        self._attr_unique_id = f"{entry.entry_id}_{unique_suffix}"  # ← ДОБАВИТЬ unique_id
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

class SvartexChargingBinarySensor(SvartexBaseBinarySensor):
    """Charging status binary sensor."""
    
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "charging")  # ← unique_suffix
        self._attr_name = "Charging"
        self._attr_icon = "mdi:ev-station"

    @property
    def is_on(self):
        """Return true if charging is in progress."""
        return self.coordinator.data.get("isSessionStarted", False)

class SvartexOnlineBinarySensor(SvartexBaseBinarySensor):
    """Online status binary sensor."""
    
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "online")  # ← unique_suffix
        self._attr_name = "Online"
        self._attr_icon = "mdi:cloud-check"

    @property
    def is_on(self):
        """Return true if charger is online."""
        return self.coordinator.data.get("isOnline", False)

class SvartexSessionActiveBinarySensor(SvartexBaseBinarySensor):
    """Session active binary sensor."""
    
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "session_active")  # ← unique_suffix
        self._attr_name = "Session Active"
        self._attr_icon = "mdi:car-electric"

    @property
    def is_on(self):
        """Return true if charging session is active."""
        return self.coordinator.data.get("isSessionStarted", False)