import logging
import aiohttp
import async_timeout
from typing import Any, Dict

from .const import GRAPHQL_URL

_LOGGER = logging.getLogger(__name__)

class SvartexAPI:
    """API client for Svartex charger."""
    
    def __init__(self, session: aiohttp.ClientSession, email: str, password: str):
        self.session = session
        self.email = email
        self.password = password
        self.token = None
        self.refresh_token = None

    async def authenticate(self):
        """Authenticate: check email, then login."""
        
        # Шаг 1 — проверка email (опционально, можно пропустить,
        # но оставим для соответствия реальному флоу)
        check_query = """
        query GetUserByEmail($email: String!) {
        userByEmail(email: $email) {
            id
            isUserVerified
        }
        }
        """
        async with async_timeout.timeout(10):
            response = await self.session.post(
                GRAPHQL_URL,
                json={
                    "operationName": "GetUserByEmail",
                    "query": check_query,
                    "variables": {"email": self.email}
                }
            )
            result = await response.json()
            if "errors" in result or not result.get("data", {}).get("userByEmail"):
                raise Exception(f"User not found for email: {self.email}")

        # Шаг 2 — логин, получаем токены
        login_mutation = """
        mutation Login($input: LoginInput!) {
        login(input: $input) {
            accessToken
            refreshToken
        }
        }
        """
        async with async_timeout.timeout(10):
            response = await self.session.post(
                GRAPHQL_URL,
                json={
                    "operationName": "Login",
                    "query": login_mutation,
                    "variables": {
                        "input": {
                            "email": self.email,
                            "password": self.password
                        }
                    }
                }
            )
            result = await response.json()
            if "errors" in result:
                raise Exception(f"Login failed: {result['errors']}")
            
            auth_data = result["data"]["login"]
            self.token = auth_data["accessToken"]
            self.refresh_token = auth_data["refreshToken"]
            _LOGGER.debug("AUTH SUCCESS: tokens received")
            return self.token

    async def get_station_data(self) -> Dict[str, Any]:
        """Get station data."""
        if not self.token:
            await self.authenticate()

        query = """
        query StationData {
          stationData {
            designedCurrent
            minCurrent
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