import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
import aiohttp
import os
from .const import DOMAIN
from .sensor import PortfolioCryptoCoordinator  # Assurez-vous d'importer correctement PortfolioCryptoCoordinator

_LOGGER = logging.getLogger(__name__)

# Configurer la journalisation pour écrire dans un fichier
log_handler = logging.FileHandler('/config/logs/integration.log')
log_handler.setLevel(logging.DEBUG)
log_formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
log_handler.setFormatter(log_formatter)
_LOGGER.addHandler(log_handler)

async def async_setup(hass: HomeAssistant, config: dict):
    """Configurer l'intégration via le fichier configuration.yaml (non utilisé ici)"""
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Configurer l'intégration via l'interface utilisateur"""
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    if entry.entry_id in hass.data[DOMAIN]:
        return False  # Entry déjà configurée

    coordinator = PortfolioCryptoCoordinator(hass, entry, update_interval=1)  # Fixe l'intervalle de mise à jour à 1 minute
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Initialiser la base de données pour le nouveau portfolio en appelant le service de l'addon
    if not entry.options.get("initialized", False):
        try:
            async with aiohttp.ClientSession() as session:
                supervisor_token = os.getenv("SUPERVISOR_TOKEN")
                headers = {
                    "Authorization": f"Bearer {supervisor_token}",
                    "Content-Type": "application/json",
                }
                url = "http://localhost:5000/initialize"
                _LOGGER.info(f"Appel de l'URL {url} avec l'ID d'entrée: {entry.entry_id}")
                async with session.post(url, json={"entry_id": entry.entry_id}, headers=headers) as response:
                    response_text = await response.text()
                    _LOGGER.info(f"Statut de la réponse: {response.status}, Texte de la réponse: {response_text}")
                    if response.status == 200:
                        _LOGGER.info(f"Base de données initialisée avec succès pour l'ID d'entrée: {entry.entry_id}")
                        hass.config_entries.async_update_entry(entry, options={**entry.options, "initialized": True})
                    else:
                        _LOGGER.error(f"Échec de l'initialisation de la base de données pour l'ID d'entrée: {entry.entry_id}, code de statut: {response.status}, texte de la réponse: {response_text}")
        except Exception as e:
            _LOGGER.error(f"Exception survenue lors de l'initialisation de la base de données pour l'ID d'entrée: {entry.entry_id}: {e}")

    await hass.config_entries.async_forward_entry_setup(entry, "sensor")

    async def async_add_crypto_service(call):
        """Service pour ajouter une nouvelle crypto-monnaie"""
        name = call.data.get("crypto_name")
        entry_id = call.data.get("entry_id")
        coordinator = hass.data[DOMAIN].get(entry_id)
        if coordinator:
            success = await coordinator.add_crypto(name)
            if not success:
                _LOGGER.error(f"Crypto {name} introuvable")

    hass.services.async_register(
        DOMAIN, "add_crypto", async_add_crypto_service
    )
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Décharger une entrée configurée"""
    if entry.entry_id in hass.data[DOMAIN]:
        await hass.config_entries.async_forward_entry_unload(entry, "sensor")
        hass.services.async_remove(DOMAIN, "add_crypto")
        hass.data[DOMAIN].pop(entry.entry_id)

    return True
