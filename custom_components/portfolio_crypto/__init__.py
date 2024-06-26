import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers import device_registry as dr, entity_registry as er
from datetime import timedelta, datetime
import aiohttp
import async_timeout
import asyncio
import os
from .const import DOMAIN, COINGECKO_API_URL
from .db import save_crypto, load_crypto_attributes, delete_crypto_db


_LOGGER = logging.getLogger(__name__)

# Configurer la journalisation pour écrire dans un fichier
#log_handler = logging.FileHandler('/config/logs/integration.log')
#log_handler.setLevel(logging.DEBUG)
#log_formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
#log_handler.setFormatter(log_formatter)
#_LOGGER.addHandler(log_handler)

async def async_setup(hass: HomeAssistant, config: dict):
    """Configurer l'intégration via le fichier configuration.yaml (non utilisé ici)"""
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    if entry.entry_id in hass.data[DOMAIN]:
        return False  # Entry déjà configurée

    coordinator = PortfolioCryptoCoordinator(hass, entry, update_interval=1)
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Charger les cryptos depuis la base de données
    cryptos = await coordinator.load_cryptos_from_db(entry.entry_id)
    if not cryptos:
        cryptos = []
    hass.config_entries.async_update_entry(entry, options={**entry.options, "cryptos": cryptos})

    # Initialiser la base de données pour le nouveau portfolio en appelant le service de l'addon
    if not entry.options.get("initialized", False):
        await initialize_database(entry, hass)

    await hass.config_entries.async_forward_entry_setup(entry, "sensor")

    async def async_delete_crypto_service(call):
        crypto_id = call.data.get("crypto_id")
        entry_id = call.data.get("entry_id")
        _LOGGER.debug(f"Service delete_crypto appelé avec entry_id: {entry_id} et crypto_id: {crypto_id}")
        coordinator = hass.data[DOMAIN].get(entry_id)
        if coordinator:
            success = await coordinator.delete_crypto(crypto_id)
            if success:
                # Recharger les entités après la suppression d'une crypto
                await hass.config_entries.async_forward_entry_unload(entry, "sensor")
                await hass.config_entries.async_forward_entry_setup(entry, "sensor")
                _LOGGER.debug(f"Crypto {crypto_id} supprimée avec succès et les entités ont été rechargées.")
            else:
                _LOGGER.error(f"Crypto {crypto_id} introuvable ou déjà supprimée.")
        else:
            _LOGGER.error(f"Aucun coordinator trouvé pour l'entry_id: {entry_id}")

        # Recharger l'intégration pour supprimer les cryptomonnaies
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
                # Recharger les entités après l'ajout d'une nouvelle crypto
                await hass.config_entries.async_forward_entry_unload(entry, "sensor")
                await hass.config_entries.async_forward_entry_setup(entry, "sensor")
                _LOGGER.debug(f"Crypto {name} ajoutée avec succès et les entités ont été rechargées.")
            else:
                _LOGGER.error(f"Crypto {name} introuvable ou déjà existante.")
        else:
            _LOGGER.error(f"Aucun coordinator trouvé pour l'entry_id: {entry_id}")

        # Recharger l'intégration pour ajouter les nouvelles cryptomonnaies
        #await self.hass.config_entries.async_reload(self.config_entry.entry_id)
    hass.services.async_register(DOMAIN, "add_crypto", async_add_crypto_service)

    return True


