import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import (
    UnitOfPower, 
    UnitOfEnergy, 
    UnitOfElectricCurrent, 
    UnitOfElectricPotential,
    UnitOfTemperature,
    EntityCategory
)
from homeassistant.core import callback
from .const import DOMAIN, STATION_STATES, get_device_info

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Svartex sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    sensors = [
        # Основные параметры зарядки
        SvartexPowerSensor(coordinator, entry),
        SvartexStatusSensor(coordinator, entry),
        
        SvartexPhaseSensor(coordinator, entry, "volt", 1),
        SvartexPhaseSensor(coordinator, entry, "volt", 2),
        SvartexPhaseSensor(coordinator, entry, "volt", 3),
        SvartexPhaseSensor(coordinator, entry, "cur", 1),
        SvartexPhaseSensor(coordinator, entry, "cur", 2),
        SvartexPhaseSensor(coordinator, entry, "cur", 3),

        # Энергия и стоимость
        SvartexTotalEnergySensor(coordinator, entry),
        SvartexSessionEnergySensor(coordinator, entry),
        SvartexSessionCostSensor(coordinator, entry),
        
        # Температура
        SvartexTemperatureSensor(coordinator, entry, 1),
        #SvartexTemperatureSensor(coordinator, entry, 2),
        
        # Сигнал WiFi
        SvartexRSSISensor(coordinator, entry),

        SvartexInfoSensor(coordinator, entry, "serialInt", "Serial Number", "mdi:identifier"),
        SvartexInfoSensor(coordinator, entry, "mainFWVersion", "Firmware", "mdi:chip"),
        SvartexInfoSensor(coordinator, entry, "wifiFWVersion", "WiFi Firmware", "mdi:wifi-cog"),
        SvartexInfoSensor(coordinator, entry, "STA_IP_Addres", "IP Address", "mdi:ip-network"),
        
    ]
    
    async_add_entities(sensors)

class SvartexBaseSensor(SensorEntity):
    """Base class for Svartex sensors."""
    
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

class SvartexPowerSensor(SvartexBaseSensor):
    """Power sensor."""
    
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "power")  # ← unique_suffix
        self._attr_name = "Power"
        self._attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
        self._attr_device_class = "power"

    @property
    def native_value(self):
        """Return current power consumption."""
        return self.coordinator.data.get("measurements", {}).get("powerMeasurement")

class SvartexStatusSensor(SvartexBaseSensor):
    """Status sensor."""
    
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "status")  # ← unique_suffix
        self._attr_name = "Status"
        self._attr_icon = "mdi:ev-station"

    @property
    def native_value(self):
        """Return current status."""
        state = self.coordinator.data.get("stationState")
        return STATION_STATES.get(state, "Unknown")

class SvartexTotalEnergySensor(SvartexBaseSensor):
    """Total energy sensor."""
    
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "total_energy")  # ← unique_suffix
        self._attr_name = "Total Energy"
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_device_class = "energy"
        self._attr_state_class = "total_increasing"

    @property
    def native_value(self):
        """Return total energy delivered."""
        return round(self.coordinator.data.get("totalEnergy", 0), 2)

class SvartexSessionEnergySensor(SvartexBaseSensor):
    """Session energy sensor."""
    
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "session_energy")  # ← unique_suffix
        self._attr_name = "Session Energy"
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_device_class = "energy"

    @property
    def native_value(self):
        """Return current session energy."""
        return self.coordinator.data.get("session", {}).get("sessionEnergy")

class SvartexSessionCostSensor(SvartexBaseSensor):
    """Session cost sensor."""
    
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "session_cost")  # ← unique_suffix
        self._attr_name = "Session Cost"
        self._attr_icon = "mdi:cash"
        self._attr_native_unit_of_measurement = "UAH"

    @property
    def native_value(self):
        """Return current session cost."""
        return self.coordinator.data.get("session", {}).get("sessionCost")

class SvartexTemperatureSensor(SvartexBaseSensor):
    """Temperature sensor."""
    
    def __init__(self, coordinator, entry, sensor_num):
        super().__init__(coordinator, entry, f"temperature_{sensor_num}")  # ← unique_suffix
        self.sensor_num = sensor_num
        self._attr_name = f"Temperature {sensor_num}"
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_device_class = "temperature"

    @property
    def native_value(self):
        """Return temperature value."""
        temp_data = self.coordinator.data.get("measurements", {}).get("temperature", {})
        return temp_data.get(f"temperature{self.sensor_num}")

class SvartexRSSISensor(SvartexBaseSensor):
    """WiFi signal sensor."""
    
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "wifi_signal")  # ← unique_suffix
        self._attr_name = "WiFi Signal"
        self._attr_native_unit_of_measurement = "dBm"
        self._attr_icon = "mdi:wifi"

    @property
    def native_value(self):
        """Return WiFi signal strength."""
        return self.coordinator.data.get("RSSI")
    
class SvartexPhaseSensor(SvartexBaseSensor):
    """Phase current/voltage sensor."""
    
    def __init__(self, coordinator, entry, measurement_type, phase_num):
        super().__init__(coordinator, entry, f"{measurement_type}_phase_{phase_num}")
        self.measurement_type = measurement_type
        self.phase_num = phase_num
        
        if measurement_type == "cur":
            self._attr_name = f"Current L{phase_num}"
            self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
            self._attr_device_class = "current"
        else:
            self._attr_name = f"Voltage L{phase_num}"
            self._attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
            self._attr_device_class = "voltage"

    @property
    def native_value(self):
        measurements = self.coordinator.data.get("measurements", {})
        if self.measurement_type == "cur":
            return measurements.get(f"curMeasurement{self.phase_num}")
        else:
            return measurements.get(f"voltMeasurement{self.phase_num}")
        
class SvartexInfoSensor(SvartexBaseSensor):
    """Informational sensor for device details."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, entry, field, name, icon):
        super().__init__(coordinator, entry, field.lower())
        self.field = field
        self._attr_name = name
        self._attr_icon = icon

    @property
    def native_value(self):
        return self.coordinator.data.get(self.field)