import logging
from datetime import timedelta, datetime
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo
import aiohttp
import async_timeout
import asyncio
import os
from .const import DOMAIN, COINGECKO_API_URL
from .db import save_crypto, load_crypto_attributes
import ast

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    coordinator = PortfolioCryptoCoordinator(hass, config_entry, update_interval=1)  # Fixing update interval to 1 minute
    await coordinator.async_config_entry_first_refresh()

    entities = []

    # Add main portfolio sensors
    entities.append(PortfolioCryptoSensor(coordinator, config_entry, "transactions"))
    entities.append(PortfolioCryptoSensor(coordinator, config_entry, "total_investment"))
    entities.append(PortfolioCryptoSensor(coordinator, config_entry, "total_profit_loss"))
    entities.append(PortfolioCryptoSensor(coordinator, config_entry, "total_profit_loss_percent"))
    entities.append(PortfolioCryptoSensor(coordinator, config_entry, "total_value"))

    # Add sensors for each cryptocurrency in the portfolio
    cryptos = config_entry.options.get("cryptos", [])
    crypto_attributes = load_crypto_attributes(config_entry.entry_id)
    for crypto in cryptos:
        if isinstance(crypto, dict) and "id" in crypto:
            crypto_id = crypto["id"]
            crypto_name = crypto["name"]
            crypto_data = crypto_attributes.get(crypto_id, {})
        elif isinstance(crypto, list) and len(crypto) > 1:
            crypto_id = crypto[1]
            crypto_name = crypto[0]
            crypto_data = crypto_attributes.get(crypto_id, {})
        else:
            _LOGGER.error(f"Le format de 'crypto' est incorrect: {crypto}")
            continue

        for sensor_type in ['investment', 'current_value', 'profit_loss', 'profit_loss_percent', 'transactions_count', 'average_price']:
            entities.append(CryptoSensor(coordinator, config_entry, {"name": crypto_name, "id": crypto_id}, sensor_type, crypto_data))

    async_add_entities(entities, update_before_add=True)

    # Schedule periodic updates for all entities
    for entity in entities:
        coordinator.async_add_listener(entity.async_write_ha_state)



