import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from datetime import timedelta, datetime
import aiohttp
import async_timeout
import asyncio
import os
from .const import DOMAIN, COINGECKO_API_URL
from .db import get_crypto_attributes  # Ajoutez cette ligne

_LOGGER = logging.getLogger(__name__)

# Configurer la journalisation pour écrire dans un fichier
log_handler = logging.FileHandler('/config/logs/integration.log')
log_handler.setLevel(logging.DEBUG)
log_formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
log_handler.setFormatter(log_formatter)
_LOGGER.addHandler(log_handler)

async def async_setup(hass: HomeAssistant, config: dict):
    """Configurer l'intégration via le fichier configuration.yaml (non utilisé ici)"""
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Configurer l'intégration via l'interface utilisateur"""
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    if entry.entry_id in hass.data[DOMAIN]:
        return False  # Entry déjà configurée

    coordinator = PortfolioCryptoCoordinator(hass, entry, update_interval=1)  # Fixe l'intervalle de mise à jour à 1 minute
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Charger les cryptos depuis la base de données
    await coordinator.load_crypto_attributes()
    cryptos = coordinator.cryptos
    if not cryptos:
        cryptos = []
    hass.config_entries.async_update_entry(entry, options={**entry.options, "cryptos": cryptos})

    # Initialiser la base de données pour le nouveau portfolio en appelant le service de l'addon
    if not entry.options.get("initialized", False):
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

    await hass.config_entries.async_forward_entry_setup(entry, "sensor")

    async def async_add_crypto_service(call):
        """Service pour ajouter une nouvelle crypto-monnaie"""
        name = call.data.get("crypto_name")
        entry_id = call.data.get("entry_id")
        coordinator = hass.data[DOMAIN].get(entry_id)
        if coordinator:
            success = await coordinator.add_crypto(name)
            if not success:
                _LOGGER.error(f"Crypto {name} introuvable")

    hass.services.async_register(
        DOMAIN, "add_crypto", async_add_crypto_service
    )
    
    return True

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
        self.cryptos = []
        _LOGGER.info(f"Coordinator initialized with update interval: {update_interval} minute(s)")

    async def _async_update_data(self):
        now = datetime.now()
        if self._last_update is not None:
            elapsed = now - self._last_update
            _LOGGER.info(f"Data updated. {(elapsed.total_seconds() / 60):.2f} minutes elapsed since last update.")
        self._last_update = now

        _LOGGER.info("Fetching new data from API/database")

        # Fetch data from API or database
        data = {}
        data["transactions"] = await self.fetch_transactions()
        data["total_investment"] = await self.fetch_total_investment()
        data["total_profit_loss"] = await self.fetch_total_profit_loss()
        data["total_profit_loss_percent"] = await self.fetch_total_profit_loss_percent()
        data["total_value"] = await self.fetch_total_value()

        for crypto in self.config_entry.options.get("cryptos", []):
            crypto_data = await self.fetch_crypto_data(crypto["id"])
            data[crypto["id"]] = crypto_data

        _LOGGER.info("New data fetched successfully")
        return data

    async def load_crypto_attributes(self):
        self.cryptos = get_crypto_attributes(self.config_entry.entry_id)
        _LOGGER.info(f"Loaded crypto attributes: {self.cryptos}")

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
        return {
            "transactions": [],
            "total_investment": 0,
            "total_profit_loss": 0,
            "total_profit_loss_percent": 0,
            "total_value": 0
        }

    async def add_crypto(self, crypto_name):
        crypto_id = await self.fetch_crypto_id(crypto_name)
        if crypto_id:
            cryptos = self.config_entry.options.get("cryptos", [])
            cryptos.append({"name": crypto_name, "id": crypto_id})
            self.hass.config_entries.async_update_entry(self.config_entry, options={**self.config_entry.options, "cryptos": cryptos})

            # Sauvegarder les informations de crypto dans la base de données
            await self.save_crypto_to_db(self.config_entry.entry_id, crypto_name, crypto_id)

            # Reconfigurer les entités pour ajouter les nouvelles cryptomonnaies
            await self.hass.config_entries.async_forward_entry_unload(self.config_entry, "sensor")
            await self.hass.config_entries.async_forward_entry_setup(self.config_entry, "sensor")

            return True
        return False

    async def fetch_crypto_id(self, crypto_name):
        async with aiohttp.ClientSession() as session:
            try:
                with async_timeout.timeout(10):
                    async with session.get(COINGECKO_API_URL) as response:
                        result = await response.json()
                        for coin in result:
                            if coin['name'].lower() == crypto_name.lower() or coin['id'].lower() == crypto_name.lower():
                                return coin['id']
            except (aiohttp.ClientError, asyncio.TimeoutError):
                _LOGGER.error("Error fetching CoinGecko data")
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
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        _LOGGER.info(f"Crypto {crypto_name} avec ID {crypto_id} sauvegardée dans la base de données.")
                    else:
                        _LOGGER.error(f"Erreur lors de la sauvegarde de la crypto {crypto_name} dans la base de données.")
        except Exception as e:
            _LOGGER.error(f"Exception lors de la sauvegarde de la crypto dans la base de données: {e}")
