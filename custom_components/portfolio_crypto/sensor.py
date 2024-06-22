import logging
from datetime import timedelta
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, CoordinatorEntity
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    coordinator = PortfolioCryptoCoordinator(hass, config_entry)
    await coordinator.async_config_entry_first_refresh()

    entities = [
        PortfolioCryptoSensor(coordinator, config_entry, "transactions"),
        PortfolioCryptoSensor(coordinator, config_entry, "total_investment"),
        PortfolioCryptoSensor(coordinator, config_entry, "total_profit_loss"),
        PortfolioCryptoSensor(coordinator, config_entry, "total_profit_loss_percent"),
        PortfolioCryptoSensor(coordinator, config_entry, "total_value"),
    ]

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
        return {}

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
