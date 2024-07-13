import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers import device_registry as dr, entity_registry as er
from datetime import timedelta, datetime
import aiohttp
import async_timeout
import asyncio
import os
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from .const import DOMAIN, COINGECKO_API_URL, UPDATE_INTERVAL, RATE_LIMIT
from .db import save_crypto, load_crypto_attributes, delete_crypto_db
from .outils import send_req_backend
from .coingecko import send_req_coingecko, fetch_crypto_id_from_coingecko
from .price_updater import start_price_updater_thread, add_crypto_to_general_db

_LOGGER = logging.getLogger(__name__)

# Définir le schéma de validation pour le service
FETCH_CRYPTOS_SCHEMA = vol.Schema({
    vol.Required('entry_id'): cv.string,
})

async def async_setup(hass: HomeAssistant, config: dict):
    """Configurer l'intégration via le fichier configuration.yaml (non utilisé ici)"""
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    if entry.entry_id in hass.data[DOMAIN]:
        return False  # Entry déjà configurée

    coordinator = PortfolioCryptoCoordinator(hass, entry, update_interval=RATE_LIMIT)
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Charger les cryptos depuis la base de données
    cryptos = await coordinator.load_cryptos_from_db(entry.entry_id)
    if not cryptos:
        cryptos = []
    hass.config_entries.async_update_entry(entry, options={**entry.options, "cryptos": cryptos})

    # Initialiser la base de données pour le nouveau portfolio en appelant le service de l'addon
    if not entry.options.get("initialized", False):
        await initialize_database(entry, hass)

    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])

    async def async_fetch_cryptos_service(call: ServiceCall) -> ServiceResponse:
        entry_id = call.data.get("entry_id")
        return_response = call.data.get("return_response", True)
        _LOGGER.debug(f"Service fetch_cryptos called with entry_id: {entry_id}, return_response: {return_response}")
        coordinator = hass.data[DOMAIN].get(entry_id)
        if coordinator:
            cryptos = await coordinator.load_cryptos_from_db(entry_id)
            if cryptos is not None:
                _LOGGER.debug(f"Cryptocurrencies retrieved: {cryptos}")
                if return_response:
                    return {"data": {"cryptos": cryptos}}
                else:
                    return {"data": {"status": "success", "cryptos": cryptos}}
            else:
                _LOGGER.error("Error retrieving cryptocurrencies")
                raise ValueError("Error retrieving cryptocurrencies")
        else:
            _LOGGER.error(f"No coordinator found for entry_id: {entry_id}")
            raise ValueError(f"No coordinator found for entry_id: {entry_id}")

    hass.services.async_register(
        DOMAIN,
        "fetch_cryptos",
        async_fetch_cryptos_service,
        schema=FETCH_CRYPTOS_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )


    async def async_delete_crypto_service(call):
        crypto_id = call.data.get("crypto_id")
        entry_id = call.data.get("entry_id")
        _LOGGER.debug(f"Service delete_crypto appelé avec entry_id: {entry_id} et crypto_id: {crypto_id}")
        coordinator = hass.data[DOMAIN].get(entry_id)
        if coordinator:
            success = await coordinator.delete_crypto(crypto_id)
            if success:
                await hass.config_entries.async_forward_entry_unload(entry, "sensor")
                await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
                _LOGGER.debug(f"Crypto {crypto_id} supprimée avec succès et les entités ont été rechargées.")
            else:
                _LOGGER.error(f"Crypto {crypto_id} introuvable ou déjà supprimée.")
        else:
            _LOGGER.error(f"Aucun coordinator trouvé pour l'entry_id: {entry_id}")

        await hass.config_entries.async_reload(entry.entry_id)
    hass.services.async_register(DOMAIN, "delete_crypto", async_delete_crypto_service)

    async def async_add_crypto_service(call):
        name = call.data.get("crypto_name")
        entry_id = call.data.get("entry_id")
        _LOGGER.debug(f"Service add_crypto appelé avec entry_id: {entry_id} et crypto_name: {name}")
        coordinator = hass.data[DOMAIN].get(entry_id)
        if coordinator:
            success = await coordinator.add_crypto(name)
            if success:
                await hass.config_entries.async_forward_entry_unload(entry, "sensor")
                await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
                _LOGGER.debug(f"Crypto {name} ajoutée avec succès et les entités ont été rechargées.")
            else:
                _LOGGER.error(f"Crypto {name} introuvable ou déjà existante.")
        else:
            _LOGGER.error(f"Aucun coordinator trouvé pour l'entry_id: {entry_id}")

    hass.services.async_register(DOMAIN, "add_crypto", async_add_crypto_service)

    async def async_save_transaction_service(call):
        entry_id = call.data.get("entry_id")
        transaction = {
            "crypto_id": call.data.get("crypto_id"),
            "crypto_name": call.data.get("crypto_name"),
            "quantity": call.data.get("quantity"),
            "price_usd": call.data.get("price_usd"),
            "transaction_type": call.data.get("transaction_type"),
            "location": call.data.get("location"),
            "date": call.data.get("date"),
        }
        _LOGGER.debug(f"Service save_transaction appelé avec entry_id: {entry_id} et transaction: {transaction}")
        coordinator = hass.data[DOMAIN].get(entry_id)
        if coordinator:
            success = await coordinator.save_transaction(transaction)
            if success:
                _LOGGER.debug("Transaction ajoutée avec succès")
            else:
                _LOGGER.error("Erreur lors de l'ajout de la transaction")
        else:
            _LOGGER.error(f"Aucun coordinator trouvé pour l'entry_id: {entry_id}")

    hass.services.async_register(DOMAIN, "save_transaction", async_save_transaction_service)

    async def async_delete_transaction_service(call):
        entry_id = call.data.get("entry_id")
        transaction_id = call.data.get("transaction_id")
        _LOGGER.debug(f"Service delete_transaction appelé avec entry_id: {entry_id} et transaction_id: {transaction_id}")
        coordinator = hass.data[DOMAIN].get(entry_id)
        if coordinator:
            success = await coordinator.delete_transaction(transaction_id)
            if success:
                _LOGGER.debug("Transaction supprimée avec succès")
            else:
                _LOGGER.error("Erreur lors de la suppression de la transaction")
        else:
            _LOGGER.error(f"Aucun coordinator trouvé pour l'entry_id: {entry_id}")

    hass.services.async_register(DOMAIN, "delete_transaction", async_delete_transaction_service)

    async def async_update_transaction_service(call):
        entry_id = call.data.get("entry_id")
        transaction = {
            "transaction_id": call.data.get("transaction_id"),
            "crypto_id": call.data.get("crypto_id"),
            "crypto_name": call.data.get("crypto_name"),
            "quantity": call.data.get("quantity"),
            "price_usd": call.data.get("price_usd"),
            "transaction_type": call.data.get("transaction_type"),
            "location": call.data.get("location"),
            "date": call.data.get("date"),
        }
        _LOGGER.debug(f"Service update_transaction appelé avec entry_id: {entry_id} et transaction: {transaction}")
        coordinator = hass.data[DOMAIN].get(entry_id)
        if coordinator:
            success = await coordinator.update_transaction(transaction)
            if success:
                _LOGGER.debug("Transaction mise à jour avec succès")
            else:
                _LOGGER.error("Erreur lors de la mise à jour de la transaction")
        else:
            _LOGGER.error(f"Aucun coordinator trouvé pour l'entry_id: {entry_id}")

    hass.services.async_register(DOMAIN, "update_transaction", async_update_transaction_service)

    async def async_export_db_service(call):
        entry_id = call.data.get("entry_id")
        _LOGGER.debug(f"Service export_db appelé avec entry_id: {entry_id}")
        coordinator = hass.data[DOMAIN].get(entry_id)
        if coordinator:
            success = await coordinator.export_db(entry_id)
            if success:
                _LOGGER.debug("Base de données exportée avec succès")
            else:
                _LOGGER.error("Erreur lors de l'exportation de la base de données")
        else:
            _LOGGER.error(f"Aucun coordinator trouvé pour l'entry_id: {entry_id}")

    hass.services.async_register(DOMAIN, "export_db", async_export_db_service)

    async def async_import_db_service(call):
        entry_id = call.data.get("entry_id")
        file = call.data.get("file")
        _LOGGER.debug(f"Service import_db appelé avec entry_id: {entry_id} et fichier: {file}")
        coordinator = hass.data[DOMAIN].get(entry_id)
        if coordinator:
            success = await coordinator.import_db(entry_id, file)
            if success:
                _LOGGER.debug("Base de données importée avec succès")
            else:
                _LOGGER.error("Erreur lors de l'importation de la base de données")
        else:
            _LOGGER.error(f"Aucun coordinator trouvé pour l'entry_id: {entry_id}")

    hass.services.async_register(DOMAIN, "import_db", async_import_db_service)

    async def async_fetch_transactions_service(call):
        entry_id = call.data.get("entry_id")
        crypto_id = call.data.get("crypto_id")
        _LOGGER.debug(f"Service fetch_transactions appelé avec entry_id: {entry_id} et crypto_id: {crypto_id}")
        coordinator = hass.data[DOMAIN].get(entry_id)
        if coordinator:
            transactions = await coordinator.fetch_transactions()
            if transactions is not None:
                _LOGGER.debug(f"Transactions récupérées: {transactions}")
                # Filter transactions by crypto_id if needed and process or return them
            else:
                _LOGGER.error("Erreur lors de la récupération des transactions")
        else:
            _LOGGER.error(f"Aucun coordinator trouvé pour l'entry_id: {entry_id}")

    hass.services.async_register(DOMAIN, "fetch_transactions", async_fetch_transactions_service)

    return True

