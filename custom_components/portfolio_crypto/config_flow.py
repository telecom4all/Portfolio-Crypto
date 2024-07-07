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
            entry_id = self.hass.helpers.entity_registry.async_get_or_create(DOMAIN, DOMAIN, user_input["name"]).entry_id
            # Création de l'entrée de configuration
            config_entry = await self.async_set_unique_id(entry_id)
            self._abort_if_unique_id_configured()
            
            # Sauvegarder l'ID et le nom du portefeuille
            self.hass.states.async_set(f"{DOMAIN}.{entry_id}", user_input["name"], {
                "id": entry_id,
                "name": user_input["name"]
            })
            
            # Créer et configurer l'entrée
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
            session = async_get_clientsession(self.hass)
            async with session.get(f"{COINGECKO_API_URL}?query={crypto_name_or_id}") as response:
                if response.status == 200:
                    data = await response.json()
                    crypto_id = None
                    crypto_name = None
                    for coin in data:
                        if coin['name'].lower() == crypto_name_or_id.lower() or coin['id'].lower() == crypto_name_or_id.lower():
                            crypto_id = coin['id']
                            crypto_name = coin['name']
                            break
                    if crypto_id:
                        return self.async_show_form(
                            step_id="confirm_add_crypto",
                            data_schema=vol.Schema({
                                vol.Required("crypto_name", default=crypto_name, description="Nom de la cryptomonnaie"): str,
                                vol.Required("crypto_id", default=crypto_id, description="ID de la cryptomonnaie"): str,
                            }),
                            errors={},
                        )
                    else:
                        return self.async_show_form(
                            step_id="init",
                            data_schema=vol.Schema({
                                vol.Required("crypto_name_or_id", description="Nom ou ID de la cryptomonnaie"): str,
                            }),
                            errors={"base": "crypto_not_found"},
                        )
                else:
                    return self.async_show_form(
                        step_id="init",
                        data_schema=vol.Schema({
                            vol.Required("crypto_name_or_id", description="Nom ou ID de la cryptomonnaie"): str,
                        }),
                        errors={"base": "api_error"},
                    )

    async def async_step_confirm_add_crypto(self, user_input=None):
        errors = {}
        if user_input is not None:
            crypto_name = user_input.get("crypto_name")
            crypto_id = user_input.get("crypto_id")

            #_LOGGER.error(f"crypto_name : {crypto_name}")
            #_LOGGER.error(f"crypto_id : {crypto_id}")

            # Vérifier si la crypto est déjà enregistrée dans l'intégration
            cryptos = self.config_entry.options.get("cryptos", [])
            valid_cryptos = [crypto for crypto in cryptos if isinstance(crypto, dict) and "id" in crypto]

            if any(crypto["id"] == crypto_id for crypto in valid_cryptos):
                errors["base"] = "crypto_already_exists"
            else:
                # Vérifier si la crypto existe déjà dans la base de données
                session = async_get_clientsession(self.hass)
                async with session.get(f"http://localhost:5000/load_cryptos/{self.config_entry.entry_id}") as response:
                    if response.status == 200:
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
                                    await self.hass.config_entries.async_forward_entry_setup(self.config_entry, "sensor")

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
