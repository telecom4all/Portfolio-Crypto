#!/bin/bash

# Créez le répertoire si nécessaire
mkdir -p /config/custom_components/portfolio_crypto
mkdir -p /config/www

# Copiez le composant personnalisé dans le répertoire custom_components de Home Assistant
cp -r /app/custom_components/portfolio_crypto/* /config/custom_components/portfolio_crypto/

# Copiez le fichier JavaScript du panneau personnalisé dans le répertoire www de Home Assistant
#cp /app/crypto-transactions-panel.js /config/www/
#cp /app/icon_portfolio_crypto.png /config/www/

# Ajouter la configuration du panneau personnalisé dans configuration.yaml
#CONFIG_FILE="/config/configuration.yaml"
#PANEL_CONFIG="
#panel_custom:
#  - name: crypto-transactions-panel
#    sidebar_title: 'Transactions Crypto' #Nom affiché sur la sidebar
#    sidebar_icon: 'mdi:currency-usd' #icone de la sidebar
#    js_url: '/local/crypto-transactions-panel.js'
#    config:
#      entry_id: your_entry_id # entry_id de votre db
#      entry_name: your_entry_name # nom du portefeuille 
#"

#if ! grep -q "panel_custom:" "$CONFIG_FILE"; then
#    echo "$PANEL_CONFIG" >> "$CONFIG_FILE"
#else
#    echo "La configuration du panneau personnalisé existe déjà dans configuration.yaml"
#fi

# Vérifiez et ajoutez la section homeassistant: et external_url: dans configuration.yaml
CONFIG_FILE="/config/configuration.yaml"
HOMEASSISTANT_SECTION="homeassistant:"
EXTERNAL_URL="external_url: \"https://domain\""
EXTERNAL_URL_test="external_url:"

if ! grep -q "^$HOMEASSISTANT_SECTION" "$CONFIG_FILE"; then
    echo -e "\n$HOMEASSISTANT_SECTION\n  $EXTERNAL_URL" >> "$CONFIG_FILE"
    echo "Section homeassistant: ajoutée avec external_url: dans configuration.yaml"
else
    if ! grep -q "^  $EXTERNAL_URL_test" "$CONFIG_FILE"; then
        sed -i "/^$HOMEASSISTANT_SECTION/a\  $EXTERNAL_URL" "$CONFIG_FILE"
        echo "external_url: ajoutée dans la section homeassistant: existante de configuration.yaml"
    else
        echo "La section homeassistant: et external_url: existent déjà dans configuration.yaml"
    fi
fi


# Vérifiez et ajoutez la configuration portfolio_crypto: dans configuration.yaml
#PORTFOLIO_CRYPTO_CONFIG="
#portfolio_crypto:
#  update_interval: 10
#  rate_limit: 30
#  update_interval_sensor: 15
#  port_app: 5000
#"

#if ! grep -q "^portfolio_crypto:" "$CONFIG_FILE"; then
#    echo "$PORTFOLIO_CRYPTO_CONFIG" >> "$CONFIG_FILE"
#    echo "Configuration portfolio_crypto ajoutée dans configuration.yaml"
#else
#    echo "La configuration portfolio_crypto existe déjà dans configuration.yaml"
#fi


# Créer le fichier de configuration de Gunicorn
GUNICORN_CONF="/app/gunicorn.conf.py"

cat <<EOL > $GUNICORN_CONF
import logging
import logging.config

# Configuration de la journalisation avec horodatage
logging_config = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '%(asctime)s %(levelname)s:%(name)s:%(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'default',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}

def on_starting(server):
    logging.config.dictConfig(logging_config)

def post_fork(server, worker):
    logging.config.dictConfig(logging_config)
EOL

# Démarrer l'application Flask avec Gunicorn
gunicorn --config $GUNICORN_CONF --bind 0.0.0.0:5000 portfolio_crypto.portfolio_crypto:app &
gunicorn --config $GUNICORN_CONF --bind 0.0.0.0:8099 portfolio_crypto.portfolio_crypto:app &

# Attendre que l'application Flask démarre correctement
sleep 5

# Afficher un message à l'utilisateur pour redémarrer Home Assistant
echo "L'installation est terminée. Veuillez redémarrer Home Assistant pour terminer la configuration."

# Continuer à exécuter Gunicorn en premier plan
wait


