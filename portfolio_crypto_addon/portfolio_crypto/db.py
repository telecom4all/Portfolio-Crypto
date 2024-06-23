import sqlite3
import os

def get_database_path(entry_id):
    return os.path.join(os.getenv('HASS_CONFIG', '.'), f'portfolio_crypto_{entry_id}.db')

def create_table(entry_id):
    conn = sqlite3.connect(get_database_path(entry_id))
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

def add_transaction(entry_id, crypto_name, crypto_id, quantity, price_usd, transaction_type, location, date, historical_price):
    conn = sqlite3.connect(get_database_path(entry_id))
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO transactions (crypto_name, crypto_id, quantity, price_usd, transaction_type, location, date, historical_price)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (crypto_name, crypto_id, quantity, price_usd, transaction_type, location, date, historical_price))
    conn.commit()
    conn.close()

def get_transactions(entry_id):
    conn = sqlite3.connect(get_database_path(entry_id))
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM transactions')
    transactions = cursor.fetchall()
    conn.close()
    return transactions

def get_all_transactions():
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
    conn = sqlite3.connect(get_database_path(entry_id))
    cursor = conn.cursor()
    cursor.execute('DELETE FROM transactions WHERE id = ?', (transaction_id,))
    conn.commit()
    conn.close()

def update_transaction(entry_id, transaction_id, crypto_name, crypto_id, quantity, price_usd, transaction_type, location, date, historical_price):
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
    conn = sqlite3.connect(get_database_path(entry_id))
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM transactions WHERE crypto_name = ?', (crypto_name,))
    transactions = cursor.fetchall()
    conn.close()
    return transactions

# Appel à create_table pour chaque entry_id lors de l'initialisation
