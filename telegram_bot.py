# test

import time
import logging
import localization.english as msg

from classes.fuel_station import FuelStation, get_station_by_name
from loader import db

from datetime import datetime
from zoneinfo import ZoneInfo #  this one requires python 3.9+
from telegram.helpers import escape_markdown
from telegram import Update, Chat, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler

lastUpdate = None

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

def get_time(unix_timestamp):
    return datetime.fromtimestamp(unix_timestamp, tz=ZoneInfo("Europe/Riga"))

def escape(text: str) -> str:
    return escape_markdown(text=text, version=2)

def get_fuel_icon(station : FuelStation, fuel_type: str) -> str:
    is_diesel = station.is_diesel(fuel_type)
    is_lpg = station.is_lpg(fuel_type)
    if is_diesel:
        return "⚫"
    elif is_lpg:
        return "💨"
    else:
        return "🟢"

def ping_update():
    global lastUpdate
    lastUpdate = time.time()

# external

async def send_price_update(context: ContextTypes.DEFAULT_TYPE, station: FuelStation, changes: dict):
    message = msg.PRICE_UPDATE_HEADER.format(station=station.name) + "\n"
    for fuel_type, (old_price, new_price) in changes.items():
        diff = round(new_price - old_price, 2)
        icon = "📈" if diff > 0 else "📉" if diff < 0 else ""
        baseIcon = get_fuel_icon(station, fuel_type)

        diff_str = escape_markdown(text=f"{diff:+.2f}", version=2)
        fuel_type_str = escape_markdown(text=fuel_type, version=2) # Miles+ and etc.
        new_price_str = escape_markdown(text=f"{new_price:.2f}", version=2)

        message += f"• {baseIcon} *{fuel_type_str}*: {new_price_str}€ \\(*{diff_str}€* {icon}\\)\n"

    subscribers = db.get_subscribers()
    for subscriber in subscribers:
        chat_id = subscriber[0]
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode="MarkdownV2"
            )
        except Exception as e:
            logger.error(f"Error sending price update to chat_id {chat_id}: {e}")

# --------------
# utils
# --------------
async def shared_response(update: Update, text: str):
    if update.message is not None:
        await update.message.reply_text(text, parse_mode="MarkdownV2")
    elif update.callback_query is not None:
        await update.callback_query.answer(text, show_alert=True)

async def request_subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    logger.info(f"Subscription request from chat_id: {chat.id}, username: {chat.username}")

    if db.is_subscribed(chat):
        if update.message is not None:
            await update.message.reply_text(msg.ALREADY_SUBSCRIBED, parse_mode="MarkdownV2")
        else:
            await update.callback_query.answer(msg.ALREADY_SUBSCRIBED, show_alert=True)
    else:
        db.add_subscriber(chat)
        if update.message is not None:
            await update.message.reply_text(msg.SUBSCRIBED, parse_mode="MarkdownV2")
        else:
            await update.callback_query.answer(msg.SUBSCRIBED, show_alert=True)

async def request_unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    logger.info(f"Unsubscription request from chat_id: {chat.id}, username: {chat.username}")

    if db.is_subscribed(chat):
        db.remove_subscriber(chat)
        if update.message is not None:
            await update.message.reply_text("You have successfully unsubscribed from updates.", parse_mode="MarkdownV2")
        else:
            await update.callback_query.answer("You have successfully unsubscribed from updates.", show_alert=True)
    else:
        if update.message is not None:
            await update.message.reply_text("You are not currently subscribed to updates.", parse_mode="MarkdownV2")
        else:
            await update.callback_query.answer("You are not currently subscribed to updates.", show_alert=True)

async def request_prices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prices = db.get_prices()
    if not prices:
        await shared_response(update, "No price data available.")
        return

    timePassed = time.time() - lastUpdate if lastUpdate else None
    # support seconds, minutes and hours
    timePassedStr = (f"{round(timePassed)} seconds ago" if timePassed and timePassed < 60 else
                     f"{round(timePassed / 60)} minutes ago" if timePassed and timePassed < 3600 else
                     f"{round(timePassed / 3600)} hours ago" if timePassed else "No updates yet")
    
    message = msg.STATUS_HEADER.format(timeAgo=timePassedStr)
    inserted_headers = {}
    cheapest_in_each_category = {}

    for company, fuel_type, price in prices:
        station = get_station_by_name(company)

        if station is None:
            continue

        if not inserted_headers.get(company, False):
            message += f"\n⛽️ *{escape(company)}*:\n"
            inserted_headers[company] = True

        fuel_icon = get_fuel_icon(station, fuel_type)
        message += f"• {fuel_icon} *{escape(fuel_type)}*: {escape(f'{price:.2f}')}€\n"

        # track cheapest fuel in each category
        category = "Diesel" if station.is_diesel(fuel_type) else "LPG" if station.is_lpg(fuel_type) else "Petrol"
        if category not in cheapest_in_each_category or price < cheapest_in_each_category[category][2]:
            cheapest_in_each_category[category] = (company, fuel_type, price)

    message += '\n🏆 Cheapest:\n'

    for category, (cheapest_company, cheapest_fuel_type, cheapest_price) in cheapest_in_each_category.items():
        message += f"{category}: *{escape(cheapest_fuel_type)}* at *{escape(cheapest_company)}* for __*{escape(f'{cheapest_price:.2f}')}€*__\n"

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Request new prices", callback_data="request_new")]
    ])

    if update.callback_query is not None:
        await update.callback_query.answer()

    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, parse_mode="MarkdownV2", reply_markup=markup)

