import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .const import DOMAIN, COINGECKO_API_URL

_LOGGER = logging.getLogger(__name__)

@config_entries.HANDLERS.register(DOMAIN)
class PortfolioCryptoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title=user_input["name"], data={"name": user_input["name"], "cryptos": [], "initialized": False})

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
        if user_input is not None:
            return await self.async_step_add_crypto(user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required("crypto_name"): str,
            }),
            errors={},
        )

    async def async_step_add_crypto(self, user_input=None):
        if user_input is not None:
            crypto_name = user_input.get("crypto_name")
            session = async_get_clientsession(self.hass)
            async with session.get(f"{COINGECKO_API_URL}?query={crypto_name}") as response:
                if response.status == 200:
                    data = await response.json()
                    if isinstance(data, list):
                        for coin in data:
                            if coin['name'].lower() == crypto_name.lower():
                                crypto_id = coin['id']
                                break
                        else:
                            crypto_id = None
                    else:
                        crypto_id = None

                    if crypto_id:
                        return self.async_show_form(
                            step_id="confirm_add_crypto",
                            data_schema=vol.Schema({
                                vol.Required("crypto_name"): str,
                                vol.Required("crypto_id"): str,
                            }),
                            errors={},
                        )
                    else:
                        return self.async_show_form(
                            step_id="init",
                            data_schema=vol.Schema({
                                vol.Required("crypto_name"): str,
                            }),
                            errors={"base": "crypto_not_found"},
                        )
                else:
                    return self.async_show_form(
                        step_id="init",
                        data_schema=vol.Schema({
                            vol.Required("crypto_name"): str,
                        }),
                        errors={"base": "api_error"},
                    )

    async def async_step_confirm_add_crypto(self, user_input=None):
        if user_input is not None:
            crypto_name = user_input.get("crypto_name")
            crypto_id = user_input.get("crypto_id")
            cryptos = self.config_entry.options.get("cryptos", [])
            cryptos.append({"name": crypto_name, "id": crypto_id})
            self.hass.config_entries.async_update_entry(self.config_entry, options={**self.config_entry.options, "cryptos": cryptos})
            return self.async_create_entry(title=crypto_name, data={})
