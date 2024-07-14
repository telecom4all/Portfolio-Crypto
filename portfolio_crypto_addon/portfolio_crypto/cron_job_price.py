import logging
import asyncio
import aiocron
import sqlite3
#import threading
import requests
from datetime import datetime

PATH_DB_BASE = "/config/portfolio_crypto"
UPDATE_INTERVAL_PRICE_UPDATER = 120
COINGECKO_API_URL = "https://api.coingecko.com/api/v3/coins/list"
COINGECKO_API_URL_PRICE = "https://api.coingecko.com/api/v3"

# Configurer les logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s:%(name)s:%(message)s')


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
        logging.info(f"URL PRICE UPDATER {url}")
        response = requests.get(url)
        if response.status_code == 200:
            price = response.json().get(crypto_id, {}).get('usd', 0)
            if price:
                logging.info(f"Prix récupéré pour {crypto_id}: {price}")
                save_crypto_price(crypto_id, price)
            else:
                logging.error(f"Prix non trouvé dans la réponse pour {crypto_id}: {response.json()}")
        else:
            logging.error(f"Échec de la récupération du prix pour {crypto_id}: {response.status_code}")
    except Exception as e:
        logging.error(f"Erreur lors de la mise à jour du prix pour {crypto_id}: {e}")


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



async def update_crypto_prices():
    logging.info("Starting to update crypto prices...")
    cryptos = await get_crypto_list()
    for crypto_id in cryptos:
        logging.info(f"Updating price for {crypto_id}")
        await update_crypto_price(crypto_id)
        await asyncio.sleep(60)  # Sleep for 1 minute
    logging.info("Finished updating crypto prices")

    
@aiocron.crontab('*/5 * * * *')
async def scheduled_task():
    logging.info("Tâche cron démarrée")
    try:
        await update_crypto_prices()
        logging.info("Tâche cron terminée avec succès")
    except Exception as e:
        logging.error(f"Erreur lors de l'exécution de la tâche cron : {e}")

async def main():
    logging.info("Starting scheduled tasks...")
    # Start the cron job manually to avoid waiting for the first interval
    await scheduled_task()
    # Keep the script running to allow the cron job to run
    while True:
        await asyncio.sleep(UPDATE_INTERVAL_PRICE_UPDATER)  # Sleep for 1 minute

if __name__ == "__main__":
    asyncio.run(main())