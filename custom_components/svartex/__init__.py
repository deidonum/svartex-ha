import logging
from datetime import timedelta
from typing import Any, Dict

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .api import SvartexAPI

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "binary_sensor", "switch", "number", "time"]

async def async_setup(hass: HomeAssistant, config: Dict[str, Any]) -> bool:
    """Set up the Svartex component."""
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Svartex from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    session = async_get_clientsession(hass)
    api = SvartexAPI(
        session=session,
        station_int=entry.data["station_int"],
        password=entry.data["password"]
    )
    
    coordinator = SvartexCoordinator(hass, api, entry)
    await coordinator.async_config_entry_first_refresh()
    
    hass.data[DOMAIN][entry.entry_id] = coordinator
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok

class SvartexCoordinator(DataUpdateCoordinator):
    """Svartex coordinator."""

    def __init__(self, hass: HomeAssistant, api: SvartexAPI, entry: ConfigEntry):
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=30),
        )
        self.api = api
        self.entry = entry

    async def _async_update_data(self):
        """Fetch data from API."""
        try:
            return await self.api.get_station_data()
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}")
    async def update_station_data(self, input_data: Dict[str, Any]) -> bool:
        """Update schedule data."""
        _LOGGER.debug("Coordinator: Starting schedule update")
        try:
            success = await self.api.update_station_data(input_data)
            _LOGGER.debug("Coordinator: API update result: %s", success)
            
            if success:
                # НЕМЕДЛЕННО обновляем данные после изменения
                _LOGGER.debug("Coordinator: Requesting IMMEDIATE data refresh")
                await self.async_refresh()
            else:
                _LOGGER.error("Coordinator: Failed to update schedule")
            return success
        except Exception as err:
            _LOGGER.error("Coordinator: Error updating schedule: %s", err)
            return False