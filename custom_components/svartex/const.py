"""Constants for the Svartex integration."""

DOMAIN = "svartex"

# GraphQL API endpoint
GRAPHQL_URL = "https://direct-access.ladergy.com/graphql"

# Configuration keys
CONF_EMAIL = "email"
CONF_PASSWORD = "password"

# Station state mappings
STATION_STATES = {
    0: "Unknown",
    1: "Preparing", 
    2: "Available",
    3: "Charging",
    4: "Finished",
    5: "Error"
}

# Default values
DEFAULT_UPDATE_INTERVAL = 30  # seconds
def get_device_info(entry):
    """Get consistent device info for all platforms."""
    return {
        "identifiers": {(DOMAIN, entry.entry_id)},
        "name": "Svartex Charging Station",
        "manufacturer": "Svartex",
        "model": "EV Charger",
    }