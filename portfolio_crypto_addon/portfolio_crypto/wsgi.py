"""
Fichier wsgi.py
Ce fichier est le point d'entrée pour Gunicorn afin de lancer l'application Flask pour l'addon Portfolio Crypto.
"""

from portfolio_crypto.portfolio_crypto import app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
