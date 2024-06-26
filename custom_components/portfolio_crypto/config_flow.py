"""
Fichier config_flow.py
Ce fichier gère le flux de configuration pour l'intégration Portfolio Crypto dans Home Assistant.
"""

import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

@config_entries.HANDLERS.register(DOMAIN)
class PortfolioCryptoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Gestion du flux de configuration pour Portfolio Crypto"""
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(self, user_input=None):
        """Gérer l'étape initiale de configuration par l'utilisateur"""
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
    """Gestion du flux des options pour Portfolio Crypto"""
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Gérer l'étape initiale des options"""
        return self.async_create_entry(title="", data={})
