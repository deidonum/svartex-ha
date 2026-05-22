import voluptuous as vol
from homeassistant import config_entries
import aiohttp
import async_timeout
import logging
from .api import STATION_DATA_QUERY_LOCAL

_LOGGER = logging.getLogger(__name__)

from .const import (
    DOMAIN,
    CONF_EMAIL, CONF_PASSWORD, CONF_IP_ADDRESS, CONF_CONNECTION_MODE,
    MODE_ONLINE, MODE_LOCAL,
    GRAPHQL_URL
)


class SvartexConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Svartex EV Charger."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Step 1 — choose connection mode."""
        if user_input is not None:
            if user_input[CONF_CONNECTION_MODE] == MODE_LOCAL:
                return await self.async_step_local()
            else:
                return await self.async_step_online()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_CONNECTION_MODE, default=MODE_ONLINE): vol.In({
                    MODE_ONLINE: "☁️ Online (cloud)",
                    MODE_LOCAL: "🏠 Local (IP address)",
                })
            })
        )

    async def async_step_online(self, user_input=None):
        """Step 2a — Online mode: email + password."""
        errors = {}

        if user_input is not None:
            valid = await self._test_online(
                user_input[CONF_EMAIL],
                user_input[CONF_PASSWORD]
            )
            if valid:
                await self.async_set_unique_id(user_input[CONF_EMAIL])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Svartex ({user_input[CONF_EMAIL]})",
                    data={
                        CONF_CONNECTION_MODE: MODE_ONLINE,
                        **user_input
                    }
                )
            errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="online",
            data_schema=vol.Schema({
                vol.Required(CONF_EMAIL): str,
                vol.Required(CONF_PASSWORD): str,
            }),
            errors=errors
        )

    async def async_step_local(self, user_input=None):
        """Step 2b — Local mode: IP address only."""
        errors = {}

        if user_input is not None:
            valid = await self._test_local(user_input[CONF_IP_ADDRESS])
            if valid:
                await self.async_set_unique_id(user_input[CONF_IP_ADDRESS])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Svartex @ {user_input[CONF_IP_ADDRESS]}",
                    data={
                        CONF_CONNECTION_MODE: MODE_LOCAL,
                        **user_input
                    }
                )
            errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="local",
            data_schema=vol.Schema({
                vol.Required(CONF_IP_ADDRESS): str,
            }),
            errors=errors
        )

    # ------------------------------------------------------------------
    # Connection tests
    # ------------------------------------------------------------------

    async def _test_online(self, email: str, password: str) -> bool:
        """Test cloud credentials."""
        login_mutation = """
        mutation Login($input: LoginInput!) {
          login(input: $input) {
            accessToken
            refreshToken
          }
        }
        """
        try:
            async with async_timeout.timeout(10):
                async with aiohttp.ClientSession() as session:
                    response = await session.post(
                        GRAPHQL_URL,
                        json={
                            "operationName": "Login",
                            "query": login_mutation,
                            "variables": {
                                "input": {
                                    "email": email,
                                    "password": password
                                }
                            }
                        }
                    )
                    result = await response.json()
                    if "errors" in result:
                        return False
                    return bool(
                        result.get("data", {}).get("login", {}).get("accessToken")
                    )
        except Exception:
            return False

    async def _test_local(self, ip_address: str) -> bool:
        """Test local connection by fetching full stationData."""
        try:
            async with async_timeout.timeout(5):
                async with aiohttp.ClientSession() as session:
                    response = await session.post(
                        f"http://{ip_address}/graphql",
                        json={
                            "operationName": "StationData",
                            "variables": {},
                            "query": STATION_DATA_QUERY_LOCAL  # Используем унифицированный запрос
                        },
                        headers={"Content-Type": "application/json"}
                    )
                    
                    response.raise_for_status()
                    result = await response.json()
                    
                    # Если вернулся serialInt, значит весь большой парсинг прошел успешно
                    return bool(
                        result.get("data", {}).get("stationData", {}).get("serialInt")
                    )
        except Exception as err:
            _LOGGER.error("Local connection test failed for %s: %s", ip_address, err)
            return False
