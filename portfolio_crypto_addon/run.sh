#!/bin/bash

# Copy the custom component to the Home Assistant custom_components directory
cp -r /app/portfolio_crypto /config/custom_components/portfolio_crypto

# Start the Flask app using Gunicorn
exec gunicorn --bind 0.0.0.0:5000 portfolio_crypto.wsgi:app
