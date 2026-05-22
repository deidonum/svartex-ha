"""Constants for the Svartex integration."""

DOMAIN = "svartex"

# GraphQL API endpoints
GRAPHQL_URL = "https://direct-access.ladergy.com/graphql"

# Configuration keys
CONF_EMAIL = "email"
CONF_PASSWORD = "password"
CONF_IP_ADDRESS = "ip_address"
CONF_CONNECTION_MODE = "connection_mode"

# Connection modes
MODE_ONLINE = "online"
MODE_LOCAL = "local"

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
DEFAULT_UPDATE_INTERVAL = 30       # seconds for cloud
DEFAULT_UPDATE_INTERVAL_LOCAL = 5  # seconds for local

def get_device_info(entry):
    """Get consistent device info for all platforms."""
    return {
        "identifiers": {(DOMAIN, entry.entry_id)},
        "name": "Svartex Charging Station",
        "manufacturer": "Svartex",
        "model": "EV Charger",
    }
