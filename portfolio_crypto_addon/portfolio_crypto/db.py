import sqlite3
import os
import logging

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
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
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
        conn.close()
        logging.info(f"Table 'transactions' créée avec succès pour l'entrée {entry_id}")
    except Exception as e:
        logging.error(f"Erreur lors de la création de la table pour l'entrée {entry_id}: {e}")

def create_crypto_table(entry_id):
    db_path = get_database_path(entry_id)
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cryptos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_id TEXT,
                crypto_name TEXT,
                crypto_id TEXT
            )
        ''')
        conn.commit()
        conn.close()
        logging.info(f"Table 'cryptos' créée avec succès pour l'entrée {entry_id}")
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

def get_crypto_transactions(entry_id, crypto_name):
    """Récupérer les transactions d'une crypto-monnaie spécifique pour un ID d'entrée donné"""
    conn = sqlite3.connect(get_database_path(entry_id))
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM transactions WHERE crypto_name = ?', (crypto_name,))
    transactions = cursor.fetchall()
    conn.close()
    return transactions

def load_crypto_attributes(entry_id):
    """Charger les attributs des cryptos depuis la base de données pour un ID d'entrée donné"""
    create_crypto_table(entry_id)
    conn = sqlite3.connect(get_database_path(entry_id))
    cursor = conn.cursor()
    cursor.execute('SELECT crypto_name, crypto_id FROM cryptos WHERE entry_id = ?', (entry_id,))
    cryptos = cursor.fetchall()
    conn.close()
    return {crypto_id: {'crypto_name': crypto_name, 'crypto_id': crypto_id} for crypto_name, crypto_id in cryptos}