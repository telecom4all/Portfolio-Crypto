"""
Fichier const.py
Ce fichier contient les constantes utilisées pour l'intégration Portfolio Crypto.
"""

DOMAIN = "portfolio_crypto"
COINGECKO_API_URL = "https://api.coingecko.com/api/v3/coins/list"
COINGECKO_API_URL_PRICE = "https://api.coingecko.com/api/v3"
VS_CURRENCIES = "usd"
UPDATE_INTERVAL = 10 # Intervalle de mise à jour en minutes
RATE_LIMIT = 30  # Limite de taux en minutes pour les requêtes à CoinGecko
UPDATE_INTERVAL_SENSOR = 15 # Intervalle de mise à jour en minutes
PORT_APP = 5000
PATH_DB_BASE = "/config/portfolio_crypto"