async def initialize_database(entry: ConfigEntry, hass: HomeAssistant):
    """Initialize the database for the new portfolio by calling the addon service."""
    try:
        async with aiohttp.ClientSession() as session:
            supervisor_token = os.getenv("SUPERVISOR_TOKEN")
            headers = {
                "Authorization": f"Bearer {supervisor_token}",
                "Content-Type": "application/json",
            }
            url = "http://localhost:5000/initialize"
            _LOGGER.info(f"Appel de l'URL {url} avec l'ID d'entrée: {entry.entry_id}")
            async with session.post(url, json={"entry_id": entry.entry_id}, headers=headers) as response:
                response_text = await response.text()
                _LOGGER.info(f"Statut de la réponse: {response.status}, Texte de la réponse: {response_text}")
                if response.status == 200:
                    _LOGGER.info(f"Base de données initialisée avec succès pour l'ID d'entrée: {entry.entry_id}")
                    hass.config_entries.async_update_entry(entry, options={**entry.options, "initialized": True})
                else:
                    _LOGGER.error(f"Échec de l'initialisation de la base de données pour l'ID d'entrée: {entry.entry_id}, code de statut: {response.status}, texte de la réponse: {response_text}")
    except Exception as e:
        _LOGGER.error(f"Exception survenue lors de l'initialisation de la base de données pour l'ID d'entrée: {entry.entry_id}: {e}")

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

        # Recharger l'intégration pour ajouter les nouvelles cryptomonnaies
        await self.hass.config_entries.async_reload(self.config_entry.entry_id)

        return True
    
    async def fetch_crypto_id(self, crypto_name):
        async with aiohttp.ClientSession() as session:
            try:
                with async_timeout.timeout(10):
                    async with session.get(COINGECKO_API_URL) as response:
                        if response.status == 200:
                            result = await response.json()
                            if isinstance(result, list):
                                for coin in result:
                                    if isinstance(coin, dict):
                                        if coin.get('name', '').lower() == crypto_name.lower() or coin.get('id', '').lower() == crypto_name.lower():
                                            return coin['id']
                            else:
                                _LOGGER.error("Unexpected response format from CoinGecko API")
                                return None
                        else:
                            _LOGGER.error(f"Error fetching data from CoinGecko API: {response.status}")
                            return None
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                _LOGGER.error(f"Error fetching CoinGecko data: {e}")
                return None
        return None



    async def save_crypto_to_db(self, entry_id, crypto_name, crypto_id):
        try:
            async with aiohttp.ClientSession() as session:
                supervisor_token = os.getenv("SUPERVISOR_TOKEN")
                headers = {
                    "Authorization": f"Bearer {supervisor_token}",
                    "Content-Type": "application/json",
                }
                url = f"http://localhost:5000/save_crypto"
                payload = {
                    "entry_id": entry_id,
                    "crypto_name": crypto_name,
                    "crypto_id": crypto_id
                }
                _LOGGER.debug(f"Envoi de la requête à {url} avec payload: {payload}")
                async with session.post(url, json=payload, headers=headers) as response:
                    response_text = await response.text()
                    _LOGGER.debug(f"Réponse reçue: {response.status}, {response_text}")
                    if response.status == 200:
                        _LOGGER.info(f"Crypto {crypto_name} avec ID {crypto_id} sauvegardée dans la base de données.")
                    else:
                        _LOGGER.error(f"Erreur lors de la sauvegarde de la crypto {crypto_name} avec ID {crypto_id} dans la base de données. Statut: {response.status}, Réponse: {response_text}")
        except Exception as e:
            _LOGGER.error(f"Exception lors de la sauvegarde de la crypto {crypto_name} avec ID {crypto_id} dans la base de données: {e}")

    async def load_cryptos_from_db(self, entry_id):
        try:
            async with aiohttp.ClientSession() as session:
                supervisor_token = os.getenv("SUPERVISOR_TOKEN")
                headers = {
                    "Authorization": f"Bearer {supervisor_token}",
                    "Content-Type": "application/json",
                }
                url = f"http://localhost:5000/load_cryptos/{entry_id}"
                async with session.get(url, headers=headers) as response:
                    response_text = await response.text()
                    _LOGGER.info(f"Statut de la réponse: {response.status}, Texte de la réponse: {response_text}")
                    if response.status == 200:
                        cryptos = await response.json()
                        _LOGGER.info(f"Cryptos chargées depuis la base de données: {cryptos}")
                        return cryptos
                    else:
                        _LOGGER.error(f"Erreur lors du chargement des cryptos depuis la base de données pour l'ID d'entrée {entry_id}. Statut: {response.status}, Réponse: {response_text}")
                        return []
        except Exception as e:
            _LOGGER.error(f"Exception lors du chargement des cryptos depuis la base de données pour l'ID d'entrée {entry_id}: {e}")
            return []
