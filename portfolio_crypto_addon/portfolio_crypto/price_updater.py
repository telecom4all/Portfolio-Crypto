# portfolio_crypto_addon/portfolio_crypto/price_updater.py
import sqlite3
import time
import threading
import requests
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)

COINGECKO_API_URL = "https://api.coingecko.com/api/v3/simple/price"

def get_crypto_list():
    conn = sqlite3.connect('/config/list_crypto.db')
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
    conn = sqlite3.connect('/config/cache_prix_crypto.db')
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
    while True:
        cryptos = get_crypto_list()
        for crypto_id in cryptos:
            update_crypto_price(crypto_id)
            time.sleep(300)  # 5 minutes

def start_price_updater_thread():
    thread = threading.Thread(target=price_updater)
    thread.daemon = True
    thread.start()
