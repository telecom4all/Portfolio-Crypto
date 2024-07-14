# price_updater.py

import sqlite3
import time
#import threading
import requests
import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from .const import COINGECKO_API_URL, UPDATE_INTERVAL, RATE_LIMIT, PORT_APP, PATH_DB_BASE, UPDATE_INTERVAL_PRICE_UPDATER

# Configurer un logger spécifique pour price_updater
logger = logging.getLogger('price_updater')
logger.setLevel(logging.INFO)

# Créer un gestionnaire de fichiers pour enregistrer les logs
file_handler = logging.FileHandler('/config/portfolio_crypto/price_updater.log')
file_handler.setLevel(logging.INFO)

# Créer un formatteur et l'ajouter au gestionnaire
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

# Ajouter le gestionnaire au logger
logger.addHandler(file_handler)

def get_crypto_list():
    conn = sqlite3.connect(f'{PATH_DB_BASE}/list_crypto.db')
    cursor = conn.cursor()
    cursor.execute('SELECT crypto_id FROM cryptos')
    cryptos = cursor.fetchall()
    conn.close()
    return [crypto[0] for crypto in cryptos]

def update_crypto_price(crypto_id):
    try:
        url = f"{COINGECKO_API_URL}?ids={crypto_id}&vs_currencies=usd"
        logger.info(f"URL PRICE UPDATER {url}")
        response = requests.get(url)
        if response.status_code == 200:
            price = response.json().get(crypto_id, {}).get('usd', 0)
            if price:
                logger.info(f"Prix récupéré pour {crypto_id}: {price}")
                save_crypto_price(crypto_id, price)
            else:
                logger.error(f"Prix non trouvé dans la réponse pour {crypto_id}: {response.json()}")
        else:
            logger.error(f"Échec de la récupération du prix pour {crypto_id}: {response.status_code}")
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour du prix pour {crypto_id}: {e}")


def save_crypto_price(crypto_id, price):
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

def price_updater():
    logger.info("Starting price updater...")
    while True:
        try:
            cryptos = get_crypto_list()
            logger.info(f"Cryptos to update: {cryptos}")
            for crypto_id in cryptos:
                update_crypto_price(crypto_id)
            time.sleep(UPDATE_INTERVAL_PRICE_UPDATER)
        except Exception as e:
            logger.error(f"Error in price updater: {e}")
            time.sleep(UPDATE_INTERVAL_PRICE_UPDATER)


async def add_crypto_to_general_db(crypto_name, crypto_id):
    """Ajouter une crypto à la base de données générale."""
    conn = sqlite3.connect(f'{PATH_DB_BASE}/list_crypto.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cryptos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            crypto_name TEXT,
            crypto_id TEXT
        )
    ''')
    cursor.execute('''
        INSERT INTO cryptos (crypto_name, crypto_id)
        VALUES (?, ?)
    ''', (crypto_name, crypto_id))
    conn.commit()
    conn.close()

#def start_price_updater_thread():
#    logger.info("Initializing the price updater thread...")
#    thread = threading.Thread(target=price_updater)
#    thread.daemon = True
#    thread.start()
#    logger.info("Price updater thread initialized successfully.")
def update_prices():
    logger.info("Démarrage de la mise à jour des prix...")
    cryptos = get_crypto_list()
    logger.info(f"Cryptos à mettre à jour: {cryptos}")
    for crypto_id in cryptos:
        update_crypto_price(crypto_id)
        

def start_scheduler():
    scheduler = BackgroundScheduler()
    trigger = IntervalTrigger(seconds=UPDATE_INTERVAL)
    scheduler.add_job(update_prices, trigger)
    scheduler.start()
    logger.info("Planificateur de mise à jour des prix démarré.")

if __name__ == "__main__":
    start_scheduler()
    try:
        while True:
            time.sleep(2)
    except (KeyboardInterrupt, SystemExit):
        pass