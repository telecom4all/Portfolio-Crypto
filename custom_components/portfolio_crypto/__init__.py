import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import service
from .sensor import PortfolioCryptoCoordinator
from .const import DOMAIN
import aiohttp
import os

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict):
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    if entry.entry_id in hass.data[DOMAIN]:
        return False  # Entry already set up

    update_interval = entry.options.get("update_interval", 10)
    coordinator = PortfolioCryptoCoordinator(hass, entry, update_interval)
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Initialize the database for the new portfolio by calling the addon service
    if not entry.options.get("initialized", False):
        try:
            async with aiohttp.ClientSession() as session:
                supervisor_token = os.getenv("SUPERVISOR_TOKEN")
                headers = {
                    "Authorization": f"Bearer {supervisor_token}",
                    "Content-Type": "application/json",
                }
                url = "http://localhost:5000/initialize"
                _LOGGER.info(f"Calling URL {url} with entry ID: {entry.entry_id}")
                async with session.post(url, json={"entry_id": entry.entry_id}, headers=headers) as response:
                    response_text = await response.text()
                    _LOGGER.info(f"Response status: {response.status}, Response text: {response_text}")
                    if response.status == 200:
                        _LOGGER.info(f"Successfully initialized database for entry ID: {entry.entry_id}")
                        hass.config_entries.async_update_entry(entry, options={**entry.options, "initialized": True})
                    else:
                        _LOGGER.error(f"Failed to initialize database for entry ID: {entry.entry_id}, status code: {response.status}, response text: {response_text}")
        except Exception as e:
            _LOGGER.error(f"Exception occurred while initializing database for entry ID: {entry.entry_id}: {e}")

    await hass.config_entries.async_forward_entry_setup(entry, "sensor")

    async def async_add_crypto_service(call):
        name = call.data.get("crypto_name")
        entry_id = call.data.get("entry_id")
        coordinator = hass.data[DOMAIN].get(entry_id)
        if coordinator:
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
