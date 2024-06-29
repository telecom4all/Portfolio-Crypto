import logging
from datetime import timedelta, datetime
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo
import aiohttp
import async_timeout
import asyncio
from .const import DOMAIN, COINGECKO_API_URL
from .db import save_crypto, load_crypto_attributes

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
        crypto_data = crypto_attributes.get(crypto["id"], {})
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
        crypto_attributes = load_crypto_attributes(self.config_entry.entry_id)
        crypto = next((c for c in self.config_entry.options.get("cryptos", []) if c["id"] == crypto_id), None)
        return {
            "crypto_id": crypto["id"] if crypto else None,
            "crypto_name": crypto["name"] if crypto else None,
            **crypto_attributes.get(crypto_id, {
                "transactions": [],
                "total_investment": 0,
                "total_profit_loss": 0,
                "total_profit_loss_percent": 0,
                "total_value": 0,
            })
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
        self._attributes.update(crypto_data)

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
