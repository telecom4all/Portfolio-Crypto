import sqlite3
import time
import threading
import requests
import logging
from datetime import datetime
from .const import COINGECKO_API_URL, UPDATE_INTERVAL, RATE_LIMIT, PORT_APP, PATH_DB_BASE

# Configurer un logger spécifique pour price_updater
logger = logging.getLogger('price_updater')
logger.setLevel(logging.DEBUG)

# Créer un gestionnaire de fichiers pour enregistrer les logs
file_handler = logging.FileHandler('/config/portfolio_crypto/price_updater.log')
file_handler.setLevel(logging.DEBUG)

# Créer un formatteur et l'ajouter au gestionnaire
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

# Ajouter le gestionnaire au logger
logger.addHandler(file_handler)

COINGECKO_API_URL = "https://api.coingecko.com/api/v3/simple/price"

def get_crypto_list():
    try:
        conn = sqlite3.connect(f'{PATH_DB_BASE}/list_crypto.db')
        cursor = conn.cursor()
        cursor.execute('SELECT crypto_id FROM cryptos')
        cryptos = cursor.fetchall()
        conn.close()
        return [crypto[0] for crypto in cryptos]
    except Exception as e:
        logger.error(f"Error fetching crypto list: {e}")
        return []

def update_crypto_price(crypto_id):
    try:
        url = f"{COINGECKO_API_URL}?ids={crypto_id}&vs_currencies=usd"
        response = requests.get(url)
        if response.status_code == 200:
            price = response.json().get(crypto_id, {}).get('usd', 0)
            save_crypto_price(crypto_id, price)
            logger.info(f"Prix mis à jour pour {crypto_id}: {price}")
        else:
            logger.error(f"Failed to fetch price for {crypto_id}: {response.status_code}")
    except Exception as e:
        logger.error(f"Error updating price for {crypto_id}: {e}")

def save_crypto_price(crypto_id, price):
    try:
        conn = sqlite3.connect(f'{PATH_DB_BASE}/cache_prix_crypto.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                crypto_id TEXT,
                price REAL,
                timestamp TEXT
            )
        ''')
        cursor.execute('''
            INSERT INTO prices (crypto_id, price, timestamp)
            VALUES (?, ?, ?)
        ''', (crypto_id, price, datetime.now().isoformat()))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error saving price for {crypto_id}: {e}")

def price_updater():
    logger.info("Price updater thread has started running.")
    while True:
        try:
            cryptos = get_crypto_list()
            logger.info(f"Liste des cryptos récupérées: {cryptos}")
            for crypto_id in cryptos:
                logger.info(f"Mise à jour du prix pour {crypto_id}")
                update_crypto_price(crypto_id)
                time.sleep(60)  # Pause de 1 minute entre chaque mise à jour de crypto
        except Exception as e:
            logger.error(f"Error in price updater loop: {e}")

def start_price_updater_thread():
    logger.info("Initializing the price updater thread...")
    thread = threading.Thread(target=price_updater)
    thread.daemon = True
    thread.start()
    logger.info("Price updater thread initialized successfully.")
