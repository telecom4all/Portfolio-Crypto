import json
import requests
import requests_cache
from datetime import datetime, timedelta
import logging
import time
from flask import Flask, jsonify, request
from .db import add_transaction, get_transactions, delete_transaction, update_transaction, get_crypto_transactions, create_table
import os

# Configure logging
logging.basicConfig(level=logging.INFO)

# Configure caching
expire_after = timedelta(minutes=10)
requests_cache.install_cache('coingecko_cache', expire_after=expire_after)

# Flask app setup
app = Flask(__name__)

@app.route('/initialize', methods=['POST'])
def initialize():
    entry_id = request.json.get('entry_id')
    if not entry_id:
        return jsonify({"error": "entry_id is required"}), 400
    try:
        create_table(entry_id)
        logging.info(f"Initialized new portfolio with entry ID: {entry_id}")
        return jsonify({"message": "Database initialized"}), 200
    except Exception as e:
        logging.error(f"Error initializing database for entry ID {entry_id}: {e}")
        return jsonify({"error": str(e)}), 500

def get_data_with_retry(url, retries=5, backoff_factor=1.0):
    for i in range(retries):
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if response.status_code == 429:  # Too Many Requests
                wait time = backoff_factor * (2 ** i)
                logging.warning(f"Rate limit exceeded. Waiting for {wait time} seconds.")
                time.sleep(wait_time)
            else:
                raise e
    raise requests.exceptions.RequestException(f"Failed to get data from {url} after {retries} retries")

def get_crypto_id(name):
    url = f"https://api.coingecko.com/api/v3/search?query={name}"
    data = get_data_with_retry(url)
    for coin in data['coins']:
        if coin['name'].lower() == name.lower():
            return coin['id']
    return None

def get_crypto_price(crypto_id):
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={crypto_id}&vs_currencies=usd"
    data = get_data_with_retry(url)
    if crypto_id in data:
        return data[crypto_id]['usd']
    else:
        logging.error(f"Price data for {crypto_id} not found.")
        return 0

def get_historical_price(crypto_id, date):
    url = f"https://api.coingecko.com/api/v3/coins/{crypto_id}/history?date={date}"
    data = get_data_with_retry(url)
    try:
        return data['market_data']['current_price']['usd']
    except KeyError:
        return None

def calculate_profit_loss(entry_id):
    transactions = get_transactions(entry_id)
    crypto_groups = {}
    for transaction in transactions:
        crypto_id = transaction[2]
        if crypto_id not in crypto_groups:
            crypto_groups[crypto_id] = []
        crypto_groups[crypto_id].append(transaction)

    total_investment = 0
    total_value = 0

    results = []
    for crypto_id, transactions in crypto_groups.items():
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
        total_investment += investment
        total_value += current_value
        profit_loss = current_value - investment
        profit_loss_percent = (profit_loss / investment) * 100 if investment != 0 else 0
        results.append({
            "crypto_id": crypto_id,
            "investment": investment,
            "current_value": current_value,
            "profit_loss": profit_loss,
            "profit_loss_percent": profit_loss_percent
        })

    total_profit_loss = total_value - total_investment
    total_profit_loss_percent = (total_profit_loss / total_investment) * 100 if total_investment != 0 else 0
    summary = {
        "total_investment": total_investment,
        "total_value": total_value,
        "total_profit_loss": total_profit_loss,
        "total_profit_loss_percent": total_profit_loss_percent
    }

    return {"details": results, "summary": summary}

def calculate_crypto_profit_loss(entry_id, crypto_name):
    transactions = get_crypto_transactions(entry_id, crypto_name)
    current_price = get_crypto_price(crypto_name)
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

@app.route('/transactions/<entry_id>', methods=['GET'])
def list_transactions(entry_id):
    transactions = get_transactions(entry_id)
    logging.info(f"Fetched transactions for entry {entry_id}: {transactions}")
    return jsonify(transactions)

