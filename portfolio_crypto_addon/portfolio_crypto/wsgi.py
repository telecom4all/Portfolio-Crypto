"""
Fichier wsgi.py
Ce fichier est le point d'entrée pour Gunicorn afin de lancer l'application Flask pour l'addon Portfolio Crypto.
"""

from portfolio_crypto.portfolio_crypto import app
from werkzeug.middleware.proxy_fix import ProxyFix

# Appliquer ProxyFix pour prendre en compte les en-têtes du reverse proxy
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)