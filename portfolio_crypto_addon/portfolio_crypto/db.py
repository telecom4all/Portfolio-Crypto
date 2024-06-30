import sqlite3
import os
import logging
import requests

# Configurer les logs
logging.basicConfig(level=logging.INFO)

def get_database_path(entry_id):
    """Récupérer le chemin de la base de données pour un ID d'entrée donné"""
    db_path = os.path.join(os.getenv('HASS_CONFIG', '.'), f'portfolio_crypto_{entry_id}.db')
    logging.info(f"Chemin de la base de données pour l'entrée {entry_id}: {db_path}")
    return db_path

def create_table(entry_id):
    db_path = get_database_path(entry_id)
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Vérifier si la table 'transactions' existe déjà
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='transactions'")
        if cursor.fetchone() is None:
            # Si la table n'existe pas, la créer
            cursor.execute('''
                CREATE TABLE transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    crypto_name TEXT,
                    crypto_id TEXT,
                    quantity REAL,
                    price_usd REAL,
                    transaction_type TEXT,
                    location TEXT,
                    date TEXT,
                    historical_price REAL
                )
            ''')
            conn.commit()
            logging.info(f"Table 'transactions' créée avec succès pour l'entrée {entry_id}")
        else:
            logging.info(f"Table 'transactions' existe déjà pour l'entrée {entry_id}")

        conn.close()
    except Exception as e:
        logging.error(f"Erreur lors de la création de la table pour l'entrée {entry_id}: {e}")

def create_crypto_table(entry_id):
    db_path = get_database_path(entry_id)
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Vérifier si la table 'cryptos' existe déjà
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cryptos'")
        if cursor.fetchone() is None:
            # Si la table n'existe pas, la créer
            cursor.execute('''
                CREATE TABLE cryptos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_id TEXT,
                    crypto_name TEXT,
                    crypto_id TEXT
                )
            ''')
            conn.commit()
            logging.info(f"Table 'cryptos' créée avec succès pour l'entrée {entry_id}")
        else:
            logging.info(f"Table 'cryptos' existe déjà pour l'entrée {entry_id}")

        conn.close()
    except Exception as e:
        logging.error(f"Erreur lors de la création de la table 'cryptos' pour l'entrée {entry_id}: {e}")

def save_crypto(entry_id, crypto_name, crypto_id):
    create_crypto_table(entry_id)
    conn = sqlite3.connect(get_database_path(entry_id))
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO cryptos (entry_id, crypto_name, crypto_id)
            VALUES (?, ?, ?)
        ''', (entry_id, crypto_name, crypto_id))
        conn.commit()
        logging.info(f"Crypto {crypto_name} avec ID {crypto_id} sauvegardée pour l'entrée {entry_id}")
    except Exception as e:
        logging.error(f"Erreur lors de la sauvegarde de la crypto pour l'entrée {entry_id}: {e}")
    finally:
        conn.close()

def get_cryptos(entry_id):
    create_crypto_table(entry_id)
    conn = sqlite3.connect(get_database_path(entry_id))
    cursor = conn.cursor()
    cursor.execute('SELECT crypto_name, crypto_id FROM cryptos WHERE entry_id = ?', (entry_id,))
    cryptos = cursor.fetchall()
    conn.close()
    return cryptos

def add_transaction(entry_id, crypto_name, crypto_id, quantity, price_usd, transaction_type, location, date, historical_price):
    """Ajouter une transaction à la base de données"""
    create_table(entry_id)  # Assurer que la table est créée avant d'ajouter des données
    conn = sqlite3.connect(get_database_path(entry_id))
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO transactions (crypto_name, crypto_id, quantity, price_usd, transaction_type, location, date, historical_price)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (crypto_name, crypto_id, quantity, price_usd, transaction_type, location, date, historical_price))
    conn.commit()
    conn.close()

def get_transactions(entry_id):
    """Récupérer toutes les transactions pour un ID d'entrée donné"""
    conn = sqlite3.connect(get_database_path(entry_id))
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM transactions')
    transactions = cursor.fetchall()
    conn.close()
    return transactions

def get_all_transactions():
    """Récupérer toutes les transactions de toutes les bases de données"""
    databases = [f for f in os.listdir(os.getenv('HASS_CONFIG', '.')) if f.startswith('portfolio_crypto_') and f.endswith('.db')]
    all_transactions = []
    for db in databases:
        conn = sqlite3.connect(os.path.join(os.getenv('HASS_CONFIG', '.'), db))
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM transactions')
        transactions = cursor.fetchall()
        all_transactions.extend(transactions)
        conn.close()
    return all_transactions

def delete_transaction(entry_id, transaction_id):
    """Supprimer une transaction de la base de données"""
    conn = sqlite3.connect(get_database_path(entry_id))
    cursor = conn.cursor()
    cursor.execute('DELETE FROM transactions WHERE id = ?', (transaction_id,))
    conn.commit()
    conn.close()

def update_transaction(entry_id, transaction_id, crypto_name, crypto_id, quantity, price_usd, transaction_type, location, date, historical_price):
    """Mettre à jour une transaction dans la base de données"""
    conn = sqlite3.connect(get_database_path(entry_id))
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE transactions
        SET crypto_name = ?, crypto_id = ?, quantity = ?, price_usd = ?, transaction_type = ?, location = ?, date = ?, historical_price = ?
        WHERE id = ?
    ''', (crypto_name, crypto_id, quantity, price_usd, transaction_type, location, date, historical_price, transaction_id))
    conn.commit()
    conn.close()

