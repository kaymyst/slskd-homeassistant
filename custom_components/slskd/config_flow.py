import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    DOMAIN,
    CONF_HOST,
    CONF_API_KEY,
    CONF_API_KEY_ROLE,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    API_KEY_ROLES,
    ROLE_READONLY,
    ROLE_READWRITE,
)


def _check_key(host: str, api_key: str, role: str) -> str | None:
    """Return an error key if the server can't be reached or the key lacks the chosen role."""
    from slskd_api import SlskdClient
    from .helpers import detect_role, get_server_state

    try:
        client = SlskdClient(host=host, api_key=api_key)
        if not get_server_state(client):
            return "cannot_connect"
        if role == ROLE_READWRITE and detect_role(client) != ROLE_READWRITE:
            return "readonly_key"
    except Exception:
        return "cannot_connect"
    return None


class SlskdConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for slskd."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            api_key = user_input[CONF_API_KEY]
            role = user_input[CONF_API_KEY_ROLE]

            # Test connection and key permissions
            error = await self.hass.async_add_executor_job(_check_key, host, api_key, role)
            if error:
                errors["base"] = error

            if not errors:
                return self.async_create_entry(
                    title=f"slskd ({host})",
                    data={CONF_HOST: host, CONF_API_KEY: api_key, CONF_API_KEY_ROLE: role},
                )

        data_schema = vol.Schema({
            vol.Required(CONF_HOST, default="http://localhost:5030"): str,
            vol.Required(CONF_API_KEY): str,
            vol.Required(CONF_API_KEY_ROLE, default=ROLE_READONLY): vol.In(API_KEY_ROLES),
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return SlskdOptionsFlowHandler()


class SlskdOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for slskd integration."""

    async def async_step_init(self, user_input=None):
        from .helpers import get_role

        entry = self.config_entry
        errors = {}

        if user_input is not None:
            # Only switching to readwrite needs the server to confirm the key's permissions
            error = None
            if user_input[CONF_API_KEY_ROLE] == ROLE_READWRITE:
                error = await self.hass.async_add_executor_job(
                    _check_key,
                    entry.data[CONF_HOST],
                    entry.data[CONF_API_KEY],
                    ROLE_READWRITE,
                )
            if error:
                errors["base"] = error
            else:
                return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema({
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ): int,
            vol.Required(
                CONF_API_KEY_ROLE, default=get_role(entry) or ROLE_READONLY
            ): vol.In(API_KEY_ROLES),
        })

        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
