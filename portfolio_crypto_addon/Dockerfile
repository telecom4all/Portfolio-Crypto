# Fichier Dockerfile
# Ce fichier configure l'image Docker pour l'addon Portfolio Crypto.

FROM python:3.9-slim-buster

# Définir le répertoire de travail
WORKDIR /app

# Copier le code source
COPY portfolio_crypto_addon/portfolio_crypto /app/portfolio_crypto
COPY portfolio_crypto_addon/requirements.txt /app/requirements.txt
COPY portfolio_crypto_addon/run.sh /app/run.sh
COPY custom_components/portfolio_crypto /app/custom_components/portfolio_crypto
COPY portfolio_crypto_addon/portfolio_crypto/wsgi.py /app/wsgi.py
#COPY portfolio_crypto_addon/crypto-transactions-panel.js /app/crypto-transactions-panel.js
COPY portfolio_crypto_addon/portfolio_crypto/db.py /app/custom_components/portfolio_crypto/db.py
COPY custom_components/portfolio_crypto/icon_portfolio_crypto.png /app/icon_portfolio_crypto.png
COPY portfolio_crypto_addon/portfolio_crypto/outils.py /app/custom_components/portfolio_crypto/outils.py

COPY custom_components/portfolio_crypto/const.py /app/const.py
COPY custom_components/portfolio_crypto/const.py /app/portfolio_crypto/const.py

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt
RUN pip list

# Installer Nginx
RUN apt-get update && apt-get install -y nginx sqlite3 && mkdir -p /run/nginx && rm -rf /var/lib/apt/lists/*

# Copier le fichier de configuration Nginx
COPY portfolio_crypto_addon/ingress.conf /etc/nginx/http.d/

# Rendre run.sh exécutable
RUN chmod +x /app/run.sh

# Exposer les ports
EXPOSE 5000 
EXPOSE 8099
# Commande pour exécuter l'application
CMD ["/app/run.sh"]
