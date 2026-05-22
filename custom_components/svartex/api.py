import logging
import aiohttp
import async_timeout
from typing import Any, Dict

from .const import GRAPHQL_URL

_LOGGER = logging.getLogger(__name__)

# Shared query string used by both cloud and local API
STATION_DATA_QUERY = """
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
      schedule1CurrentEnabled
      schedule1CurrentValue
      schedule1EnergyEnabled
      schedule1EnergyValue
      schedule2CurrentEnabled
      schedule2CurrentValue
      schedule2EnergyEnabled
      schedule2EnergyValue
    }
  }
}
"""

# Local API uses same query but without isOnline (not available locally)
STATION_DATA_QUERY_LOCAL = """
query StationData {
  stationData {
    designedCurrent
    minCurrent
    stationState
    stationSubState
    isSessionStarted
    isServerConnected
    stationCurrent
    isChargerEnabled
    totalEnergy
    RSSI
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
      schedule1CurrentEnabled
      schedule1CurrentValue
      schedule1EnergyEnabled
      schedule1EnergyValue
      schedule2CurrentEnabled
      schedule2CurrentValue
      schedule2EnergyEnabled
      schedule2EnergyValue
    }
  }
}
"""

UPDATE_MUTATION = """
mutation UpdateStationData($input: StationDataInput!) {
  updateStationData(input: $input)
}
"""


class SvartexAPI:
    """API client for Svartex charger (cloud mode)."""

    def __init__(self, session: aiohttp.ClientSession, email: str, password: str):
        self.session = session
        self.email = email
        self.password = password
        self.token = None
        self.refresh_token = None

    async def authenticate(self):
        """Authenticate: check email, then login."""

        # Step 1 — verify email exists
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

        # Step 2 — login, get tokens
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

        _LOGGER.debug("GET DATA REQUEST (cloud)")
        data = await self._send_graphql_query(STATION_DATA_QUERY)
        return data.get("stationData", {})

    async def update_station_data(self, input_data: Dict[str, Any]) -> bool:
        """Update station data."""
        _LOGGER.debug("UPDATE REQUEST: %s", input_data)
        try:
            result = await self._send_graphql_query(UPDATE_MUTATION, {"input": input_data})
            return bool(result.get("updateStationData", False))
        except Exception as err:
            _LOGGER.error("UPDATE ERROR: %s", err)
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

        try:
            async with async_timeout.timeout(10):
                response = await self.session.post(
                    GRAPHQL_URL,
                    json=payload,
                    headers=headers
                )
                result = await response.json()

                if "errors" in result:
                    _LOGGER.error("GRAPHQL ERRORS: %s", result["errors"])
                    await self.authenticate()
                    raise Exception(f"GraphQL error: {result['errors']}")

                return result["data"]

        except Exception as err:
            _LOGGER.error("GRAPHQL ERROR: %s", err)
            self.token = None
            raise


class SvartexLocalAPI:
    """API client for Svartex charger (local direct access, no auth)."""

    def __init__(self, session: aiohttp.ClientSession, ip_address: str):
        self.session = session
        self.ip_address = ip_address

    @property
    def graphql_url(self):
        return f"http://{self.ip_address}/graphql"

    async def get_station_data(self) -> Dict[str, Any]:
        """Get station data directly from charger."""
        _LOGGER.debug("GET DATA REQUEST (local) -> %s", self.graphql_url)
        data = await self._send_graphql_query(STATION_DATA_QUERY_LOCAL)
        raw = data.get("stationData", {})

        # Map isServerConnected → isOnline so the rest of the integration
        # (binary_sensor etc.) works identically in both modes
        raw.setdefault("isOnline", raw.get("isServerConnected", False))

        return raw

    async def update_station_data(self, input_data: Dict[str, Any]) -> bool:
        """Update station data."""
        _LOGGER.debug("UPDATE REQUEST (local): %s", input_data)
        try:
            result = await self._send_graphql_query(UPDATE_MUTATION, {"input": input_data})
            return bool(result.get("updateStationData", False))
        except Exception as err:
            _LOGGER.error("UPDATE ERROR (local): %s", err)
            return False

    async def _send_graphql_query(self, query: str, variables: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send GraphQL query — no Authorization header needed."""
        payload = {
            "query": query,
            "variables": variables or {}
        }

        try:
            async with async_timeout.timeout(10):
                response = await self.session.post(
                    self.graphql_url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                result = await response.json()

                if "errors" in result:
                    _LOGGER.error("GRAPHQL ERRORS (local): %s", result["errors"])
                    raise Exception(f"GraphQL error: {result['errors']}")

                return result["data"]

        except Exception as err:
            _LOGGER.error("GRAPHQL ERROR (local): %s", err)
            raise
