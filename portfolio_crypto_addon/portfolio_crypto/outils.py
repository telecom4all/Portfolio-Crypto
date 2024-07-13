import aiohttp
import os
import logging

_LOGGER = logging.getLogger(__name__)

async def send_req_backend(url, payload=None, title='', method='post', form_data=None):
    try:
        async with aiohttp.ClientSession() as session:
            _LOGGER.info(f"Appel de l'URL {url} avec payload : {payload if payload else form_data}")

            supervisor_token = os.getenv("SUPERVISOR_TOKEN")
            headers = {
                "Authorization": f"Bearer {supervisor_token}",
            }

            if method in ['post', 'put']:
                if form_data:
                    async with session.request(method, url, data=form_data, headers=headers) as response:
                        response_text = await response.text()
                        _LOGGER.info(f"Statut de la réponse: {response.status}, Texte de la réponse: {response_text}")
                        if response.status == 200:
                            _LOGGER.info(f"Réponse 200 pour {title} : {response_text}")
                            return response
                        else:
                            _LOGGER.error(f"Échec pour la requête : {title}, code de statut: {response.status}, texte de la réponse: {response_text}")
                            return False
                else:
                    headers["Content-Type"] = "application/json"
                    async with session.request(method, url, json=payload, headers=headers) as response:
                        response_text = await response.text()
                        _LOGGER.info(f"Statut de la réponse: {response.status}, Texte de la réponse: {response_text}")
                        if response.status == 200:
                            _LOGGER.info(f"Réponse 200 pour {title} : {response_text}")
                            return response
                        else:
                            _LOGGER.error(f"Échec pour la requête : {title}, code de statut: {response.status}, texte de la réponse: {response_text}")
                            return False
            elif method == 'get':
                async with session.get(url, headers=headers) as response:
                    response_text = await response.text()
                    _LOGGER.info(f"Statut de la réponse: {response.status}, Texte de la réponse: {response_text}")
                    if response.status == 200:
                        _LOGGER.info(f"Réponse 200 pour {title} : {response_text}")
                        return response
                    else:
                        _LOGGER.error(f"Échec pour la requête : {title}, code de statut: {response.status}, texte de la réponse: {response_text}")
                        return False
            elif method == 'delete':
                async with session.delete(url, headers=headers) as response:
                    response_text = await response.text()
                    _LOGGER.info(f"Statut de la réponse: {response.status}, Texte de la réponse: {response_text}")
                    if response.status == 200:
                        _LOGGER.info(f"Réponse 200 pour {title} : {response_text}")
                        return response
                    else:
                        _LOGGER.error(f"Échec pour la requête : {title}, code de statut: {response.status}, texte de la réponse: {response_text}")
                        return False
    except Exception as e:
        _LOGGER.error(f"Erreur lors de l'appel de l'API: {e}")
        return False
