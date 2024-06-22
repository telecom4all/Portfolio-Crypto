import logging
import requests
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_track_time_interval
from datetime import timedelta

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Setup sensor platform."""
    # Initialize the main sensors
    async_add_entities([
        CryptoTransactionsSensor(hass, config_entry.entry_id),
        TotalInvestmentSensor(hass, config_entry.entry_id),
        TotalValueSensor(hass, config_entry.entry_id),
        TotalProfitLossSensor(hass, config_entry.entry_id),
        TotalProfitLossPercentSensor(hass, config_entry.entry_id)
    ])

    # Initialize the list of crypto sensors
    hass.data.setdefault('crypto_sensors', {})

    # Fetch and add individual crypto sensors
    await update_individual_crypto_sensors(hass, config_entry, async_add_entities)

    # Setup a listener to periodically update the sensors
    async_track_time_interval(hass, lambda _: update_individual_crypto_sensors(hass, config_entry, async_add_entities), timedelta(minutes=5))

async def update_individual_crypto_sensors(hass, config_entry, async_add_entities):
    """Fetch individual crypto sensors and add or update them."""
    try:
        response = await hass.async_add_executor_job(
            requests.get, 'http://localhost:5000/profit_loss'
        )
        if response.status_code == 200:
            data = response.json()
            new_sensors = []
            existing_sensors = hass.data['crypto_sensors']

            for detail in data['details']:
                sensor_id = f"{config_entry.entry_id}_{detail['crypto_id']}_investment"
                if sensor_id not in existing_sensors:
                    new_sensors.append(CryptoInvestmentSensor(hass, config_entry.entry_id, detail))
                    new_sensors.append(CryptoCurrentValueSensor(hass, config_entry.entry_id, detail))
                    new_sensors.append(CryptoProfitLossDetailSensor(hass, config_entry.entry_id, detail))
                    new_sensors.append(CryptoProfitLossPercentDetailSensor(hass, config_entry.entry_id, detail))
                else:
                    existing_sensors[sensor_id].update_data(detail)

            if new_sensors:
                async_add_entities(new_sensors)
                for sensor in new_sensors:
                    hass.data['crypto_sensors'][sensor.unique_id] = sensor

            await remove_unused_sensors(hass, config_entry, data['details'])

    except requests.exceptions.ConnectionError as e:
        _LOGGER.error(f"Error connecting to Flask server: {e}")

async def remove_unused_sensors(hass, config_entry, current_details):
    """Remove sensors for cryptos with no transactions."""
    current_crypto_ids = {detail['crypto_id'] for detail in current_details}
    sensors_to_remove = []

    for sensor_id, sensor in hass.data.get('crypto_sensors', {}).items():
        if sensor._crypto_id not in current_crypto_ids:
            sensors_to_remove.append(sensor)

    if sensors_to_remove:
        for sensor in sensors_to_remove:
            await sensor.async_remove()
            hass.data['crypto_sensors'].pop(sensor.unique_id)

class CryptoTransactionsSensor(Entity):
    def __init__(self, hass, entry_id):
        self._state = None
        self._attributes = {}
        self.hass = hass
        self._entry_id = entry_id

    @property
    def name(self):
        return 'Crypto Transactions'

    @property
    def state(self):
        return self._state

    @property
    def unique_id(self):
        return f"{self._entry_id}_crypto_transactions"

    @property
    def extra_state_attributes(self):
        return self._attributes

    async def async_update(self):
        _LOGGER.debug("Updating Crypto Transactions Sensor")
        try:
            response = await self.hass.async_add_executor_job(
                requests.get, 'http://localhost:5000/transactions'
            )
            if response.status_code == 200):
                data = response.json()
                self._state = len(data)
                self._attributes = {"transactions": data}
                _LOGGER.debug(f"Crypto Transactions Sensor updated: {data}")
            else:
                _LOGGER.error(f"Error fetching data: {response.status_code}")
        except Exception as e:
            _LOGGER.error(f"Exception in CryptoTransactionsSensor: {e}")

# Define additional sensor classes
class TotalInvestmentSensor(Entity):
    def __init__(self, hass, entry_id):
        self._state = None
        self.hass = hass
        self._entry_id = entry_id

    @property
    def name(self):
        return 'Total Investment'

    @property
    def state(self):
        return self._state

    @property
    def unique_id(self):
        return f"{self._entry_id}_total_investment"

    async def async_update(self):
        _LOGGER.debug("Updating Total Investment Sensor")
        try:
            response = await self.hass.async_add_executor_job(
                requests.get, 'http://localhost:5000/profit_loss'
            )
            if response.status_code == 200):
                data = response.json()
                self._state = data['summary']['total_investment']
                _LOGGER.debug(f"Total Investment Sensor updated: {self._state}")
            else:
                _LOGGER.error(f"Error fetching data: {response.status_code}")
        except Exception as e:
            _LOGGER.error(f"Exception in TotalInvestmentSensor: {e}")

class TotalValueSensor(Entity):
    def __init__(self, hass, entry_id):
        self._state = None
        self.hass = hass
        self._entry_id = entry_id

    @property
    def name(self):
        return 'Total Value'

    @property
    def state(self):
        return self._state

    @property
    def unique_id(self):
        return f"{self._entry_id}_total_value"

    async def async_update(self):
        _LOGGER.debug("Updating Total Value Sensor")
        try:
            response = await self.hass.async_add_executor_job(
                requests.get, 'http://localhost:5000/profit_loss'
            )
            if response.status_code == 200):
                data = response.json()
                self._state = data['summary']['total_value']
                _LOGGER.debug(f"Total Value Sensor updated: {self._state}")
            else:
                _LOGGER.error(f"Error fetching data: {response.status_code}")
        except Exception as e:
            _LOGGER.error(f"Exception in TotalValueSensor: {e}")

class TotalProfitLossSensor(Entity):
    def __init__(self, hass, entry_id):
        self._state = None
        self.hass = hass
        self._entry_id = entry_id

    @property
    def name(self):
        return 'Total Profit Loss'

    @property
    def state(self):
        return self._state

    @property
    def unique_id(self):
        return f"{self._entry_id}_total_profit_loss"

    async def async_update(self):
        _LOGGER.debug("Updating Total Profit Loss Sensor")
        try:
            response = await self.hass.async_add_executor_job(
                requests.get, 'http://localhost:5000/profit_loss'
            )
            if response.status_code == 200):
                data = response.json()
                self._state = data['summary']['total_profit_loss']
                _LOGGER.debug(f"Total Profit Loss Sensor updated: {self._state}")
            else:
                _LOGGER.error(f"Error fetching data: {response.status_code}")
        except Exception as e:
            _LOGGER.error(f"Exception in TotalProfitLossSensor: {e}")

class TotalProfitLossPercentSensor(Entity):
    def __init__(self, hass, entry_id):
        self._state = None
        self.hass = hass
        self._entry_id = entry_id

    @property
    def name(self):
        return 'Total Profit Loss Percent'

    @property
    def state(self):
        return self._state

    @property
    def unique_id(self):
        return f"{self._entry_id}_total_profit_loss_percent"

    async def async_update(self):
        _LOGGER.debug("Updating Total Profit Loss Percent Sensor")
        try:
            response = await self.hass.async_add_executor_job(
                requests.get, 'http://localhost:5000/profit_loss'
            )
            if response.status_code == 200):
                data = response.json()
                self._state = data['summary']['total_profit_loss_percent']
                _LOGGER.debug(f"Total Profit Loss Percent Sensor updated: {self._state}")
            else:
                _LOGGER.error(f"Error fetching data: {response.status_code}")
        except Exception as e:
            _LOGGER.error(f"Exception in TotalProfitLossPercentSensor: {e}")

# Individual Crypto Sensors
class CryptoInvestmentSensor(Entity):
    def __init__(self, hass, entry_id, detail):
        self._state = detail['investment']
        self._attributes = detail
        self.hass = hass
        self._entry_id = entry_id
        self._crypto_id = detail['crypto_id']

    @property
    def name(self):
        return f"Investment {self._crypto_id}"

    @property
    def state(self):
        return self._state

    @property
    def unique_id(self):
        return f"{self._entry_id}_{self._crypto_id}_investment"

    @property
    def extra_state_attributes(self):
        return self._attributes

    def update_data(self, detail):
        self._state = detail['investment']
        self._attributes = detail

class CryptoCurrentValueSensor(Entity):
    def __init__(self, hass, entry_id, detail):
        self._state = detail['current_value']
        self._attributes = detail
        self.hass = hass
        self._entry_id = entry_id
        self._crypto_id = detail['crypto_id']

    @property
    def name(self):
        return f"Current Value {self._crypto_id}"

    @property
    def state(self):
        return self._state

    @property
    def unique_id(self):
        return f"{self._entry_id}_{self._crypto_id}_current_value"

    @property
    def extra_state_attributes(self):
        return self._attributes

    def update_data(self, detail):
        self._state = detail['current_value']
        self._attributes = detail

class CryptoProfitLossDetailSensor(Entity):
    def __init__(self, hass, entry_id, detail):
        self._state = detail['profit_loss']
        self._attributes = detail
        self.hass = hass
        self._entry_id = entry_id
        self._crypto_id = detail['crypto_id']

    @property
    def name(self):
        return f"Profit Loss {self._crypto_id}"

    @property
    def state(self):
        return self._state

    @property
    def unique_id(self):
        return f"{self._entry_id}_{self._crypto_id}_profit_loss"

    @property
    def extra_state_attributes(self):
        return self._attributes

    def update_data(self, detail):
        self._state = detail['profit_loss']
        self._attributes = detail

class CryptoProfitLossPercentDetailSensor(Entity):
    def __init__(self, hass, entry_id, detail):
        self._state = detail['profit_loss_percent']
        self._attributes = detail
        self.hass = hass
        self._entry_id = entry_id
        self._crypto_id = detail['crypto_id']

    @property
    def name(self):
        return f"Profit Loss Percent {self._crypto_id}"

    @property
    def state(self):
        return self._state

    @property
    def unique_id(self):
        return f"{self._entry_id}_{self._crypto_id}_profit_loss_percent"

    @property
    def extra_state_attributes(self):
        return self._attributes

    def update_data(self, detail):
        self._state = detail['profit_loss_percent']
        self._attributes = detail
