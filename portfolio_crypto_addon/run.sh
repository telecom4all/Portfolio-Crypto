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
    sidebar_title: 'Transactions Crypto' # Nom affiché sur la sidebar
    sidebar_icon: 'mdi:currency-usd' # icone de la sidebar
    js_url: '/local/crypto-transactions-panel.js'
    config:
      entry_id: your_entry_id # entry_id de votre db
      entry_name: your_entry_name # nom du portefeuille 
ingress:
  panel_custom:
    - name: ingress
      title: 'Crypto Transactions'
      icon: 'mdi:currency-usd'
      url_path: 'portfolio_crypto'
"

if ! grep -q "panel_custom:" "$CONFIG_FILE"; then
    echo "$PANEL_CONFIG" >> "$CONFIG_FILE"
else
    echo "La configuration du panneau personnalisé existe déjà dans configuration.yaml"
fi

# Lancez l'application
exec python3 -m portfolio_crypto.portfolio_crypto
