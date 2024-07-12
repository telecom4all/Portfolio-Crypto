"""
Fichier portfolio_crypto.py
Ce fichier gère l'application Flask et les routes API pour l'addon Portfolio Crypto.
"""

import json
import requests
import requests_cache
from datetime import datetime, timedelta
import logging
import time
from flask import Flask, jsonify, request, render_template, send_file
from flask_cors import CORS
from .db import add_transaction, get_transactions, delete_transaction, update_transaction, get_crypto_transactions, create_table, create_crypto_table, save_crypto, get_cryptos, calculate_crypto_profit_loss, load_crypto_attributes, delete_crypto_db, export_db, import_db, import_transactions, verify_cryptos, get_database_path
import os
import sqlite3
import threading
from .const import COINGECKO_API_URL, UPDATE_INTERVAL, RATE_LIMIT, PORT_APP

# Configurer les logs
# Configurer les logs avec un format d'horodatage
#logging.basicConfig(
#    level=logging.INFO,
#    format='%(asctime)s %(levelname)s:%(name)s:%(message)s',
#    datefmt='%Y-%m-%d %H:%M:%S'
#)


# Configurer le cache
expire_after = timedelta(minutes=RATE_LIMIT)
requests_cache.install_cache('coingecko_cache', expire_after=expire_after)

# Configuration de l'application Flask
#app = Flask(__name__)
app = Flask(__name__, template_folder='/config/custom_components/portfolio_crypto/templates')

CORS(app, resources={r"/*": {"origins": "*"}})  # Permettre toutes les origines pour toutes les routes

@app.route('/')
def index():
    try:
        return render_template('index.html')
    except Exception as e:
        app.logger.error(f"Error rendering template: {e}")
        return str(e), 500


@app.route('/api/wallets', methods=['GET'])
def get_wallets():
    home_assistant_url = os.getenv('HASSIO', 'http://supervisor/core')  # Utilise l'URL par défaut si HASSIO n'est pas défini
    access_token = os.getenv('HASSIO_TOKEN', '')  # Utilise le token du superviseur

    if not access_token:
        return jsonify({'error': 'Supervisor token is missing'}), 500

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    response = requests.get(f'{home_assistant_url}/api/states', headers=headers)

    if response.status_code != 200:
        return jsonify({'error': 'Unable to fetch data from Home Assistant'}), 500

    sensors = response.json()
    wallets = []

    for sensor in sensors:
        if sensor['entity_id'].startswith('sensor.'):
            attributes = sensor.get('attributes', {})
            friendly_name = attributes.get('friendly_name', '')
            if 'total_investment' in friendly_name:
                wallet_name = friendly_name.replace(' total_investment', '')
                wallets.append({
                    'entry_id': attributes.get('entry_id', ''),
                    'name': wallet_name
                })

    return jsonify(wallets)


