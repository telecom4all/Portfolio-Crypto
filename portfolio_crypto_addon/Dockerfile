FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy source code
COPY ../portfolio_crypto /app/portfolio_crypto
COPY ../portfolio_crypto_addon/requirements.txt /app/requirements.txt
COPY ../portfolio_crypto_addon/run.sh /app/run.sh

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN pip list  # Ajoutez cette ligne pour lister les modules installés

# Make run.sh executable
RUN chmod +x /app/run.sh

# Expose port
EXPOSE 5000

# Command to run the application
CMD ["/app/run.sh"]


#CMD ["/app/run.sh"]
