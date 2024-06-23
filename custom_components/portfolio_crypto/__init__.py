import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import service
from .sensor import PortfolioCryptoCoordinator
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict):
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    hass.data.setdefault(DOMAIN, {})
    coordinator = PortfolioCryptoCoordinator(hass, entry)
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Utiliser await pour appeler async_forward_entry_setup
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
    await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    hass.services.async_remove(DOMAIN, "add_crypto")
    return True
