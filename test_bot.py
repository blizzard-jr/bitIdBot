#!/usr/bin/env python3
import logging
import config
from supabase import create_client, Client

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# Enable logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Supabase setup
supabase: Client = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)

# Simple keyboards
MAIN_KEYBOARD = [[KeyboardButton("Join Genesis.BitID")], [KeyboardButton("Test")]]
BACK_KEYBOARD = [[KeyboardButton("🔙 Back")]]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start command."""
    logger.info(f"START command from user {update.effective_user.id}")
    reply_markup = ReplyKeyboardMarkup(MAIN_KEYBOARD, resize_keyboard=True)
    await update.message.reply_text("TEST BOT - Choose option:", reply_markup=reply_markup)


async def handle_join(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle Join button."""
    logger.info(f"JOIN button pressed by user {update.effective_user.id}")
    reply_markup = ReplyKeyboardMarkup(BACK_KEYBOARD, resize_keyboard=True)
    await update.message.reply_text("Send me a selfie!", reply_markup=reply_markup)
    context.user_data['waiting_photo'] = True


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle photo."""
    logger.info(f"PHOTO received from user {update.effective_user.id}")
    
    if context.user_data.get('waiting_photo'):
        try:
            # Test database insert
            telegram_id = update.effective_user.id
            result = supabase.table("users").insert({"telegram_id": telegram_id}).execute()
            logger.info(f"Database insert result: {result}")
            
            await update.message.reply_text("Photo received and saved to database!")
            context.user_data.clear()
            
        except Exception as e:
            logger.error(f"Error saving to database: {e}")
            await update.message.reply_text(f"Error: {e}")
    else:
        await update.message.reply_text("I wasn't expecting a photo.")


async def handle_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle back button."""
    logger.info(f"BACK button pressed by user {update.effective_user.id}")
    await start(update, context)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle any text message."""
    logger.info(f"TEXT received: '{update.message.text}' from user {update.effective_user.id}")


def main():
    """Run the bot."""
    logger.info("Creating application...")
    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Regex("^🔙 Back$"), handle_back))
    application.add_handler(MessageHandler(filters.Regex("^Join Genesis.BitID$"), handle_join))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT, handle_text))

    logger.info("Starting polling...")
    application.run_polling()


if __name__ == "__main__":
    main()
