# price_updater.py

import sqlite3
import time
#import threading
import requests
import logging
from datetime import datetime
import asyncio
from .const import COINGECKO_API_URL, UPDATE_INTERVAL, RATE_LIMIT, PORT_APP, PATH_DB_BASE, UPDATE_INTERVAL_PRICE_UPDATER


# Configurer les logs
logging.basicConfig(level=logging.INFO)

# Configurer un logger spécifique pour price_updater
#logger = logging.getLogger('price_updater')
#logger.setLevel(logging.INFO)

# Créer un gestionnaire de fichiers pour enregistrer les logs
#file_handler = logging.FileHandler('/config/portfolio_crypto/price_updater.log')
#file_handler.setLevel(logging.INFO)

# Créer un formatteur et l'ajouter au gestionnaire
#formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
#file_handler.setFormatter(formatter)

# Ajouter le gestionnaire au logger
#logger.addHandler(file_handler)



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

