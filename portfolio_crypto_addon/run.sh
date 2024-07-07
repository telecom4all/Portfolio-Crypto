#!/bin/bash

# Créez le répertoire si nécessaire
mkdir -p /config/custom_components/portfolio_crypto
mkdir -p /config/www

# Copiez le composant personnalisé dans le répertoire custom_components de Home Assistant
cp -r /app/custom_components/portfolio_crypto/* /config/custom_components/portfolio_crypto/

# Copiez le fichier JavaScript du panneau personnalisé dans le répertoire www de Home Assistant
cp /app/crypto-transactions-panel.js /config/www/
cp /app/icon_portfolio_crypto.png /config/www/

# Ajouter la configuration du panneau personnalisé dans configuration.yaml
CONFIG_FILE="/config/configuration.yaml"
PANEL_CONFIG="
panel_custom:
  - name: crypto-transactions-panel
    sidebar_title: 'Transactions Crypto' #Nom affiché sur la sidebar
    sidebar_icon: 'mdi:currency-usd' #icone de la sidebar
    js_url: '/local/crypto-transactions-panel.js'
    config:
      entry_id: your_entry_id # entry_id de votre db
      entry_name: your_entry_name # nom du portefeuille 
"

if ! grep -q "panel_custom:" "$CONFIG_FILE"; then
    echo "$PANEL_CONFIG" >> "$CONFIG_FILE"
else
    echo "La configuration du panneau personnalisé existe déjà dans configuration.yaml"
fi

# Démarrer l'application Flask avec Gunicorn
if [ "${INGRESS}" == "true" ]; then
    gunicorn --bind 0.0.0.0:8099 portfolio_crypto.portfolio_crypto:app &
else
    gunicorn --bind 0.0.0.0:5000 portfolio_crypto.portfolio_crypto:app &
fi

# Attendre que l'application Flask démarre correctement
sleep 5

# Afficher un message à l'utilisateur pour redémarrer Home Assistant
echo "L'installation est terminée. Veuillez redémarrer Home Assistant pour terminer la configuration."

# Continuer à exécuter Gunicorn en premier plan
wait
