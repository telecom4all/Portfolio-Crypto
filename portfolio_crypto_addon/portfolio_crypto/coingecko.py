import aiohttp
import os
import sqlite3
import logging
from .const import DOMAIN, COINGECKO_API_URL, COINGECKO_API_URL_PRICE, UPDATE_INTERVAL, RATE_LIMIT, UPDATE_INTERVAL_SENSOR, PORT_APP, PATH_DB_BASE

_LOGGER = logging.getLogger(__name__)

async def send_req_coingecko(url, title, params=None):
    try:
        async with aiohttp.ClientSession() as session:
            #_LOGGER.info(f"Appel de l'URL CoinGecko {url} avec params : {params}")

            async with session.get(url, params=params) as response:
                response_text = await response.text()
                #_LOGGER.info(f"Statut de la réponse: {response.status}, Texte de la réponse: {response_text}")
                if response.status == 200:
                    #_LOGGER.info(f"Réponse 200 pour {title} : {response_text}")
                    return response
                elif response.status == 429:
                    _LOGGER.warning("Limitation Api Coingecko reessayez dans 1 min")
                    return None  # or you can return a specific error object or code
                else:
                    _LOGGER.error(f"Échec pour la requete CoinGecko : {title}, code de statut: {response.status}, texte de la réponse: {response_text}")
                    return False
    except Exception as e:
        _LOGGER.error(f"Erreur lors de l'appel CoinGecko pour {title}: {e}")
        return False
    
async def fetch_crypto_id_from_coingecko(crypto_name_or_id):
    url = f"{COINGECKO_API_URL}?query={crypto_name_or_id}"
    
    response = await send_req_coingecko(url, "Fetch Crypto ID")
    if response and response.status == 200:
        try:
            result = await response.json()
            if isinstance(result, list):
                for coin in result:
                    if isinstance(coin, dict):
                        if coin.get('name', '').lower() == crypto_name_or_id.lower() or coin.get('id', '').lower() == crypto_name_or_id.lower():
                            return coin['id']
            elif isinstance(result, dict):
                if result.get('name', '').lower() == crypto_name_or_id.lower() or result.get('id', '').lower() == crypto_name_or_id.lower():
                    return result['id']
            elif isinstance(result, str):
                if result.lower() == crypto_name_or_id.lower():
                    return result
            else:
                _LOGGER.error("Unexpected response format from CoinGecko API")
                return None
        except Exception as e:
            _LOGGER.error(f"Erreur lors du traitement des données de l'API CoinGecko: {e}")
            return None
    else:
        _LOGGER.error("Error fetching CoinGecko data")
        return None
    
async def get_crypto_price(crypto_id):
    """Récupérer le prix actuel d'une crypto-monnaie"""
    conn = sqlite3.connect(f'{PATH_DB_BASE}/cache_prix_crypto.db')
    cursor = conn.cursor()
    cursor.execute('SELECT price FROM prices WHERE crypto_id = ?', (crypto_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return row[0]
    else:
        return 0

async def get_historical_price(crypto_id, date):
    """Récupérer le prix historique d'une crypto-monnaie pour une date donnée"""
    url = f"{COINGECKO_API_URL}/coins/{crypto_id}/history?date={date}"
    
    response = await send_req_coingecko(url, "Get Historical Price")
    if response and response.status == 200:
        try:
            data = await response.json()
            return data['market_data']['current_price']['usd']
        except (KeyError, Exception) as e:
            _LOGGER.error(f"Erreur lors de la récupération du prix historique pour {crypto_id} à la date {date}: {e}")
            return None
    else:
        _LOGGER.error(f"Erreur lors de la récupération du prix historique pour {crypto_id} à la date {date}")
        return None