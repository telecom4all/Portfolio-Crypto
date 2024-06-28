import logging
from datetime import timedelta, datetime
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo
import aiohttp
import async_timeout
import asyncio
from .const import DOMAIN, COINGECKO_API_URL
from .db import save_crypto, load_crypto_attributes, get_cryptos

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
    cryptos = get_cryptos(config_entry.entry_id)
    crypto_attributes = load_crypto_attributes(config_entry.entry_id)
    for crypto in cryptos:
        crypto_data = crypto_attributes.get(crypto[1], {})
        # Create a new device for each cryptocurrency
        entities.append(CryptoSensor(coordinator, config_entry, crypto, "transactions", crypto_data))
        entities.append(CryptoSensor(coordinator, config_entry, crypto, "total_investment", crypto_data))
        entities.append(CryptoSensor(coordinator, config_entry, crypto, "total_profit_loss", crypto_data))
        entities.append(CryptoSensor(coordinator, config_entry, crypto, "total_profit_loss_percent", crypto_data))
        entities.append(CryptoSensor(coordinator, config_entry, crypto, "total_value", crypto_data))

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

        # Fetch data from the database
        transactions = self.fetch_transactions_data()
        total_investment = self.fetch_total_investment_data()
        total_profit_loss = self.fetch_total_profit_loss_data()
        total_profit_loss_percent = self.fetch_total_profit_loss_percent_data()
        total_value = self.fetch_total_value_data()

        # Fetch data for each cryptocurrency
        cryptos = get_cryptos(self.config_entry.entry_id)
        crypto_data = {}
        for crypto in cryptos:
            crypto_data[crypto[1]] = await self.fetch_crypto_data(crypto[1])

        return {
            "transactions": transactions,
            "total_investment": total_investment,
            "total_profit_loss": total_profit_loss,
            "total_profit_loss_percent": total_profit_loss_percent,
            "total_value": total_value,
            "crypto_data": crypto_data
        }

    async def fetch_crypto_data(self, crypto_id):
        url = f"{COINGECKO_API_URL}/coins/{crypto_id}"
        async with aiohttp.ClientSession() as session:
            async with async_timeout.timeout(10):
                async with session.get(url) as response:
                    if response.status != 200:
                        _LOGGER.error(f"Error fetching data for crypto ID: {crypto_id}. Status: {response.status}")
                        return None
                    data = await response.json()
                    return data

    def fetch_transactions_data(self):
        return load_crypto_attributes(self.config_entry.entry_id)

    def fetch_total_investment_data(self):
        # Calculer l'investissement total
        transactions = self.fetch_transactions_data()
        total_investment = sum(
            transaction['price_usd'] * transaction['quantity']
            for transaction in transactions
            if transaction['transaction_type'] == 'buy'
        )
        return total_investment

    def fetch_total_profit_loss_data(self):
        # Calculer le profit/perte total
        transactions = self.fetch_transactions_data()
        total_investment = self.fetch_total_investment_data()
        current_value = self.fetch_total_value_data()
        total_profit_loss = current_value - total_investment
        return total_profit_loss

    def fetch_total_profit_loss_percent_data(self):
        # Calculer le pourcentage de profit/perte
        total_investment = self.fetch_total_investment_data()
        total_profit_loss = self.fetch_total_profit_loss_data()
        if total_investment == 0:
            return 0
        return (total_profit_loss / total_investment) * 100

    def fetch_total_value_data(self):
        # Calculer la valeur totale du portefeuille
        crypto_data = self.data["crypto_data"]
        total_value = sum(
            crypto['market_data']['current_price']['usd'] * self.fetch_transactions_data()[crypto_id]['quantity']
            for crypto_id, crypto in crypto_data.items()
        )
        return total_value

class PortfolioCryptoSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, config_entry, sensor_type):
        super().__init__(coordinator)
        self.config_entry = config_entry
        self.sensor_type = sensor_type
        self._attr_unique_id = f"{config_entry.entry_id}_{sensor_type}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            name="Portfolio Crypto",
            manufacturer="Your Name",
        )

    @property
    def name(self):
        return f"Portfolio {self.sensor_type.replace('_', ' ').title()}"

    @property
    def state(self):
        return self.coordinator.data[self.sensor_type]

class CryptoSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, config_entry, crypto, sensor_type, crypto_data):
        super().__init__(coordinator)
        self.config_entry = config_entry
        self.crypto = crypto
        self.sensor_type = sensor_type
        self.crypto_data = crypto_data
        self._attr_unique_id = f"{config_entry.entry_id}_{crypto[1]}_{sensor_type}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{config_entry.entry_id}_{crypto[1]}")},
            name=f"Portfolio {crypto_data['crypto_name']}",
            manufacturer="Your Name",
        )

    @property
    def name(self):
        return f"{self.crypto_data['crypto_name']} {self.sensor_type.replace('_', ' ').title()}"

    @property
    def state(self):
        return self.coordinator.data["crypto_data"][self.crypto[1]][self.sensor_type]
