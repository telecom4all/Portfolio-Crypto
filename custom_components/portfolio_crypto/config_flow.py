import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import aiohttp_client
import aiohttp
import async_timeout
import asyncio
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

COINGECKO_API_URL = "https://api.coingecko.com/api/v3/coins/list"

@config_entries.HANDLERS.register(DOMAIN)
class PortfolioCryptoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title=user_input["name"], data={"name": user_input["name"], "cryptos": [], "update_interval": 10, "initialized": False})

        return self.async_show_form(
            step_id="user", data_schema=vol.Schema({"name": str})
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return PortfolioCryptoOptionsFlowHandler(config_entry)

class PortfolioCryptoOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        return await self.async_step_update_interval()

    async def async_step_update_interval(self, user_input=None):
        if user_input is not None:
            update_interval = user_input.get("update_interval", 10)
            self.hass.config_entries.async_update_entry(
                self.config_entry, options={**self.config_entry.options, "update_interval": update_interval}
            )
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        current_interval = self.config_entry.options.get("update_interval", 10)
        return self.async_show_form(
            step_id="update_interval",
            data_schema=vol.Schema({
                vol.Required("update_interval", default=current_interval): vol.In([1, 5, 10, 30])
            })
        )