#def get_crypto_transactions(entry_id, crypto_name):
#    """Récupérer les transactions d'une crypto-monnaie spécifique pour un ID d'entrée donné"""
#    conn = sqlite3.connect(get_database_path(entry_id))
#    cursor = conn.cursor()
#    cursor.execute('SELECT * FROM transactions WHERE crypto_name = ?', (crypto_name,))
#    transactions = cursor.fetchall()
#    conn.close()
#    return transactions

def get_crypto_transactions(entry_id, crypto_id):
    """Récupérer les transactions pour une crypto-monnaie spécifique et un ID d'entrée donné"""
    conn = sqlite3.connect(get_database_path(entry_id))
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM transactions WHERE crypto_id = ?', (crypto_id,))
    transactions = cursor.fetchall()
    conn.close()
    return transactions

def get_crypto_price(crypto_id):
    """Récupérer le prix actuel d'une crypto-monnaie"""
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={crypto_id}&vs_currencies=usd"
    response = requests.get(url)
    data = response.json()
    if crypto_id in data:
        return data[crypto_id]['usd']
    else:
        logging.error(f"Données de prix pour {crypto_id} introuvables.")
        return 0

def get_crypto_id(name):
    """Récupérer l'ID d'une crypto-monnaie en fonction de son nom"""
    url = f"https://api.coingecko.com/api/v3/search?query={name}"
    data = requests.get(url).json()
    for coin in data['coins']:
        if coin['name'].lower() == name.lower():
            return coin['id']
    return None

def calculate_crypto_profit_loss(entry_id, crypto_name):
    """Calculer le profit/perte pour une crypto-monnaie spécifique et un ID d'entrée donné"""
    transactions = get_crypto_transactions(entry_id, crypto_name)
    crypto_id = get_crypto_id(crypto_name)
    current_price = get_crypto_price(crypto_id)
    investment = 0
    quantity_held = 0
    for transaction in transactions:
        if transaction[5] == 'buy':
            investment += transaction[4]
            quantity_held += transaction[3]
        elif transaction[5] == 'sell':
            investment -= transaction[4]
            quantity_held -= transaction[3]

    current_value = quantity_held * current_price
    profit_loss = current_value - investment
    profit_loss_percent = (profit_loss / investment) * 100 if investment != 0 else 0

    return {
        "investment": investment,
        "current_value": current_value,
        "profit_loss": profit_loss,
        "profit_loss_percent": profit_loss_percent
    }

def load_crypto_attributes(entry_id):
    """Charger les attributs des cryptos depuis la base de données pour un ID d'entrée donné"""
    create_crypto_table(entry_id)
    conn = sqlite3.connect(get_database_path(entry_id))
    cursor = conn.cursor()
    cursor.execute('SELECT crypto_name, crypto_id FROM cryptos WHERE entry_id = ?', (entry_id,))
    cryptos = cursor.fetchall()
    conn.close()
    return {crypto_id: {'crypto_name': crypto_name, 'crypto_id': crypto_id} for crypto_name, crypto_id in cryptos}



def delete_crypto(entry_id, crypto_id):
    """Supprimer une crypto-monnaie de la base de données pour un ID d'entrée donné"""
    try:
        conn = sqlite3.connect(get_database_path(entry_id))
        cursor = conn.cursor()
        cursor.execute('DELETE FROM cryptos WHERE crypto_id = ?', (crypto_id,))
        conn.commit()
        conn.close()
        logging.info(f"Crypto avec ID: {crypto_id} supprimée dans l'entrée {entry_id}")
        return True
    except Exception as e:
        logging.error(f"Erreur lors de la suppression de la crypto: {e}")
        return False

