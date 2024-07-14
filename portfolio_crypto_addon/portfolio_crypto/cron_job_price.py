import logging
import asyncio
import aiocron
from .price_updater import update_crypto_prices

# Configurer les logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s:%(name)s:%(message)s')

@aiocron.crontab('*/5 * * * *')
async def scheduled_task():
    logging.info("Tâche cron démarrée")
    try:
        await update_crypto_prices()
        logging.info("Tâche cron terminée avec succès")
    except Exception as e:
        logging.error(f"Erreur lors de l'exécution de la tâche cron : {e}")

async def main():
    logging.info("Starting scheduled tasks...")
    # Start the cron job manually to avoid waiting for the first interval
    await scheduled_task()
    # Keep the script running to allow the cron job to run
    while True:
        await asyncio.sleep(120)  # Sleep for 1 minute

if __name__ == "__main__":
    asyncio.run(main())