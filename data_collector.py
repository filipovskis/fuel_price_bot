import logging
import unicodedata

from telegram.ext import ContextTypes
from classes.fuel_station import *
from loader import db
from telegram_bot import send_price_update, ping_update

logger = logging.getLogger(__name__)
stations = {Circle_K(), Neste(), Virsi()}

def normalize_text(text):
    return unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')

async def process_data(context, station: FuelStation, data: dict):
    logger.info(f"Processing received data for {station.name}: {data}")
    ping_update()

    changes = {}

    for fuel_type, price in data.items():
        fuel_type = normalize_text(fuel_type)

        previous_price = db.get_price(station, fuel_type)
        old_exists = previous_price is not None
    
        logger.info(f"Previous price for {fuel_type} at {station.name}: {previous_price}")
        
        if not old_exists or price != previous_price:
            logger.info(f"Price change detected for {fuel_type} at {station.name}: {previous_price} -> {price}")
        
            if old_exists:
                db.insert_price_change(station, fuel_type, previous_price, price)
                changes[fuel_type] = (previous_price, price)

            db.update_price(station, fuel_type, price)
        else:
            logger.info(f"No price change for {fuel_type} at {station.name}. Current price: {price}")
    
    if changes:
        try:
            await send_price_update(context, station, changes)
        except Exception as e:
            logger.error(f"Error sending price update for {station.name}: {e}")

async def collect_data(context):
    logger.info("Starting data collection...")
    for station in stations:
        try:
            logger.info(f"Collecting data for {station.name}...")
            received_data = station.collect_data()

            if received_data:
                await process_data(context, station, received_data)
        except Exception as e:
            logger.error(f"Error collecting data for {station.name}: {e}")

async def run_collector(context: ContextTypes.DEFAULT_TYPE):
    try:
        await collect_data(context)
    except Exception as e:
        logger.error(f"Error during data collection: {e}")
        