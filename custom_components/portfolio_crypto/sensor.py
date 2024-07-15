import logging
from datetime import timedelta, datetime
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers import entity_registry as er, device_registry as dr
import aiohttp
import async_timeout
import asyncio
import os
from .const import DOMAIN, COINGECKO_API_URL, UPDATE_INTERVAL, RATE_LIMIT, UPDATE_INTERVAL_SENSOR, PORT_APP
from .db import save_crypto, load_crypto_attributes, delete_crypto_db
import ast
from .outils import send_req_backend
from .coingecko import send_req_coingecko, fetch_crypto_id_from_coingecko, get_crypto_price


_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    coordinator = PortfolioCryptoCoordinator(hass, config_entry, update_interval=UPDATE_INTERVAL_SENSOR)  # Fixing update interval to 1 minute
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

        for sensor_type in ['investment', 'current_value', 'profit_loss', 'profit_loss_percent', 'transactions_count', 'average_price', 'current_price', 'total_tokens']:
            entities.append(CryptoSensor(coordinator, config_entry, {"name": crypto_name, "id": crypto_id}, sensor_type, crypto_data))

    async_add_entities(entities)



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

            # Calcul du prix moyen
            total_quantity = 0
            total_cost = 0
            for transaction in crypto_transactions:
                if transaction[5] == 'buy':
                    quantity = transaction[3]
                    price = transaction[4]
                    total_quantity += quantity
                    total_cost += price
                elif transaction[5] == 'sell':
                    quantity = transaction[3]
                    total_quantity -= quantity

            if total_quantity > 0:
                average_price = total_cost / total_quantity
            else:
                average_price = 0

            current_price = await get_crypto_price(crypto_id)

            crypto_data["transactions_count"] = len(crypto_transactions)
            crypto_data["average_price"] = average_price
            crypto_data["current_price"] = current_price
            crypto_data["total_tokens"] = total_quantity


            data[crypto_id] = {
                "crypto_id": crypto_id,
                "crypto_name": crypto_name,
                "investment": crypto_data.get("investment"),
                "current_value": crypto_data.get("current_value"),
                "profit_loss": crypto_data.get("profit_loss"),
                "profit_loss_percent": crypto_data.get("profit_loss_percent"),
                "transactions_count": crypto_data.get("transactions_count"),
                "average_price": crypto_data.get("average_price"),
                "current_price": crypto_data.get("current_price"),
                "total_tokens": crypto_data.get("total_tokens")
            }
        _LOGGER.info(f"Fetched data: {data}")
        _LOGGER.info("New data fetched successfully")
        return data



    async def fetch_crypto_profit_loss(self, crypto_id):
        entry_id = self.config_entry.entry_id
        url = f"http://localhost:{PORT_APP}/crypto_profit_loss/{entry_id}/{crypto_id}"
        response = await send_req_backend(url, {}, "Fetch Crypto Profit/Loss", method='get')
        if response and response.status == 200:
            return await response.json()
        else:
            return {
                "investment": 0,
                "current_value": 0,
                "profit_loss": 0,
                "profit_loss_percent": 0
            }

    async def fetch_crypto_transactions(self, crypto_id):
        entry_id = self.config_entry.entry_id
        url = f"http://localhost:{PORT_APP}/transactions/{entry_id}/{crypto_id}"
        response = await send_req_backend(url, {}, "Fetch Crypto Transactions", method='get')
        if response and response.status == 200:
            return await response.json()
        else:
            return []
        
    async def fetch_transactions(self):
        entry_id = self.config_entry.entry_id
        url = f"http://localhost:{PORT_APP}/transactions/{entry_id}"
        response = await send_req_backend(url, {}, "Fetch Transactions", method='get')
        if response and response.status == 200:
            return await response.json()
        else:
            return []

    async def fetch_total_investment(self):
        entry_id = self.config_entry.entry_id
        url = f"http://localhost:{PORT_APP}/profit_loss/{entry_id}"
        response = await send_req_backend(url, {}, "Fetch Total Investment", method='get')
        if response and response.status == 200:
            data = await response.json()
            return data['summary']['total_investment']
        else:
            return 0

    async def fetch_total_profit_loss(self):
        entry_id = self.config_entry.entry_id
        url = f"http://localhost:{PORT_APP}/profit_loss/{entry_id}"
        response = await send_req_backend(url, {}, "Fetch Total Profit/Loss", method='get')
        if response and response.status == 200:
            data = await response.json()
            return data['summary']['total_profit_loss']
        else:
            return 0

    async def fetch_total_profit_loss_percent(self):
        entry_id = self.config_entry.entry_id
        url = f"http://localhost:{PORT_APP}/profit_loss/{entry_id}"
        response = await send_req_backend(url, {}, "Fetch Total Profit/Loss Percent", method='get')
        if response and response.status == 200:
            data = await response.json()
            return data['summary']['total_profit_loss_percent']
        else:
            return 0

    async def fetch_total_value(self):
        entry_id = self.config_entry.entry_id
        url = f"http://localhost:{PORT_APP}/profit_loss/{entry_id}"
        response = await send_req_backend(url, {}, "Fetch Total Value", method='get')
        if response and response.status == 200:
            data = await response.json()
            return data['summary']['total_value']
        else:
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

            # Vérifiez que la structure est correcte
            valid_cryptos = [crypto for crypto in cryptos if isinstance(crypto, dict) and "id" in crypto]

            if any((isinstance(crypto, dict) and crypto.get("id") == crypto_id) or 
                (isinstance(crypto, list) and len(crypto) > 1 and crypto[1] == crypto_id) for crypto in valid_cryptos):
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
        return False

    async def fetch_crypto_id(self, crypto_name):
        return await fetch_crypto_id_from_coingecko(crypto_name)

    async def save_crypto_to_db(self, entry_id, crypto_name, crypto_id):
        url = f"http://localhost:{PORT_APP}/save_crypto"
        payload = {
            "entry_id": entry_id,
            "crypto_name": crypto_name,
            "crypto_id": crypto_id
        }
        await send_req_backend(url, payload, f"Save Crypto {crypto_name} with ID {crypto_id}")


    async def delete_crypto(self, crypto_id):
        entry_id = self.config_entry.entry_id
        _LOGGER.info(f"Tentative de suppression de la crypto avec ID: {crypto_id}")

        # Supprimer la crypto de la base de données
        success = delete_crypto_db(entry_id, crypto_id)
        if not success:
            _LOGGER.error(f"Échec de la suppression de la crypto avec ID: {crypto_id} de la base de données")
            return False

        _LOGGER.info(f"Crypto avec ID: {crypto_id} supprimée de la base de données")

        # Supprimer la crypto de la configuration
        cryptos = self.config_entry.options.get("cryptos", [])
        updated_cryptos = [crypto for crypto in cryptos if crypto["id"] != crypto_id]
        self.hass.config_entries.async_update_entry(self.config_entry, options={**self.config_entry.options, "cryptos": updated_cryptos})

        _LOGGER.info(f"Crypto avec ID: {crypto_id} supprimée de la configuration")

        # Supprimer les entités de Home Assistant
        entity_registry = er.async_get(self.hass)
        device_registry = dr.async_get(self.hass)

        # Trouver toutes les entités et l'appareil associé à la crypto_id
        entries = er.async_entries_for_config_entry(entity_registry, self.config_entry.entry_id)
        for entry in entries:
            if entry.unique_id.startswith(f"{self.config_entry.entry_id}_{crypto_id}"):
                _LOGGER.info(f"Suppression de l'entité avec ID: {entry.entity_id}")
                # Supprimer l'entité
                entity_registry.async_remove(entry.entity_id)

        # Forcer la suppression de l'appareil associé à cette crypto_id
        devices = dr.async_entries_for_config_entry(device_registry, self.config_entry.entry_id)
        for device in devices:
            if device.name == crypto_id:
                _LOGGER.info(f"Suppression de l'appareil avec ID: {device.id}")
                device_registry.async_remove_device(device.id)

        # Attendre un court instant pour s'assurer que les suppressions sont complètes
        await asyncio.sleep(1)
        
        # Recharger l'intégration pour mettre à jour les entités restantes
        await self.hass.config_entries.async_reload(self.config_entry.entry_id)

        _LOGGER.info(f"Rechargement de l'intégration pour entry_id: {self.config_entry.entry_id}")

        return True
    
class PortfolioCryptoSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, config_entry, sensor_type):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self.config_entry = config_entry
        self._sensor_type = sensor_type
        portfolio_name = config_entry.title.replace(" ", "_")  # Replace spaces with underscores
        self._name = f"{portfolio_name} {sensor_type}"
        self._attr_name = f"{portfolio_name} {sensor_type.replace('_', ' ').title()}"
        self._attr_unique_id = f"{portfolio_name}_{sensor_type}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            name=config_entry.title,
            manufacturer="Telecom4all",
            model="Portfolio Crypto",
        )
        self._attributes = {
            "entry_id": config_entry.entry_id,
        }

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        value = self.coordinator.data.get(self._sensor_type)
        return self._format_value(value)

    @property
    def unique_id(self):
        return self._attr_unique_id

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, self.config_entry.entry_id)},
            name=self.config_entry.title,
            manufacturer="Telecom4all",
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

    def _format_value(self, value):
        if isinstance(value, (float, int)):
            return f"{value:.4f}"
        return value
    
class CryptoSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, config_entry, crypto, sensor_type, crypto_data):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self.config_entry = config_entry
        self._crypto = crypto
        self._sensor_type = sensor_type
        portfolio_name = config_entry.title.replace(" ", "_")  # Replace spaces with underscores
        self._attr_unique_id = f"{portfolio_name}_{crypto['id']}_{sensor_type}"
        self._attr_name = f"{portfolio_name} {crypto['name']} {sensor_type.replace('_', ' ').title()}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{config_entry.entry_id}_{crypto['id']}")},
            name=f"{config_entry.title} {crypto['name']}",
            manufacturer="Telecom4all",
            model="Crypto",
        )
        self._attributes = {
            "crypto_id": crypto['id'],
            "crypto_name": crypto['name'],
        }
        
    @property
    def icon(self):
        icon_value = "mdi:currency-usd-circle"  # Icône globale pour tous les appareils
        _LOGGER.debug(f"Setting icon for {self._name} to {icon_value}")
        return icon_value
    
    @property
    def name(self):
        return self._attr_name

    @property
    def state(self):
        coordinator_data = self.coordinator.data
        data_crypto = coordinator_data.get(self._crypto['id'], {})
        value = data_crypto.get(self._sensor_type, "unknown")
        return self._format_value(value)

    @property
    def unique_id(self):
        return self._attr_unique_id

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, self._crypto['id'])},
            name=self._crypto['name'],
            manufacturer="Telecom4all",
            model="Crypto",
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

    def _format_value(self, value):
        if isinstance(value, (float, int)):
            return f"{value:.4f}"
        return value
