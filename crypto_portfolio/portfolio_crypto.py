import json
import requests
import requests_cache
from datetime import datetime, timedelta
import logging
import time
from flask import Flask, jsonify, request
from .db import add_transaction, get_transactions, delete_transaction, update_transaction, get_crypto_transactions
import os

# Configure logging
logging.basicConfig(level=logging.INFO)

# Configure caching
expire_after = timedelta(minutes=10)
requests_cache.install_cache('coingecko_cache', expire_after=expire_after)

# Flask app setup
app = Flask(__name__)

def get_data_with_retry(url, retries=5, backoff_factor=1.0):
    for i in range(retries):
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if response.status_code == 429:  # Too Many Requests
                wait_time = backoff_factor * (2 ** i)
                logging.warning(f"Rate limit exceeded. Waiting for {wait_time} seconds.")
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

def add_test_transactions():
    test_transactions = [
        ('Polygon', 'matic-network', 244.862, 130.346, 'buy', 'Bitget', '2023-09-18', 0.5323243296223996),
        ('Polygon', 'matic-network', 227.913, 127.461, 'buy', 'Bitget', '2023-10-01', 0.5592528728067289),
        ('Ethereum', 'ethereum', 0.0188939, 30.77, 'buy', 'Kucoin', '2023-10-21', 1628.567950502543),
        ('Ethereum', 'ethereum', 0.01, 18.17, 'sell', 'Kucoin', '2023-10-25', 1817),
        ('Ethereum', 'ethereum', 0.0199527, 41.47, 'buy', 'Bitget', '2023-11-25', 2078.41545254527)
    ]
    for tx in test_transactions:
        logging.info(f"Attempting to add test transaction: {tx}")
        add_transaction(*tx)
        logging.info(f"Added test transaction: {tx}")

def calculate_profit_loss():
    transactions = get_transactions()
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

@app.route('/transactions', methods=['GET'])
def transactions():
    transactions = get_transactions()
    logging.info(f"Fetched transactions: {transactions}")
    return jsonify(transactions)

@app.route('/profit_loss', methods=['GET'])
def profit_loss():
    result = calculate_profit_loss()
    logging.info(f"Calculated profit/loss: {result}")
    return jsonify(result)

@app.route('/transaction', methods=['POST'])
def add_transaction_endpoint():
    try:
        data = request.json
        logging.info(f"Received data for new transaction: {data}")
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

        add_transaction(crypto_name, crypto_id, quantity, price_usd, transaction_type, location, date, historical_price)

        # Detect and add new sensors if necessary
        update_transactions()  # Ensure new sensors are created for new cryptos

        logging.info(f"Added transaction: {crypto_name}, {crypto_id}, {quantity}, {price_usd}, {transaction_type}, {location}, {date}, {historical_price}")
        return jsonify({"message": "Transaction added"}), 201
    except Exception as e:
        logging.error(f"Error adding transaction: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

@app.route('/transaction/<int:transaction_id>', methods=['DELETE'])
def delete_transaction_endpoint(transaction_id):
    try:
        logging.info(f"Attempting to delete transaction with ID: {transaction_id}")
        delete_transaction(transaction_id)
        logging.info(f"Deleted transaction with ID: {transaction_id}")
        return jsonify({"message": "Transaction deleted"}), 200
    except Exception as e:
        logging.error(f"Error deleting transaction: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

@app.route('/transaction/<int:transaction_id>', methods=['PUT'])
def update_transaction_endpoint(transaction_id):
    try:
        data = request.json
        logging.info(f"Received data for updating transaction: {data}")
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

        update_transaction(transaction_id, crypto_name, crypto_id, quantity, price_usd, transaction_type, location, date, historical_price)
        logging.info(f"Updated transaction with ID: {transaction_id}")
        return jsonify({"message": "Transaction updated"}), 200
    except Exception as e:
        logging.error(f"Error updating transaction: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

def update_transactions():
    transactions = get_transactions()
    known_cryptos = get_known_cryptos()  # Function to get currently known cryptos

    new_cryptos = set()
    for transaction in transactions:
        crypto_id = transaction[2]
        if crypto_id not in known_cryptos:
            new_cryptos.add(crypto_id)
            known_cryptos.add(crypto_id)

    if new_cryptos:
        for crypto_id in new_cryptos:
            add_new_crypto_sensor(crypto_id)  # Function to add new sensor

    # Recalculate profit/loss
    result = calculate_profit_loss()

    # Update Home Assistant sensors with the recalculated data
    update_sensors(result)

def update_sensors(profit_loss_data):
    for detail in profit_loss_data['details']:
        crypto_id = detail['crypto_id']
        update_sensor_state(f"sensor.crypto_{crypto_id}_investment", detail['investment'])
        update_sensor_state(f"sensor.crypto_{crypto_id}_current_value", detail['current_value'])
        update_sensor_state(f"sensor.crypto_{crypto_id}_profit_loss", detail['profit_loss'])
        update_sensor_state(f"sensor.crypto_{crypto_id}_profit_loss_percent", detail['profit_loss_percent'])

    update_sensor_state("sensor.total_investment", profit_loss_data['summary']['total_investment'])
    update_sensor_state("sensor.total_value", profit_loss_data['summary']['total_value'])
    update_sensor_state("sensor.total_profit_loss", profit_loss_data['summary']['total_profit_loss'])
    update_sensor_state("sensor.total_profit_loss_percent", profit_loss_data['summary']['total_profit_loss_percent'])

def update_sensor_state(sensor_id, state):
    url = f"http://supervisor/core/api/states/{sensor_id}"
    data = {
        "state": state,
        "attributes": {
            "unit_of_measurement": "USD" if "percent" not in sensor_id else "%",
            "friendly_name": sensor_id.replace("sensor.", "").replace("_", " ").title()
        }
    }
    headers = {
        "Authorization": f"Bearer {os.environ['SUPERVISOR_TOKEN']}",
        "content-type": "application/json",
    }
    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 200:
        logging.info(f"Updated sensor {sensor_id} with state {state}")
    else:
        logging.error(f"Failed to update sensor {sensor_id}. Status code: {response.status_code}, Response: {response.text}")

def get_known_cryptos():
    transactions = get_transactions()
    return {transaction[2] for transaction in transactions}

def add_new_crypto_sensor(crypto_id):
    url = f"http://supervisor/core/api/states/sensor.crypto_{crypto_id}"
    data = {
        "state": "unknown",
        "attributes": {
            "unit_of_measurement": "USD",
            "friendly_name": f"Crypto {crypto_id}"
        }
    }
    headers = {
        "Authorization": f"Bearer {os.environ['SUPERVISOR_TOKEN']}",
        "content-type": "application/json",
    }
    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 201:
        logging.info(f"Added new sensor for {crypto_id}")
    else:
        logging.error(f"Failed to add new sensor for {crypto_id}. Status code: {response.status_code}, Response: {response.text}")

def run_flask_app():
    app.run(host='0.0.0.0', port=5000)

if __name__ == '__main__':
    run_flask_app()
