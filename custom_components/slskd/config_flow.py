import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import DOMAIN, CONF_HOST, CONF_API_KEY, DEFAULT_SCAN_INTERVAL

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

            # Test connection
            try:
                from slskd_api import SlskdClient
                client = SlskdClient(host=host, api_key=api_key)
                state = await self.hass.async_add_executor_job(client.server.state)
                if not state:
                    errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "cannot_connect"

            if not errors:
                return self.async_create_entry(
                    title=f"slskd ({host})",
                    data={CONF_HOST: host, CONF_API_KEY: api_key},
                )

        data_schema = vol.Schema({
            vol.Required(CONF_HOST, default="http://localhost:5030"): str,
            vol.Required(CONF_API_KEY): str,
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return SlskdOptionsFlowHandler(config_entry)


class SlskdOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for slskd integration."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        import voluptuous as vol

        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema({
            vol.Optional("scan_interval", default=DEFAULT_SCAN_INTERVAL): int
        })

        return self.async_show_form(step_id="init", data_schema=schema)
