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
            return self.async_create_entry(title=user_input["name"], data={"name": user_input["name"], "cryptos": []})

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
        return self.async_show_menu(
            step_id="menu",
            menu_options=["add_crypto", "finish"]
        )

    async def async_step_menu(self, user_input=None):
        if user_input == "add_crypto":
            return await self.async_step_add_crypto()
        elif user_input == "finish":
            return self.async_create_entry(title="", data={})

    async def async_step_add_crypto(self, user_input=None):
        if user_input is not None:
            crypto_name = user_input["crypto_name"]
            crypto_id = await self.fetch_crypto_id(crypto_name)
            if not crypto_id:
                matches = await self.search_crypto(crypto_name)
                return self.async_show_form(
                    step_id="select_crypto",
                    data_schema=vol.Schema({
                        vol.Required("crypto_id"): vol.In({c['id']: c['name'] for c in matches})
                    })
                )
            else:
                cryptos = self.config_entry.data.get("cryptos", [])
                cryptos.append({"name": crypto_name, "id": crypto_id})
                self.hass.config_entries.async_update_entry(self.config_entry, data={**self.config_entry.data, "cryptos": cryptos})
                return self.async_show_menu(
                    step_id="menu",
                    menu_options=["add_crypto", "finish"]
                )

        return self.async_show_form(
            step_id="add_crypto", data_schema=vol.Schema({"crypto_name": str})
        )

    async def async_step_select_crypto(self, user_input=None):
        if user_input is not None:
            cryptos = self.config_entry.data.get("cryptos", [])
            cryptos.append({"name": user_input["crypto_id"], "id": user_input["crypto_id"]})
            self.hass.config_entries.async_update_entry(self.config_entry, data={**self.config_entry.data, "cryptos": cryptos})
            return self.async_show_menu(
                step_id="menu",
                menu_options=["add_crypto", "finish"]
            )

    async def fetch_crypto_id(self, crypto_name):
        async with aiohttp.ClientSession() as session:
            try:
                with async_timeout.timeout(10):
                    async with session.get(COINGECKO_API_URL) as response:
                        result = await response.json()
                        for coin in result:
                            if coin['name'].lower() == crypto_name.lower():
                                return coin['id']
            except (aiohttp.ClientError, asyncio.TimeoutError):
                _LOGGER.error("Error fetching CoinGecko data")
        return None

    async def search_crypto(self, crypto_name):
        async with aiohttp.ClientSession() as session:
            try:
                with async_timeout.timeout(10):
                    async with session.get(COINGECKO_API_URL) as response:
                        result = await response.json()
                        matches = [coin for coin in result if crypto_name.lower() in coin['name'].lower()]
                        return matches
            except (aiohttp.ClientError, asyncio.TimeoutError):
                _LOGGER.error("Error fetching CoinGecko data")
        return []
