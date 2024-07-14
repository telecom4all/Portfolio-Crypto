# portfolio_crypto_addon/portfolio_crypto/price_updater.py
import sqlite3
import time
import threading
import requests
import logging
from datetime import datetime
from .const import COINGECKO_API_URL, UPDATE_INTERVAL, RATE_LIMIT, PORT_APP, PATH_DB_BASE

#logging.basicConfig(level=logging.INFO)

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


COINGECKO_API_URL = "https://api.coingecko.com/api/v3/simple/price"

def get_crypto_list():
    
    conn = sqlite3.connect(f'{PATH_DB_BASE}/list_crypto.db')
    cursor = conn.cursor()
    cursor.execute('SELECT crypto_id FROM cryptos')
    cryptos = cursor.fetchall()
    conn.close()
    return [crypto[0] for crypto in cryptos]

def update_crypto_price(crypto_id):
    url = f"{COINGECKO_API_URL}?ids={crypto_id}&vs_currencies=usd"
    response = requests.get(url)
    if response.status_code == 200:
        price = response.json().get(crypto_id, {}).get('usd', 0)
        save_crypto_price(crypto_id, price)
    else:
        logging.error(f"Failed to fetch price for {crypto_id}: {response.status_code}")

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
    logging.info("Price updater thread has started running.")
    while True:
        cryptos = get_crypto_list()
        for crypto_id in cryptos:
            logging.info(f"*************Update Price**************")
            update_crypto_price(crypto_id)
            time.sleep(300)  # 5 minutes


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


def start_price_updater_thread():
    logging.info("Initializing the price updater thread...")
    thread = threading.Thread(target=price_updater)
    thread.daemon = True
    thread.start()
    logging.info("Price updater thread initialized successfully.")
