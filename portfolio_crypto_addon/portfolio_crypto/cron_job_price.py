import logging
import asyncio
import sqlite3
import requests
from datetime import datetime

PATH_DB_BASE = "/config/portfolio_crypto"
UPDATE_INTERVAL_PRICE_UPDATER = 180  # 3 minutes en secondes
COINGECKO_API_URL_PRICE = "https://api.coingecko.com/api/v3/simple/price"

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
        url = f"{COINGECKO_API_URL_PRICE}?ids={crypto_id}&vs_currencies=usd"
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
            crypto_id TEXT PRIMARY KEY,
            price REAL,
            timestamp TEXT
        )
    ''')
    cursor.execute('''
        INSERT OR REPLACE INTO prices (crypto_id, price, timestamp)
        VALUES (?, ?, ?)
    ''', (crypto_id, price, datetime.now().isoformat()))
    conn.commit()
    conn.close()


async def update_crypto_prices():
    logging.info("Starting to update crypto prices...")
    crypto_to_check = get_crypto_list()  # Initial load of crypto list
    
    while True:
        for crypto_id in crypto_to_check:
            logging.info(f"Updating price for {crypto_id}")
            update_crypto_price(crypto_id)
            await asyncio.sleep(UPDATE_INTERVAL_PRICE_UPDATER)  # Sleep for the defined interval
            
            # Check for new cryptos in the database and update the list if necessary
            current_crypto_list = get_crypto_list()
            for crypto in current_crypto_list:
                if crypto not in crypto_to_check:
                    logging.info(f"New crypto found and added to list: {crypto}")
                    crypto_to_check.append(crypto)
        
        logging.info("Finished updating crypto prices. Restarting the process to check for new cryptos.")

async def main():
    while True:
        try:
            logging.info("Starting price updater loop...")
            await update_crypto_prices()
            # Sleep for a short interval before starting the next cycle to avoid tight looping
            await asyncio.sleep(60)  # Sleep for 1 minute before checking for new cryptos and starting the loop again
        except Exception as e:
            logging.error(f"Unhandled error occurred: {e}")
            # Optionally, wait a bit before restarting the loop
            await asyncio.sleep(10)


if __name__ == "__main__":
    asyncio.run(main())
