#!/bin/bash

# Créez le répertoire si nécessaire
mkdir -p /config/custom_components/portfolio_crypto

# Copiez le composant personnalisé dans le répertoire custom_components de Home Assistant
cp -r /app/custom_components/portfolio_crypto/* /config/custom_components/portfolio_crypto/

# Copier le fichier JavaScript pour la carte Lovelace personnalisée
cp /app/www/crypto-transactions-card.js /config/www/

# Vérifier si ui-lovelace.yaml existe, sinon le créer
if [ ! -f /config/ui-lovelace.yaml ]; then
    touch /config/ui-lovelace.yaml
fi

# Vérifier et ajouter la ressource Lovelace si elle n'est pas déjà présente
if ! grep -q 'crypto-transactions-card.js' /config/ui-lovelace.yaml; then
    echo 'resources:' >> /config/ui-lovelace.yaml
    echo '  - url: /local/crypto-transactions-card.js' >> /config/ui-lovelace.yaml
    echo '    type: module' >> /config/ui-lovelace.yaml
fi

# Démarrer l'application Flask avec Gunicorn
gunicorn --bind 0.0.0.0:5000 portfolio_crypto.portfolio_crypto:app &

# Attendre que l'application Flask démarre correctement
sleep 5

# Debug: afficher le token et l'URL
echo "Token: $SUPERVISOR_TOKEN"
echo "Restarting Home Assistant..."

# Redémarrer Home Assistant
response=$(curl -s -o /dev/null -w "%{http_code}" -X POST -H "Authorization: Bearer $SUPERVISOR_TOKEN" -H "Content-Type: application/json" http://supervisor/core/restart)

# Debug: vérifier le statut de la requête curl
if [ "$response" -ne 200 ]; then
    echo "Erreur lors du redémarrage de Home Assistant. Code de réponse: $response"
else
    echo "Home Assistant redémarré avec succès."
fi

# Continuer à exécuter Gunicorn en premier plan
wait