async def request_price_changes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    price_changes = db.get_price_changes()
    if not price_changes:
        await shared_response(update, "No price change data available.")
        return
    
    if update.callback_query is not None:
        await update.callback_query.answer()
    
    grouped_by_time = {}
    for company, fuel_type, old_price, new_price, change_date in price_changes:
        if change_date not in grouped_by_time:
            grouped_by_time[change_date] = []
    
        grouped_by_time[change_date].append((company, fuel_type, old_price, new_price))

    message = msg.PRICE_CHANGES_HEADER
    for change_date, changes in grouped_by_time.items():
        date_str = escape(get_time(change_date).strftime("%d.%m.%Y %H:%M"))
        message += f"• \\[{date_str}\\]\n"

        for company, fuel_type, old_price, new_price in changes:
            diff = round(new_price - old_price, 2)
            icon = "📈" if diff > 0 else "📉" if diff < 0 else ""
            fuel_icon = get_fuel_icon(get_station_by_name(company), fuel_type)

            diff_str = escape(text=f"{diff:+.2f}")
            old_price_str = escape(text=f"{old_price:.2f}")
            new_price_str = escape(text=f"{new_price:.2f}")

            line_str = f"  *\\({escape(company)}\\) {escape(fuel_type)}*: *{diff_str}€* {icon} \\({old_price_str}€ → *__{new_price_str}€__*\\)\n"
            message += line_str

        message += "\n"

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🆕 Check current prices", callback_data="request_new")]
    ])

    await context.bot.send_message(chat_id=update.effective_chat.id, text=message, parse_mode="MarkdownV2", reply_markup=markup)

# --------------
# buttons
# --------------

async def update_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    data = query.data

    if ( data is None or data == '' ):
        await query.answer()
        return

    if ( data == "subscribe" ):
        await request_subscribe(update, context)
    elif ( data == "unsubscribe" ):
        await request_unsubscribe(update, context)
    elif ( data == "prices" ):
        await request_prices(update, context)
    elif ( data == "request_new" ):
        await request_prices(update, context)
    elif ( data == 'history' ):
        await request_price_changes(update, context)

# --------------
# commands
# --------------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("⛽ Get current prices", callback_data="prices")],
        [InlineKeyboardButton("📖 Get price history", callback_data="history")],
        [InlineKeyboardButton("🔔 Subscribe to updates", callback_data="subscribe"), InlineKeyboardButton("🔕 Unsubscribe from updates", callback_data="unsubscribe")]
    ])

    is_subscribed = db.is_subscribed(update.effective_chat)
    subscribed_state = msg.SUBSCRIBED_STATUS if is_subscribed else msg.UNSUBSCRIBED_STATUS

    await update.message.reply_text(msg.START.format(subscribed=subscribed_state), parse_mode="Markdown", reply_markup=markup)

async def cmd_subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await request_subscribe(update, context)

async def cmd_unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await request_unsubscribe(update, context)

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await request_prices(update, context)

async def cmd_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await request_price_changes(update, context)

def init_bot():
    try: 
        with open("config/telegram_token.txt", "r") as token_file:
            token = token_file.read().strip()
            if token == "":
                raise ValueError("Telegram token is empty. Please add your bot token to 'config/telegram_token.txt'.")

            application = ApplicationBuilder().token(token).build()
    except FileNotFoundError:
        print("Telegram token file not found. Please create 'config/telegram_token.txt' and add your bot token.")
        exit(1)
    except ValueError as e:
        print(e)
        exit(1)

    application.add_handler(CallbackQueryHandler(update_handler))
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("subscribe", cmd_subscribe))
    application.add_handler(CommandHandler("unsubscribe", cmd_unsubscribe))
    application.add_handler(CommandHandler("status", cmd_status))
    application.add_handler(CommandHandler("history", cmd_history))

    return application