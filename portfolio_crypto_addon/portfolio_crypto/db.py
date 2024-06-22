import sqlite3
import os

DATABASE = os.path.join(os.getenv('HASS_CONFIG', '.'), 'portfolio_crypto.db')

def create_table():
    conn = sqlite3.connect(DATABASE)
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

def add_transaction(crypto_name, crypto_id, quantity, price_usd, transaction_type, location, date, historical_price):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO transactions (crypto_name, crypto_id, quantity, price_usd, transaction_type, location, date, historical_price)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (crypto_name, crypto_id, quantity, price_usd, transaction_type, location, date, historical_price))
    conn.commit()
    conn.close()

def get_transactions():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM transactions')
    transactions = cursor.fetchall()
    conn.close()
    return transactions

def delete_transaction(transaction_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM transactions WHERE id = ?', (transaction_id,))
    conn.commit()
    conn.close()

def update_transaction(transaction_id, crypto_name, crypto_id, quantity, price_usd, transaction_type, location, date, historical_price):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE transactions
        SET crypto_name = ?, crypto_id = ?, quantity = ?, price_usd = ?, transaction_type = ?, location = ?, date = ?, historical_price = ?
        WHERE id = ?
    ''', (crypto_name, crypto_id, quantity, price_usd, transaction_type, location, date, historical_price, transaction_id))
    conn.commit()
    conn.close()

def get_crypto_transactions(crypto_name):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM transactions WHERE crypto_name = ?', (crypto_name,))
    transactions = cursor.fetchall()
    conn.close()
    return transactions

create_table()