async def initialize_database(entry: ConfigEntry, hass: HomeAssistant):
    """Initialize the database for the new portfolio by calling the addon service."""
    url = "http://localhost:5000/initialize"
    payload = {"entry_id": entry.entry_id}
    await send_req_backend(url, payload, "Initialize Database")

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Décharger une entrée configurée"""
    if entry.entry_id in hass.data[DOMAIN]:
        await hass.config_entries.async_forward_entry_unload(entry, "sensor")
        hass.services.async_remove(DOMAIN, "add_crypto")
        hass.data[DOMAIN].pop(entry.entry_id)

    return True

class PortfolioCryptoCoordinator(DataUpdateCoordinator):
    """Coordinator pour gérer les mises à jour des données du portfolio crypto."""

    def __init__(self, hass, config_entry, update_interval):
        super().__init__(
            hass,
            _LOGGER,
            name="PortfolioCrypto",
            update_interval=timedelta(minutes=update_interval),
        )
        self.config_entry = config_entry
        self._last_update = None
        _LOGGER.info(f"Coordinator initialized with update interval: {update_interval} minute(s)")

    async def _async_update_data(self):
        now = datetime.now()
        if self._last_update is not None:
            elapsed = now - self._last_update
            _LOGGER.info(f"Data updated. {elapsed.total_seconds() / 60:.2f} minutes elapsed since last update.")
        self._last_update = now

        _LOGGER.info("Fetching new data from API/database")

        # Fetch data from API or database
        data = await self.fetch_all_data()

        _LOGGER.info("New data fetched successfully")
        return data

    async def delete_crypto(self, crypto_id):
        entry_id = self.config_entry.entry_id
        # Supprimer la crypto de la base de données
        success = delete_crypto_db(entry_id, crypto_id)
        if not success:
            return False

        # Supprimer la crypto de la configuration
        cryptos = self.config_entry.options.get("cryptos", [])
        updated_cryptos = [crypto for crypto in cryptos if crypto["id"] != crypto_id]
        self.hass.config_entries.async_update_entry(self.config_entry, options={**self.config_entry.options, "cryptos": updated_cryptos})

        # Supprimer les entités de Home Assistant
        entity_registry = er.async_get(self.hass)
        device_registry = dr.async_get(self.hass)
        
        # Trouver toutes les entités et l'appareil associé à la crypto_id
        entries = er.async_entries_for_config_entry(entity_registry, self.config_entry.entry_id)
        for entry in entries:
            if entry.unique_id.startswith(f"{self.config_entry.entry_id}_{crypto_id}"):
                # Supprimer l'entité
                entity_registry.async_remove(entry.entity_id)

                # Trouver l'appareil associé à cette entité et le supprimer
                device_entry = device_registry.async_get_device({(DOMAIN, entry.unique_id)})
                if device_entry is not None:
                    device_registry.async_remove_device(device_entry.id)

        return True
    
    async def fetch_all_data(self):
        """Fetch all necessary data."""
        data = {}
        data["transactions"] = await self.fetch_transactions()
        data["total_investment"] = await self.fetch_total_investment()
        data["total_profit_loss"] = await self.fetch_total_profit_loss()
        data["total_profit_loss_percent"] = await self.fetch_total_profit_loss_percent()
        data["total_value"] = await self.fetch_total_value()

        for crypto in self.config_entry.options.get("cryptos", []):
            crypto_data = await self.fetch_crypto_data(crypto["id"])
            data[crypto["id"]] = crypto_data
        return data

    async def fetch_transactions(self):
        _LOGGER.info("Fetching transactions data")
        return []

    async def fetch_total_investment(self):
        _LOGGER.info("Fetching total investment data")
        return 0

    async def fetch_total_profit_loss(self):
        _LOGGER.info("Fetching total profit/loss data")
        return 0

    async def fetch_total_profit_loss_percent(self):
        _LOGGER.info("Fetching total profit/loss percent data")
        return 0

    async def fetch_total_value(self):
        _LOGGER.info("Fetching total value data")
        return 0
    
    async def fetch_crypto_data(self, crypto_id):
        _LOGGER.info(f"Fetching data for crypto ID: {crypto_id}")
        # Reload data from database if available
        crypto_attributes = load_crypto_attributes(self.config_entry.entry_id)
        return crypto_attributes.get(crypto_id, {
            
            "crypto_id": next((crypto["id"] for crypto in self.config_entry.options.get("cryptos", []) if crypto["id"] == crypto_id), None),
            "crypto_name": next((crypto["name"] for crypto in self.config_entry.options.get("cryptos", []) if crypto["id"] == crypto_id), None)
        })

    async def add_crypto(self, crypto_name, crypto_id):
        cryptos = self.config_entry.options.get("cryptos", [])

        # Vérifiez que la structure est correcte
        valid_cryptos = [crypto for crypto in cryptos if isinstance(crypto, dict) and "id" in crypto]

        # Assurez-vous que la crypto n'existe pas déjà
        if any(c["id"] == crypto_id for c in valid_cryptos):
            _LOGGER.info(f"Crypto {crypto_name} with ID {crypto_id} already exists")
            return False

        # Ajoutez la nouvelle crypto à la liste valide
        valid_cryptos.append({"name": crypto_name, "id": crypto_id})

        # Mettez à jour les options de configuration avec la liste valide
        self.hass.config_entries.async_update_entry(self.config_entry, options={**self.config_entry.options, "cryptos": valid_cryptos})

        # Sauvegarder les informations de crypto dans la base de données
        await self.save_crypto_to_db(self.config_entry.entry_id, crypto_name, crypto_id)

        # ajout de la crypto dans la liste des crypto a surveiller 
        await add_crypto_to_general_db(crypto_name, crypto_id)

        # Recharger l'intégration pour ajouter les nouvelles cryptomonnaies
        await self.hass.config_entries.async_reload(self.config_entry.entry_id)

        return True
    
    async def fetch_crypto_id(self, crypto_name):
        return await fetch_crypto_id_from_coingecko(crypto_name)
    


    async def save_crypto_to_db(self, entry_id, crypto_name, crypto_id):
        url = f"http://localhost:5000/save_crypto"
        payload = {
            "entry_id": entry_id,
            "crypto_name": crypto_name,
            "crypto_id": crypto_id
        }
        await send_req_backend(url, payload, f"Save Crypto {crypto_name} with ID {crypto_id}")


    async def load_cryptos_from_db(self, entry_id):
        url = f"http://localhost:5000/load_cryptos/{entry_id}"
        response = await send_req_backend(url, {}, "Load Cryptos", method='get')
        if response and response.status == 200:
            cryptos = await response.json()
            _LOGGER.info(f"Cryptos chargées depuis la base de données: {cryptos}")
            return cryptos
        else:
            return []

    async def save_transaction(self, transaction):
        entry_id = transaction["entry_id"]
        url = f"http://localhost:5000/transaction/{entry_id}"
        return await send_req_backend(url, transaction, "Save Transaction")


    async def delete_transaction(self, transaction_id):
        entry_id = self.config_entry.entry_id
        url = f"http://localhost:5000/transaction/{entry_id}/{transaction_id}"
        return await send_req_backend(url, {}, "Delete Transaction", method='delete')


    async def update_transaction(self, transaction):
        entry_id = transaction["entry_id"]
        transaction_id = transaction["transaction_id"]
        url = f"http://localhost:5000/transaction/{entry_id}/{transaction_id}"
        return await send_req_backend(url, transaction, "Update Transaction", method='put')


    async def export_db(self, entry_id):
        url = f"http://localhost:5000/export_db/{entry_id}"
        response = await send_req_backend(url, {}, "Export Database", method='get')
        return response and response.status == 200

    async def import_db(self, entry_id, file):
        url = f"http://localhost:5000/import_db"
        return await send_req_backend(url, title="Import DB", method='post', form_data={'file': file, 'entry_id': entry_id})
