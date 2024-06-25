FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy source code
COPY portfolio_crypto_addon/portfolio_crypto /app/portfolio_crypto
COPY portfolio_crypto_addon/requirements.txt /app/requirements.txt
COPY portfolio_crypto_addon/run.sh /app/run.sh
COPY custom_components/portfolio_crypto /app/custom_components/portfolio_crypto
COPY portfolio_crypto_addon/portfolio_crypto/wsgi.py /app/wsgi.py

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN pip list

# Make run.sh executable
RUN chmod +x /app/run.sh

# Expose port
EXPOSE 5000

# Command to run the application
CMD ["/app/run.sh"]