@app.route('/all_transactions', methods=['GET'])
def all_transactions():
    # Here, we assume that get_transactions() can be called without an entry_id to fetch all transactions
    # If get_transactions() requires an entry_id, you will need to modify this function accordingly
    entry_ids = []  # Replace this with a way to get all entry_ids if necessary
    all_transactions = []
    for entry_id in entry_ids:
        transactions = get_transactions(entry_id)
        all_transactions extend(transactions)
    logging.info(f"Fetched all transactions: {all_transactions}")
    return jsonify(all_transactions)

@app.route('/profit_loss/<entry_id>', methods=['GET'])
def profit_loss(entry_id):
    result = calculate_profit_loss(entry_id)
    logging.info(f"Calculated profit/loss for entry {entry_id}: {result}")
    return jsonify(result)

@app.route('/crypto_profit_loss/<entry_id>/<crypto_name>', methods=['GET'])
def crypto_profit_loss(entry_id, crypto_name):
    result = calculate_crypto_profit_loss(entry_id, crypto_name)
    logging.info(f"Calculated profit/loss for {crypto_name} in entry {entry_id}: {result}")
    return jsonify(result)

@app.route('/transaction/<entry_id>', methods=['POST'])
def create_transaction(entry_id):
    try:
        data = request.json
        logging.info(f"Received data for new transaction in entry {entry_id}: {data}")
        crypto_name = data['crypto_name']
        crypto_id = get_crypto_id(crypto_name)
        if not crypto_id:
            logging.error("Cryptocurrency not found")
            return jsonify({"error": "Cryptocurrency not found"}), 404
        quantity = data['quantity']
        price_usd = data['price_usd']
        transaction_type = data['transaction_type']
        location = data['location']
        date = data['date']
        historical_price = get_historical_price(crypto_id, datetime.strptime(date, "%Y-%m-%d").strftime("%d-%m-%Y"))
        if not historical_price:
            historical_price = price_usd / quantity

        add_transaction(entry_id, crypto_name, crypto_id, quantity, price_usd, transaction_type, location, date, historical_price)

        logging.info(f"Added transaction: {crypto_name}, {crypto_id}, {quantity}, {price_usd}, {transaction_type}, {location}, {date}, {historical_price}")
        return jsonify({"message": "Transaction added"}), 201
    except Exception as e:
        logging.error(f"Error adding transaction: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

@app.route('/transaction/<entry_id>/<int:transaction_id>', methods=['DELETE'])
def delete_transaction_endpoint(entry_id, transaction_id):
    try:
        logging.info(f"Attempting to delete transaction with ID: {transaction_id} in entry {entry_id}")
        delete_transaction(entry_id, transaction_id)
        logging.info(f"Deleted transaction with ID: {transaction_id} in entry {entry_id}")
        return jsonify({"message": "Transaction deleted"}), 200
    except Exception as e:
        logging.error(f"Error deleting transaction: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

@app.route('/transaction/<entry_id>/<int:transaction_id>', methods=['PUT'])
def update_transaction_endpoint(entry_id, transaction_id):
    try:
        data = request.json
        logging.info(f"Received data for updating transaction in entry {entry_id}: {data}")
        crypto_name = data['crypto_name']
        crypto_id = get_crypto_id(crypto_name)
        if not crypto_id:
            logging.error("Cryptocurrency not found")
            return jsonify({"error": "Cryptocurrency not found"}), 404
        quantity = data['quantity']
        price_usd = data['price_usd']
        transaction_type = data['transaction_type']
        location = data['location']
        date = data['date']
        historical_price = get_historical_price(crypto_id, datetime.strptime(date, "%Y-%m-%d").strftime("%d-%m-%Y"))
        if not historical_price:
            historical_price = price_usd / quantity

        update_transaction(entry_id, transaction_id, crypto_name, crypto_id, quantity, price_usd, transaction_type, location, date, historical_price)
        logging.info(f"Updated transaction with ID: {transaction_id} in entry {entry_id}")
        return jsonify({"message": "Transaction updated"}), 200
    except Exception as e:
        logging.error(f"Error updating transaction: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

def run_flask_app():
    app.run(host='0.0.0.0', port=5000)

if __name__ == '__main__':
    run_flask_app()
