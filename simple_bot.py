#!/usr/bin/env python3
import config
from supabase import create_client
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton

print("Starting bot...")

# Setup
supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)

# Keyboards
MAIN_KB = [[KeyboardButton("Join Genesis.BitID")]]
BACK_KB = [[KeyboardButton("Back")]]

async def start(update, context):
    print(f"START from user {update.effective_user.id}")
    kb = ReplyKeyboardMarkup(MAIN_KB, resize_keyboard=True)
    await update.message.reply_text("Welcome! Choose option:", reply_markup=kb)

async def join(update, context):
    print(f"JOIN from user {update.effective_user.id}")
    kb = ReplyKeyboardMarkup(BACK_KB, resize_keyboard=True) 
    await update.message.reply_text("Send selfie to get BitID:", reply_markup=kb)
    context.user_data['want_photo'] = True

async def photo(update, context):
    print(f"PHOTO from user {update.effective_user.id}")
    if context.user_data.get('want_photo'):
        try:
            # Save to database
            user_id = update.effective_user.id
            result = supabase.table("users").insert({"telegram_id": user_id}).execute()
            print(f"DB result: {result}")
            await update.message.reply_text("Thanks! Registered successfully!")
            context.user_data.clear()
            await start(update, context)
        except Exception as e:
            print(f"DB error: {e}")
            await update.message.reply_text(f"Error: {e}")

async def back(update, context):
    print(f"BACK from user {update.effective_user.id}")
    await start(update, context)

async def text(update, context):
    print(f"TEXT: '{update.message.text}' from user {update.effective_user.id}")

# Main
app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.Regex("^Back$"), back))
app.add_handler(MessageHandler(filters.Regex("^Join Genesis.BitID$"), join))
app.add_handler(MessageHandler(filters.PHOTO, photo))
app.add_handler(MessageHandler(filters.TEXT, text))

print("Running...")
app.run_polling()