class PortfolioCryptoCoordinator(DataUpdateCoordinator):
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
        data = {}
        transactions = await self.fetch_transactions()
        data["transactions"] = len(transactions)
        data["total_investment"] = await self.fetch_total_investment()
        data["total_profit_loss"] = await self.fetch_total_profit_loss()
        data["total_profit_loss_percent"] = await self.fetch_total_profit_loss_percent()
        data["total_value"] = await self.fetch_total_value()

        for crypto in self.config_entry.options.get("cryptos", []):
            if isinstance(crypto, dict) and "id" in crypto:
                crypto_id = crypto["id"]
                crypto_name = crypto["name"]
            elif isinstance(crypto, list) and len(crypto) > 1:
                crypto_id = crypto[1]
                crypto_name = crypto[0]
            else:
                _LOGGER.error(f"Le format de 'crypto' est incorrect: {crypto}")
                continue

            crypto_data = await self.fetch_crypto_profit_loss(crypto_id)
            crypto_transactions = await self.fetch_crypto_transactions(crypto_id)
            crypto_data["transactions_count"] = len(crypto_transactions)
            crypto_data["average_price"] = 0

            data[crypto_id] = {
                "crypto_id": crypto_id,
                "crypto_name": crypto_name,
                "investment": crypto_data.get("investment"),
                "current_value": crypto_data.get("current_value"),
                "profit_loss": crypto_data.get("profit_loss"),
                "profit_loss_percent": crypto_data.get("profit_loss_percent"),
                "transactions_count": crypto_data.get("transactions_count"),
                "average_price": crypto_data.get("average_price")
            }
        _LOGGER.info(f"Fetched data: {data}")
        _LOGGER.info("New data fetched successfully")
        return data



    async def fetch_crypto_profit_loss(self, crypto_id):
        entry_id = self.config_entry.entry_id
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"http://localhost:5000/crypto_profit_loss/{entry_id}/{crypto_id}") as response:
                    if response.status == 200:
                        data = await response.json()
                        return data
                    else:
                        _LOGGER.error(f"Erreur lors de la récupération du profit/perte pour {crypto_id}: {response.status}")
                        return {
                            "investment": 0,
                            "current_value": 0,
                            "profit_loss": 0,
                            "profit_loss_percent": 0
                        }
        except Exception as e:
            _LOGGER.error(f"Exception lors de la récupération du profit/perte pour {crypto_id}: {e}")
            return {
                "investment": 0,
                "current_value": 0,
                "profit_loss": 0,
                "profit_loss_percent": 0
            }

    async def fetch_crypto_transactions(self, crypto_id):
        entry_id = self.config_entry.entry_id
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"http://localhost:5000/transactions/{entry_id}/{crypto_id}") as response:
                    if response.status == 200:
                        transactions = await response.json()
                        return transactions
                    else:
                        _LOGGER.error(f"Erreur lors de la récupération des transactions pour {crypto_id}: {response.status}")
                        return []
        except Exception as e:
            _LOGGER.error(f"Exception lors de la récupération des transactions pour {crypto_id}: {e}")
            return []
        
    async def fetch_transactions(self):
        entry_id = self.config_entry.entry_id
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"http://localhost:5000/transactions/{entry_id}") as response:
                    if response.status == 200:
                        transactions = await response.json()
                        return transactions
                    else:
                        _LOGGER.error(f"Erreur lors de la récupération des transactions: {response.status}")
                        return []
        except Exception as e:
            _LOGGER.error(f"Exception lors de la récupération des transactions: {e}")
            return []

    async def fetch_total_investment(self):
        entry_id = self.config_entry.entry_id
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"http://localhost:5000/profit_loss/{entry_id}") as response:
                    if response.status == 200:
                        data = await response.json()
                        return data['summary']['total_investment']
                    else:
                        _LOGGER.error(f"Erreur lors de la récupération de l'investissement total: {response.status}")
                        return 0
        except Exception as e:
            _LOGGER.error(f"Exception lors de la récupération de l'investissement total: {e}")
            return 0

    async def fetch_total_profit_loss(self):
        entry_id = self.config_entry.entry_id
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"http://localhost:5000/profit_loss/{entry_id}") as response:
                    if response.status == 200:
                        data = await response.json()
                        return data['summary']['total_profit_loss']
                    else:
                        _LOGGER.error(f"Erreur lors de la récupération du profit/perte total: {response.status}")
                        return 0
        except Exception as e:
            _LOGGER.error(f"Exception lors de la récupération du profit/perte total: {e}")
            return 0

    async def fetch_total_profit_loss_percent(self):
        entry_id = self.config_entry.entry_id
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"http://localhost:5000/profit_loss/{entry_id}") as response:
                    if response.status == 200:
                        data = await response.json()
                        return data['summary']['total_profit_loss_percent']
                    else:
                        _LOGGER.error(f"Erreur lors de la récupération du pourcentage de profit/perte total: {response.status}")
                        return 0
        except Exception as e:
            _LOGGER.error(f"Exception lors de la récupération du pourcentage de profit/perte total: {e}")
            return 0

    async def fetch_total_value(self):
        entry_id = self.config_entry.entry_id
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"http://localhost:5000/profit_loss/{entry_id}") as response:
                    if response.status == 200:
                        data = await response.json()
                        return data['summary']['total_value']
                    else:
                        _LOGGER.error(f"Erreur lors de la récupération de la valeur totale: {response.status}")
                        return 0
        except Exception as e:
            _LOGGER.error(f"Exception lors de la récupération de la valeur totale: {e}")
            return 0

    async def fetch_crypto_data(self, crypto_id):
        
        crypto_attributes = load_crypto_attributes(self.config_entry.entry_id)
        

        # Adapter la logique pour gérer les deux cas
        crypto = next((c for c in self.config_entry.options.get("cryptos", []) 
                    if (isinstance(c, dict) and c.get("id") == crypto_id) or 
                        (isinstance(c, list) and len(c) > 1 and c[1] == crypto_id)), None)

        return {
            "crypto_id": crypto_id if crypto else None,
            "crypto_name": crypto["name"] if isinstance(crypto, dict) else (crypto[0] if isinstance(crypto, list) and len(crypto) > 0 else None)
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
                        _LOGGER.error(f"Erreur lors de la sauvegarde de la crypto {crypto_name} avec ID {crypto_id} dans la base de données.")
        except Exception as e:
            _LOGGER.error(f"Exception lors de la sauvegarde de la crypto {crypto_name} avec ID {crypto_id} dans la base de données: {e}")

class PortfolioCryptoSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, config_entry, sensor_type):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self.config_entry = config_entry
        self._sensor_type = sensor_type
        self._name = f"{config_entry.title} {sensor_type}"
        self._attributes = {
            "entry_id": config_entry.entry_id,
        }

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self.coordinator.data.get(self._sensor_type)

    @property
    def unique_id(self):
        return f"{self.config_entry.entry_id}_{self._sensor_type}"

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, self.config_entry.entry_id)},
            name=self.config_entry.title,
            manufacturer="Custom",
            model="Portfolio Crypto",
            sw_version="1.0",
            via_device=(DOMAIN, self.config_entry.entry_id),
        )

    @property
    def extra_state_attributes(self):
        return self._attributes

    async def async_update(self):
        self._attributes = {
            "entry_id": self.config_entry.entry_id,
        }
        await self.coordinator.async_request_refresh()

class CryptoSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, config_entry, crypto, sensor_type, crypto_data):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self.config_entry = config_entry
        self._crypto = crypto
        self._sensor_type = sensor_type
        self._name = f"{crypto['name']} {sensor_type}"
        self._attributes = {
            "crypto_id": crypto['id'],
            "crypto_name": crypto['name'],
        }
        

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        coordinator_data = self.coordinator.data
        data_crypto = coordinator_data.get(self._crypto['id'], {})
        retour = data_crypto.get(self._sensor_type, "unknown")
        return retour

    @property
    def unique_id(self):
        return f"{self.config_entry.entry_id}_{self._crypto['id']}_{self._sensor_type}"

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, self._crypto['id'])},
            name=self._crypto['name'],
            manufacturer="Custom",
            model="Portfolio Crypto",
            sw_version="1.0",
            via_device=(DOMAIN, self.config_entry.entry_id),
        )

    @property
    def extra_state_attributes(self):
        return self._attributes

    async def async_update(self):
        await self.coordinator.async_request_refresh()
        crypto = next((c for c in self.config_entry.options.get("cryptos", []) if c["id"] == self._crypto['id']), None)
        self._attributes.update({
            "crypto_id": crypto["id"] if crypto else None,
            "crypto_name": crypto["name"] if crypto else None,
        })
