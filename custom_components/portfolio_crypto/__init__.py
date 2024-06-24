import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import service
from .sensor import PortfolioCryptoCoordinator
from .const import DOMAIN
from .portfolio_crypto import initialize_new_portfolio

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict):
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    if entry.entry_id in hass.data[DOMAIN]:
        return False  # Entry already set up

    coordinator = PortfolioCryptoCoordinator(hass, entry)
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Initialize the database for the new portfolio
    initialize_new_portfolio(entry.entry_id)

    await hass.config_entries.async_forward_entry_setup(entry, "sensor")

    async def async_add_crypto_service(call):
        name = call.data.get("crypto_name")
        success = await coordinator.add_crypto(name)
        if not success:
            _LOGGER.error(f"Crypto {name} not found")

    hass.services.async_register(
        DOMAIN, "add_crypto", async_add_crypto_service
    )
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    if entry.entry_id in hass.data[DOMAIN]:
        await hass.config_entries.async_forward_entry_unload(entry, "sensor")
        hass.services.async_remove(DOMAIN, "add_crypto")
        hass.data[DOMAIN].pop(entry.entry_id)

    return True
