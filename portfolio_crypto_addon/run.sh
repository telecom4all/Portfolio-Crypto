#!/bin/bash

# Créez le répertoire si nécessaire
mkdir -p /config/custom_components/portfolio_crypto

# Copiez le composant personnalisé dans le répertoire custom_components de Home Assistant
cp -r /app/custom_components/portfolio_crypto/* /config/custom_components/portfolio_crypto/

# Démarrez l'application Flask avec Gunicorn
exec gunicorn --bind 0.0.0.0:5000 portfolio_crypto.portfolio_crypto:app