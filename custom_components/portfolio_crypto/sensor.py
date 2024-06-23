import logging
from datetime import timedelta
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo
import aiohttp
import async_timeout
import asyncio  # Ajoutez cette ligne
from .const import DOMAIN, COINGECKO_API_URL

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    coordinator = PortfolioCryptoCoordinator(hass, config_entry)
    await coordinator.async_config_entry_first_refresh()

    entities = []

    # Add main portfolio sensors
    entities.append(PortfolioCryptoSensor(coordinator, config_entry, "transactions"))
    entities.append(PortfolioCryptoSensor(coordinator, config_entry, "total_investment"))
    entities.append(PortfolioCryptoSensor(coordinator, config_entry, "total_profit_loss"))
    entities.append(PortfolioCryptoSensor(coordinator, config_entry, "total_profit_loss_percent"))
    entities.append(PortfolioCryptoSensor(coordinator, config_entry, "total_value"))

    # Add sensors for each cryptocurrency in the portfolio
    cryptos = config_entry.data.get("cryptos", [])
    for crypto in cryptos:
        entities.append(CryptoSensor(coordinator, config_entry, crypto, "transactions"))
        entities.append(CryptoSensor(coordinator, config_entry, crypto, "total_investment"))
        entities.append(CryptoSensor(coordinator, config_entry, crypto, "total_profit_loss"))
        entities.append(CryptoSensor(coordinator, config_entry, crypto, "total_profit_loss_percent"))
        entities.append(CryptoSensor(coordinator, config_entry, crypto, "total_value"))

    async_add_entities(entities)

class PortfolioCryptoCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, config_entry):
        super().__init__(
            hass,
            _LOGGER,
            name="PortfolioCrypto",
            update_interval=timedelta(minutes=1),
        )
        self.config_entry = config_entry

    async def _async_update_data(self):
        # Fetch data from API or database
        data = {}
        # Update data for main portfolio
        data["transactions"] = await self.fetch_transactions()
        data["total_investment"] = await self.fetch_total_investment()
        data["total_profit_loss"] = await self.fetch_total_profit_loss()
        data["total_profit_loss_percent"] = await self.fetch_total_profit_loss_percent()
        data["total_value"] = await self.fetch_total_value()
        # Update data for each crypto
        for crypto in self.config_entry.data.get("cryptos", []):
            crypto_data = await self.fetch_crypto_data(crypto["id"])
            data[crypto["id"]] = crypto_data
        return data

    async def fetch_transactions(self):
        # Fetch transactions data
        return []

    async def fetch_total_investment(self):
        # Fetch total investment data
        return 0

    async def fetch_total_profit_loss(self):
        # Fetch total profit/loss data
        return 0

    async def fetch_total_profit_loss_percent(self):
        # Fetch total profit/loss percent data
        return 0

    async def fetch_total_value(self):
        # Fetch total value data
        return 0

    async def fetch_crypto_data(self, crypto_id):
        # Fetch data for a specific crypto
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
            cryptos = self.config_entry.data.get("cryptos", [])
            cryptos.append({"name": crypto_name, "id": crypto_id})
            self.hass.config_entries.async_update_entry(self.config_entry, data={**self.config_entry.data, "cryptos": cryptos})

            # Create entities for the new crypto
            self.hass.async_add_job(
                self.hass.config_entries.async_forward_entry_setup(self.config_entry, "sensor")
            )
            return True
        return False

    async def fetch_crypto_id(self, crypto_name):
        async with aiohttp.ClientSession() as session:
            try:
                with async_timeout.timeout(10):
                    async with session.get(COINGECKO_API_URL) as response:
                        result = await response.json()
                        for coin in result:
                            if coin['name'].lower() == crypto_name.lower():
                                return coin['id']
            except (aiohttp.ClientError, asyncio.TimeoutError):
                _LOGGER.error("Error fetching CoinGecko data")
        return None

class PortfolioCryptoSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, config_entry, sensor_type):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self.config_entry = config_entry
        self._sensor_type = sensor_type
        self._name = f"{config_entry.title} {sensor_type}"

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
        )

class CryptoSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, config_entry, crypto, sensor_type):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self.config_entry = config_entry
        self._crypto = crypto
        self._sensor_type = sensor_type
        self._name = f"{crypto['name']} {sensor_type}"

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self.coordinator.data.get(self._crypto['id'], {}).get(self._sensor_type)

    @property
    def unique_id(self):
        return f"{self.config_entry.entry_id}_{self._crypto['id']}_{self._sensor_type}"

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, self.config_entry.entry_id)},
            name=self.config_entry.title,
            manufacturer="Custom",
            model="Portfolio Crypto",
        )