@app.route('/initialize', methods=['POST'])
def initialize():
    """Initialiser la base de données pour un nouveau portfolio"""
    entry_id = request.json.get('entry_id')
    if not entry_id:
        return jsonify({"error": "entry_id is required"}), 400
    try:
        create_table(entry_id)
        create_crypto_table(entry_id)
        logging.info(f"Portfolio initialisé avec succès pour l'ID d'entrée: {entry_id}")
        return jsonify({"message": "Database initialized"}), 200
    except Exception as e:
        logging.error(f"Erreur lors de l'initialisation de la base de données pour l'ID d'entrée {entry_id}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/save_crypto', methods=['POST'])
def save_crypto_route():
    try:
        data = request.json
        entry_id = data['entry_id']
        crypto_name = data['crypto_name']
        crypto_id = data['crypto_id']
        save_crypto(entry_id, crypto_name, crypto_id)
        return jsonify({"message": "Crypto sauvegardée"}), 200
    except Exception as e:
        logging.error(f"Erreur lors de la sauvegarde de la crypto: {e}")
        return jsonify({"error": "Erreur Interne"}), 500

@app.route('/load_cryptos/<entry_id>', methods=['GET'])
def load_cryptos(entry_id):
    """Charger toutes les cryptos pour un ID d'entrée donné depuis la base de données"""
    try:
        cryptos = get_cryptos(entry_id)
        return jsonify(cryptos), 200
    except Exception as e:
        logging.error(f"Erreur lors du chargement des cryptos pour l'ID d'entrée {entry_id}: {e}")
        return jsonify({"error": "Erreur Interne"}), 500

@app.route('/crypto_profit_loss/<entry_id>/<crypto_id>', methods=['GET'])
def crypto_profit_loss(entry_id, crypto_id):
    """Calculer et retourner le profit/perte pour une crypto-monnaie spécifique et un ID d'entrée donné"""
    try:
        result = calculate_crypto_profit_loss(entry_id, crypto_id)
        logging.info(f"Profit/perte calculé pour {crypto_id} dans l'entrée {entry_id}: {result}")
        return jsonify(result)
    except Exception as e:
        logging.error(f"Erreur lors du calcul du profit/perte pour {crypto_id} dans l'entrée {entry_id}: {e}")
        return jsonify({"error": "Erreur Interne"}), 500

def get_data_with_retry(url, retries=5, backoff_factor=1.0):
    """Récupérer les données depuis une URL avec des tentatives de réessai en cas d'échec"""
    for i in range(retries):
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if response.status_code == 429:  # Trop de requêtes
                wait_time = backoff_factor * (2 ** i)
                logging.warning(f"Limite de taux dépassée. Attente de {wait_time} secondes.")
                time.sleep(wait_time)
            else:
                raise e
    raise requests.exceptions.RequestException(f"Échec de la récupération des données depuis {url} après {retries} tentatives")

def get_crypto_id(name):
    """Récupérer l'ID d'une crypto-monnaie en fonction de son nom"""
    url = f"https://api.coingecko.com/api/v3/search?query={name}"
    data = get_data_with_retry(url)
    for coin in data['coins']:
        if coin['name'].lower() == name.lower():
            return coin['id']
    return None

def get_crypto_price(crypto_id):
    """Récupérer le prix actuel d'une crypto-monnaie"""
    #logging.error(f"crypto_id {crypto_id}")
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={crypto_id}&vs_currencies=usd"
    logging.error(f"url coingecko : {url}")
    data = get_data_with_retry(url)
    if crypto_id in data:
        return data[crypto_id]['usd']
    else:
        logging.error(f"Données de prix pour {crypto_id} introuvables.")
        return 0

def get_historical_price(crypto_id, date):
    """Récupérer le prix historique d'une crypto-monnaie pour une date donnée"""
    url = f"https://api.coingecko.com/api/v3/coins/{crypto_id}/history?date={date}"
    try:
        data = get_data_with_retry(url)
        return data['market_data']['current_price']['usd']
    except (KeyError, requests.exceptions.RequestException) as e:
        logging.error(f"Erreur lors de la récupération du prix historique pour {crypto_id} à la date {date}: {e}")
        return None

def calculate_profit_loss(entry_id):
    """Calculer le profit/perte pour un ID d'entrée donné"""
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

@app.route('/transactions/<entry_id>', methods=['GET'])
def list_transactions(entry_id):
    """Lister toutes les transactions pour un ID d'entrée donné"""
    transactions = get_transactions(entry_id)
    #logging.info(f"Transactions récupérées pour l'entrée {entry_id}: {transactions}")
    return jsonify(transactions)

@app.route('/all_transactions', methods=['GET'])
def all_transactions():
    """Lister toutes les transactions de toutes les bases de données"""
    entry_ids = []  # Remplacer par une méthode pour récupérer tous les ID d'entrée si nécessaire
    all_transactions = []
    for entry_id in entry_ids:
        transactions = get_transactions(entry_id)
        all_transactions.extend(transactions)
    #logging.info(f"Toutes les transactions récupérées: {all_transactions}")
    return jsonify(all_transactions)

@app.route('/profit_loss/<entry_id>', methods=['GET'])
def profit_loss(entry_id):
    """Calculer et retourner le profit/perte pour un ID d'entrée donné"""
    result = calculate_profit_loss(entry_id)
    logging.info(f"Profit/perte calculé pour l'entrée {entry_id}: {result}")
    return jsonify(result)

@app.route('/transaction/<entry_id>', methods=['POST'])
def create_transaction(entry_id):
    """Créer une nouvelle transaction pour un ID d'entrée donné"""
    try:
        data = request.json
        #logging.info(f"Données reçues pour une nouvelle transaction dans l'entrée {entry_id}: {data}")
        crypto_name = data['crypto_name']
        crypto_id = get_crypto_id(crypto_name)
        if not crypto_id:
            logging.error("Cryptomonnaie introuvable")
            return jsonify({"error": "Cryptomonnaie introuvable"}), 404
        quantity = float(data['quantity'])
        price_usd = float(data['price_usd'])
        transaction_type = data['transaction_type']
        location = data['location']
        date = data['date']
        historical_price = price_usd / quantity
        #historical_price = get_historical_price(crypto_id, datetime.strptime(date, "%Y-%m-%d").strftime("%d-%m-%Y"))
        #if not historical_price:
        #    logging.warning(f"Prix historique non trouvé pour {crypto_id} à la date {date}. Utilisation du prix par défaut.")
        #    historical_price = price_usd / quantity

        add_transaction(entry_id, crypto_name, crypto_id, quantity, price_usd, transaction_type, location, date, historical_price)

        logging.info(f"Transaction ajoutée: {crypto_name}, {crypto_id}, {quantity}, {price_usd}, {transaction_type}, {location}, {date}, {historical_price}")
        return jsonify({"message": "Transaction ajoutée"}), 201
    except Exception as e:
        logging.error(f"Erreur lors de l'ajout de la transaction: {e}")
        return jsonify({"error": "Erreur Interne"}), 500


@app.route('/transaction/<entry_id>/<int:transaction_id>', methods=['DELETE'])
def delete_transaction_endpoint(entry_id, transaction_id):
    """Supprimer une transaction pour un ID d'entrée donné"""
    try:
        #logging.info(f"Tentative de suppression de la transaction avec ID: {transaction_id} dans l'entrée {entry_id}")
        delete_transaction(entry_id, transaction_id)
        logging.info(f"Transaction avec ID: {transaction_id} supprimée dans l'entrée {entry_id}")
        return jsonify({"message": "Transaction supprimée"}), 200
    except Exception as e:
        logging.error(f"Erreur lors de la suppression de la transaction: {e}")
        return jsonify({"error": "Erreur Interne"}), 500

@app.route('/transaction/<entry_id>/<int:transaction_id>', methods=['PUT'])
def update_transaction_endpoint(entry_id, transaction_id):
    """Mettre à jour une transaction pour un ID d'entrée donné"""
    try:
        data = request.json
        #logging.info(f"Données reçues pour la mise à jour de la transaction dans l'entrée {entry_id}: {data}")
        crypto_name = data['crypto_name']
        crypto_id = get_crypto_id(crypto_name)
        if not crypto_id:
            logging.error("Cryptomonnaie introuvable")
            return jsonify({"error": "Cryptomonnaie introuvable"}), 404
        quantity = float(data['quantity'])
        price_usd = float(data['price_usd'])
        transaction_type = data['transaction_type']
        location = data['location']
        date = data['date']
        historical_price = price_usd / quantity
        #historical_price = get_historical_price(crypto_id, datetime.strptime(date, "%Y-%m-%d").strftime("%d-%m-%Y"))
        #if not historical_price:
        #    historical_price = price_usd / quantity

        update_transaction(entry_id, transaction_id, crypto_name, crypto_id, quantity, price_usd, transaction_type, location, date, historical_price)
        logging.info(f"Transaction mise à jour avec ID: {transaction_id} dans l'entrée {entry_id}")
        return jsonify({"message": "Transaction mise à jour"}), 200
    except Exception as e:
        logging.error(f"Erreur lors de la mise à jour de la transaction: {e}")
        return jsonify({"error": "Erreur Interne"}), 500

@app.route('/transactions/<entry_id>/<crypto_id>', methods=['GET'])
def list_crypto_transactions(entry_id, crypto_id):
    """Lister toutes les transactions pour un ID d'entrée donné et un crypto_id spécifique"""
    transactions = get_crypto_transactions(entry_id, crypto_id)
    logging.info(f"Transactions récupérées pour l'entrée {entry_id} et crypto_id {crypto_id}: {transactions}")
    return jsonify(transactions)

@app.route('/delete_crypto/<entry_id>/<crypto_id>', methods=['DELETE'])
def delete_crypto(entry_id, crypto_id):
    """Supprimer une crypto-monnaie pour un ID d'entrée donné"""
    success = delete_crypto_db(entry_id, crypto_id)
    if success:
        return jsonify({"message": "Crypto supprimée"}), 200
    else:
        return jsonify({"error": "Erreur Interne"}), 500
    

@app.route('/export_db/<entry_id>', methods=['GET'])
def export_database(entry_id):
    try:
        return export_db(entry_id)
    except Exception as e:
        return jsonify({"error": "Erreur Interne"}), 500

@app.route('/import_db', methods=['POST'])
def import_database():
    try:
        entry_id = request.form['entry_id']
        file = request.files['file']
        db_path = get_database_path(entry_id)
        with open(db_path, 'wb') as db_file:
            db_file.write(file.read())

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM transactions')
        transactions = cursor.fetchall()
        logging.info(f"Transactions lues depuis le fichier: {transactions}")

        cursor.execute('SELECT crypto_name, crypto_id FROM cryptos')
        cryptos = cursor.fetchall()
        logging.info(f"Cryptos lues depuis le fichier: {cryptos}")

        conn.close()

        # Assurez-vous que chaque transaction a au moins 9 colonnes
        formatted_transactions = []
        for transaction in transactions:
            if len(transaction) >= 9:
                formatted_transactions.append(transaction)
            else:
                logging.error(f"Transaction avec nombre de colonnes incorrect: {transaction}")

        import_transactions(entry_id, formatted_transactions)
        missing_cryptos = verify_cryptos(entry_id, cryptos)

        if missing_cryptos:
            return jsonify({"message": "Importation partielle", "missing_cryptos": missing_cryptos}), 200
        else:
            return jsonify({"message": "Importation réussie"}), 200
    except Exception as e:
        logging.error(f"Erreur lors de l'importation de la base de données: {e}")
        return jsonify({"error": "Erreur Interne"}), 500


# Nouvelle fonction pour mettre à jour les prix des cryptos toutes les 5 minutes
def update_crypto_prices():
    while True:
        try:
            cryptos = get_all_tracked_cryptos()
            for crypto in cryptos:
                crypto_id = crypto['crypto_id']
                current_price = get_crypto_price(crypto_id)
                if current_price is not None:
                    save_price_to_cache(crypto_id, current_price)
        except Exception as e:
            logging.error(f"Erreur lors de la mise à jour des prix des cryptos : {e}")
        time.sleep(300)  # 5 minutes

# Fonction pour récupérer toutes les cryptos suivies
def get_all_tracked_cryptos():
    try:
        conn = sqlite3.connect('list_crypto.db')
        cursor = conn.cursor()
        cursor.execute('SELECT crypto_id FROM list_crypto')
        cryptos = cursor.fetchall()
        conn.close()
        return [{"crypto_id": crypto[0]} for crypto in cryptos]
    except sqlite3.Error as e:
        logging.error(f"Erreur lors de la récupération des cryptos suivies : {e}")
        return []

# Fonction pour sauvegarder les prix dans le cache
def save_price_to_cache(crypto_id, current_price):
    try:
        conn = sqlite3.connect('price_cache.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO price_cache (crypto_id, current_price, last_updated)
            VALUES (?, ?, ?)
            ON CONFLICT(crypto_id) DO UPDATE SET
                current_price=excluded.current_price,
                last_updated=excluded.last_updated
        ''', (crypto_id, current_price, datetime.now()))
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        logging.error(f"Erreur lors de la sauvegarde du prix dans le cache : {e}")

# Créer la table list_crypto
def create_list_crypto_table():
    try:
        conn = sqlite3.connect('list_crypto.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS list_crypto (
                crypto_id TEXT PRIMARY KEY,
                crypto_name TEXT
            )
        ''')
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        logging.error(f"Erreur lors de la création de la table list_crypto : {e}")

# Créer la table price_cache
def create_price_cache_table():
    try:
        conn = sqlite3.connect('price_cache.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_cache (
                crypto_id TEXT PRIMARY KEY,
                current_price REAL,
                last_updated TEXT
            )
        ''')
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        logging.error(f"Erreur lors de la création de la table price_cache : {e}")




if __name__ == "__main__":
    create_list_crypto_table()
    create_price_cache_table()
    price_update_thread = threading.Thread(target=update_crypto_prices)
    price_update_thread.daemon = True
    price_update_thread.start()
    app.run(host="0.0.0.0", port=PORT_APP)