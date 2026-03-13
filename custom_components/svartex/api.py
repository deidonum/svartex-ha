import logging
import aiohttp
import async_timeout
from typing import Any, Dict

from .const import GRAPHQL_URL

_LOGGER = logging.getLogger(__name__)

class SvartexAPI:
    """API client for Svartex charger."""
    
    def __init__(self, session: aiohttp.ClientSession, station_int: str, password: str):
        self.session = session
        self.station_int = station_int
        self.password = password
        self.token = None

    async def authenticate(self):
        """Authenticate and get token."""
        auth_query = """
        mutation Authenticate($input: AuthInput!) {
          authenticate(input: $input) {
            token
          }
        }
        """
        
        variables = {
            "input": {
                "stationInt": self.station_int,
                "password": self.password
            }
        }
        
        _LOGGER.debug("🔐 AUTH REQUEST: station_int=%s", self.station_int)
        
        async with async_timeout.timeout(10):
            response = await self.session.post(
                GRAPHQL_URL,
                json={
                    "operationName": "Authenticate",
                    "query": auth_query,
                    "variables": variables
                }
            )
            result = await response.json()
            _LOGGER.debug("🔐 AUTH RESPONSE: %s", result)
            
            if "errors" in result:
                raise Exception(f"Authentication failed: {result['errors']}")
            
            self.token = result["data"]["authenticate"]["token"]
            _LOGGER.debug("🔐 AUTH SUCCESS: token received")
            return self.token

    async def get_station_data(self) -> Dict[str, Any]:
        """Get station data."""
        if not self.token:
            await self.authenticate()

        query = """
        query StationData {
          stationData {
            stationState
            stationSubState
            isSessionStarted
            stationCurrent
            isChargerEnabled
            totalEnergy
            RSSI
            isOnline
            minVoltage
            serialInt
            mainFWVersion
            wifiFWVersion
            STA_IP_Addres
            session {
              sessionTime
              sessionEnergy
              sessionCost
            }
            measurements {
              curMeasurement1
              curMeasurement2
              curMeasurement3            
              voltMeasurement1
              voltMeasurement2
              voltMeasurement3
              powerMeasurement
              temperature {
                temperature1
                temperature2
              }
            }
            schedule {
              schedule1Enabled
              schedule2Enabled
              schedule1Start
              schedule1Stop
              schedule2Start
              schedule2Stop
              schedule1CurrentValue
              schedule2CurrentValue
            }
          }
        }
        """
        
        _LOGGER.debug("📡 GET DATA REQUEST")
        data = await self._send_graphql_query(query)
        _LOGGER.debug("📡 GET DATA RESPONSE - schedule1Enabled: %s", 
                     data.get("stationData", {}).get("schedule", {}).get("schedule1Enabled"))
        return data.get("stationData", {})

    async def update_station_data(self, input_data: Dict[str, Any]) -> bool:
        """Update station data (for schedules)."""
        _LOGGER.debug("🔄 UPDATE REQUEST: %s", input_data)
        
        mutation = """
        mutation UpdateStationData($input: StationDataInput!) {
          updateStationData(input: $input)
        }
        """
        
        variables = {
            "input": input_data
        }

        payload = {
            "operationName": "UpdateStationData",
            "query": mutation,
            "variables": variables
        }
        
        _LOGGER.debug("🔄 UPDATE PAYLOAD: %s", payload)
        
        try:
            result = await self._send_graphql_query(mutation, variables)
            _LOGGER.debug("🔄 UPDATE RESPONSE: %s", result)
            
            success = result.get("updateStationData", False)
            _LOGGER.debug("🔄 UPDATE RESULT: %s", success)
            return bool(success)
        except Exception as err:
            _LOGGER.error("🔄 UPDATE ERROR: %s", err)
            return False

    async def _send_graphql_query(self, query: str, variables: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send GraphQL query/mutation."""
        if not self.token:
            await self.authenticate()

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "query": query,
            "variables": variables or {}
        }
        
        _LOGGER.debug("🌐 SENDING GRAPHQL: %s", payload)
        
        try:
            async with async_timeout.timeout(10):
                response = await self.session.post(
                    GRAPHQL_URL,
                    json=payload,
                    headers=headers
                )
                result = await response.json()
                _LOGGER.debug("🌐 GRAPHQL RESPONSE: %s", result)
                
                if "errors" in result:
                    _LOGGER.error("🌐 GRAPHQL ERRORS: %s", result["errors"])
                    # Token might be expired, try to reauthenticate once
                    await self.authenticate()
                    raise Exception(f"GraphQL error: {result['errors']}")
                
                return result["data"]
                
        except Exception as err:
            _LOGGER.error("🌐 GRAPHQL ERROR: %s", err)
            self.token = None  # Reset token on error
            raise