import os
import json
import logging
from datetime import datetime
from flask import Flask, jsonify, request
import threading
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from .db import create_table, add_transaction, get_transactions, delete_transaction, update_transaction, get_crypto_transactions
from .portfolio_crypto import get_crypto_id, get_crypto_price, get_historical_price, calculate_profit_loss
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/transactions', methods=['GET'])
def transactions():
    transactions = get_transactions()
    _LOGGER.info(f"Fetched transactions: {transactions}")
    return jsonify(transactions)

@app.route('/profit_loss', methods=['GET'])
def profit_loss():
    result = calculate_profit_loss()
    _LOGGER.info(f"Calculated profit/loss: {result}")
    return jsonify(result)

@app.route('/transaction', methods=['POST'])
def add_transaction_endpoint():
    try:
        data = request.json
        _LOGGER.info(f"Received data for new transaction: {data}")
        crypto_name = data['crypto_name']
        crypto_id = get_crypto_id(crypto_name)
        if not crypto_id:
            _LOGGER.error("Cryptocurrency not found")
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
        _LOGGER.info(f"Added transaction: {crypto_name}, {crypto_id}, {quantity}, {price_usd}, {transaction_type}, {location}, {date}, {historical_price}")
        return jsonify({"message": "Transaction added"}), 201
    except Exception as e:
        _LOGGER.error(f"Error adding transaction: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

@app.route('/transaction/<int:transaction_id>', methods=['DELETE'])
def delete_transaction_endpoint(transaction_id):
    try:
        _LOGGER.info(f"Attempting to delete transaction with ID: {transaction_id}")
        delete_transaction(transaction_id)
        _LOGGER.info(f"Deleted transaction with ID: {transaction_id}")
        return jsonify({"message": "Transaction deleted"}), 200
    except Exception as e:
        _LOGGER.error(f"Error deleting transaction: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

@app.route('/transaction/<int:transaction_id>', methods=['PUT'])
def update_transaction_endpoint(transaction_id):
    try:
        data = request.json
        _LOGGER.info(f"Received data for updating transaction: {data}")
        crypto_name = data['crypto_name']
        crypto_id = get_crypto_id(crypto_name)
        if not crypto_id:
            _LOGGER.error("Cryptocurrency not found")
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
        _LOGGER.info(f"Updated transaction with ID: {transaction_id}")
        return jsonify({"message": "Transaction updated"}), 200
    except Exception as e:
        _LOGGER.error(f"Error updating transaction: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

def run_flask_app():
    _LOGGER.info("Starting Flask app with gunicorn")
    os.system("/config/custom_components/portfolio_crypto/run.sh")

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    create_table()
    thread = threading.Thread(target=run_flask_app)
    thread.start()
    _LOGGER.info("Started Flask app thread")
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})

    hass.data[DOMAIN][entry.entry_id] = {}

    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "sensor")
    )
    return True
