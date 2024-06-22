#!/bin/bash
# Start the Flask app using Gunicorn
exec gunicorn --bind 0.0.0.0:5000 portfolio_crypto.wsgi:app
