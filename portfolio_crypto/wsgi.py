from flask import Flask, request, jsonify
from .db import add_transaction, get_transactions, update_transaction, delete_transaction
from .portfolio_crypto import calculate_profit_loss, get_crypto_id, get_historical_price

app = Flask(__name__)

@app.route('/transactions', methods=['GET'])
def list_transactions():
    transactions = get_transactions()
    return jsonify(transactions)

@app.route('/transaction', methods=['POST'])
def create_transaction():
    data = request.json
    add_transaction(data['crypto_name'], data['crypto_id'], data['quantity'], data['price_usd'], data['transaction_type'], data['location'], data['date'], data['historical_price'])
    return jsonify({'success': True}), 201

@app.route('/transaction/<int:id>', methods=['PUT'])
def modify_transaction(id):
    data = request.json
    update_transaction(id, data['crypto_name'], data['crypto_id'], data['quantity'], data['price_usd'], data['transaction_type'], data['location'], data['date'], data['historical_price'])
    return jsonify({'success': True})

@app.route('/transaction/<int:id>', methods=['DELETE'])
def remove_transaction(id):
    delete_transaction(id)
    return jsonify({'success': True})

@app.route('/profit_loss', methods=['GET'])
def profit_loss():
    result = calculate_profit_loss()
    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
