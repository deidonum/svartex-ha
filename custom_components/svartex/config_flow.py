import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
import aiohttp
import async_timeout

from .const import DOMAIN, CONF_STATION_INT, CONF_PASSWORD, GRAPHQL_URL

class SvartexConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Svartex EV Charger."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            try:
                # Проверяем подключение с введенными данными
                valid = await self._test_connection(
                    user_input[CONF_STATION_INT],
                    user_input[CONF_PASSWORD]
                )
                if valid:
                    # Проверяем нет ли уже такой станции
                    await self.async_set_unique_id(user_input[CONF_STATION_INT])
                    self._abort_if_unique_id_configured()

                    return self.async_create_entry(
                        title=f"Svartex {user_input[CONF_STATION_INT]}",
                        data=user_input
                    )
                else:
                    errors["base"] = "cannot_connect"
            except aiohttp.ClientError:
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"

        data_schema = vol.Schema({
            vol.Required(CONF_STATION_INT): str,
            vol.Required(CONF_PASSWORD): str,
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "name": "SVRTX"
            }
        )

    async def _test_connection(self, station_int: str, password: str) -> bool:
        """Test if we can authenticate with the station."""
        auth_query = """
        mutation Authenticate($input: AuthInput!) {
          authenticate(input: $input) {
            token
          }
        }
        """
        
        variables = {
            "input": {
                "stationInt": station_int,
                "password": password
            }
        }
        
        try:
            async with async_timeout.timeout(10):
                async with aiohttp.ClientSession() as session:
                    response = await session.post(
                        GRAPHQL_URL,
                        json={
                            "operationName": "Authenticate",
                            "query": auth_query,
                            "variables": variables
                        }
                    )
                    result = await response.json()
                    
                    if "errors" in result:
                        return False
                    
                    return "data" in result and "authenticate" in result["data"]
        except Exception:
            return False