import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .const import DOMAIN, COINGECKO_API_URL, PORT_APP
from .outils import send_req_backend
from .coingecko import send_req_coingecko, fetch_crypto_id_from_coingecko  

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
                vol.Required("crypto_name_or_id", description="Nom ou ID de la cryptomonnaie"): str,
            }),
            errors={},
        )

    async def async_step_add_crypto(self, user_input=None):
        if user_input is not None:
            crypto_name_or_id = user_input.get("crypto_name_or_id")
            
            # Utiliser la fonction importée depuis coingecko.py
            crypto_id = await fetch_crypto_id_from_coingecko(crypto_name_or_id)
            
            if crypto_id:
                return self.async_show_form(
                    step_id="confirm_add_crypto",
                    data_schema=vol.Schema({
                        vol.Required("crypto_name", default=crypto_name_or_id, description="Nom de la cryptomonnaie"): str,
                        vol.Required("crypto_id", default=crypto_id, description="ID de la cryptomonnaie"): str,
                    }),
                    errors={},
                )
            else:
                errors = {"base": "crypto_not_found"}
                # Check if the API limit has been reached
                if crypto_id is None:
                    errors["base"] = "Limite API CoinGecko atteinte. Réessayez dans 1 minute."
                return self.async_show_form(
                    step_id="init",
                    data_schema=vol.Schema({
                        vol.Required("crypto_name_or_id", description="Nom ou ID de la cryptomonnaie"): str,
                    }),
                    errors=errors,
                )
            
            
    async def async_step_confirm_add_crypto(self, user_input=None):
        errors = {}
        if user_input is not None:
            crypto_name = user_input.get("crypto_name")
            crypto_id = user_input.get("crypto_id")

            # Vérifier si la crypto est déjà enregistrée dans l'intégration
            cryptos = self.config_entry.options.get("cryptos", [])
            valid_cryptos = [crypto for crypto in cryptos if isinstance(crypto, dict) and "id" in crypto]

            if any(crypto["id"] == crypto_id for crypto in valid_cryptos):
                errors["base"] = "crypto_already_exists"
            else:
                # Vérifier si la crypto existe déjà dans la base de données
                url = f"http://localhost:{PORT_APP}/load_cryptos/{self.config_entry.entry_id}"
                response = await send_req_backend(url, {}, "Load Cryptos", method='get')
                if response and response.status == 200:
                    db_cryptos = await response.json()
                    if any(crypto[1] == crypto_id for crypto in db_cryptos):  # Assurez-vous que la structure des données correspond à votre base de données
                        errors["base"] = "crypto_already_in_db"
                    else:
                        # Ajoute la nouvelle crypto
                        coordinator = self.hass.data[DOMAIN].get(self.config_entry.entry_id)
                        if coordinator:
                            success = await coordinator.add_crypto(crypto_name, crypto_id)
                            if success:
                                # Met à jour les options de l'entrée de configuration
                                valid_cryptos.append({"name": crypto_name, "id": crypto_id})
                                self.hass.config_entries.async_update_entry(self.config_entry, options={**self.config_entry.options, "cryptos": valid_cryptos})

                                # Reconfigure les entités pour ajouter les nouvelles cryptomonnaies
                                await self.hass.config_entries.async_forward_entry_unload(self.config_entry, "sensor")
                                await self.hass.config_entries.async_forward_entry_setups(self.config_entry, ["sensor"])

                                return self.async_create_entry(title=crypto_name, data={})
                else:
                    errors["base"] = "db_error"

        return self.async_show_form(
            step_id="confirm_add_crypto",
            data_schema=vol.Schema({
                vol.Required("crypto_name", default=user_input.get("crypto_name"), description="Nom de la cryptomonnaie"): str,
                vol.Required("crypto_id", default=user_input.get("crypto_id"), description="ID de la cryptomonnaie"): str,
            }),
            errors=errors,
        )
