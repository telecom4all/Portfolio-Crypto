FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy source code
COPY portfolio_crypto /app/portfolio_crypto
COPY requirements.txt /app/requirements.txt
COPY run.sh /app/run.sh

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Make run.sh executable
RUN chmod +x /app/run.sh

# Expose port
EXPOSE 5000

# Command to run the application
CMD ["/app/run.sh"]
