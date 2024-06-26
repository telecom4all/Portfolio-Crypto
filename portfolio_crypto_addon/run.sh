#!/bin/bash

# Créez le répertoire si nécessaire
mkdir -p /config/custom_components/portfolio_crypto

# Copiez le composant personnalisé dans le répertoire custom_components de Home Assistant
cp -r /app/custom_components/portfolio_crypto/* /config/custom_components/portfolio_crypto/

# Copier le fichier JavaScript pour la carte Lovelace personnalisée
cp /app/www/crypto-transactions-card.js /config/www/

# Vérifier et ajouter la ressource Lovelace si elle n'est pas déjà présente
if ! grep -q 'crypto-transactions-card.js' /config/ui-lovelace.yaml; then
    echo 'resources:' >> /config/ui-lovelace.yaml
    echo '  - url: /local/crypto-transactions-card.js' >> /config/ui-lovelace.yaml
    echo '    type: module' >> /config/ui-lovelace.yaml
fi

# Démarrer l'application Flask avec Gunicorn
exec gunicorn --bind 0.0.0.0:5000 portfolio_crypto.portfolio_crypto:app &

# Attendre que l'application Flask démarre correctement
sleep 5

# Redémarrer Home Assistant
curl -X POST -H "Authorization: Bearer $SUPERVISOR_TOKEN" -H "Content-Type: application/json" http://supervisor/core/restart
