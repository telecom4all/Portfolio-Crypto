import aiohttp
import os
import logging

_LOGGER = logging.getLogger(__name__)


async def send_req_backend(url, payload, title):
    try:
        async with aiohttp.ClientSession() as session:
            _LOGGER.info(f"Appel de l'URL {url} avec payload : {payload}")

            supervisor_token = os.getenv("SUPERVISOR_TOKEN")
            headers = {
                "Authorization": f"Bearer {supervisor_token}",
                "Content-Type": "application/json",
            }            
            
            async with session.post(url, json=payload, headers=headers) as response:
                response_text = await response.text()
                _LOGGER.info(f"Statut de la réponse: {response.status}, Texte de la réponse: {response_text}")
                if response.status == 200:
                    _LOGGER.info(f"Réponse 200 pour {title} : {response_text}")
                    return  response
                else:
                    _LOGGER.error(f"Échec pour la requete : {title}, code de statut: {response.status}, texte de la réponse: {response_text}")
                    return False
        
        
    except Exception as e:
        logging.error(f"Erreur lors de l'importation de la base de données: {e}")
        return False
