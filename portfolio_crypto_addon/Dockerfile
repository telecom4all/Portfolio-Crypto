# Fichier Dockerfile
# Ce fichier configure l'image Docker pour l'addon Portfolio Crypto.

FROM python:3.9-slim

# Définir le répertoire de travail
WORKDIR /app

# Copier le code source
COPY portfolio_crypto_addon/portfolio_crypto /app/portfolio_crypto
COPY portfolio_crypto_addon/requirements.txt /app/requirements.txt
COPY portfolio_crypto_addon/run.sh /app/run.sh
COPY custom_components/portfolio_crypto /app/custom_components/portfolio_crypto
COPY portfolio_crypto_addon/portfolio_crypto/wsgi.py /app/wsgi.py
COPY portfolio_crypto_addon/crypto-transactions-panel.js /app/crypto-transactions-panel.js
COPY portfolio_crypto_addon/portfolio_crypto/db.py /app/custom_components/portfolio_crypto/db.py

# Installer les dépendances
RUN pip install --no-cache-dir -r requirements.txt
RUN pip list

# Rendre run.sh exécutable
RUN chmod +x /app/run.sh

# Exposer le port
EXPOSE 5000

# Commande pour exécuter l'application
CMD ["/app/run.sh"]

