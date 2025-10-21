#!/usr/bin/env python3
import logging
from supabase import create_client
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton

# Direct config (no import)
TELEGRAM_BOT_TOKEN = "7705239177:AAHGCmjy0f3c8Ue10l538WDZLLkB0AYjcF8"
SUPABASE_URL = "https://dmkaespwshdwhghwbzmz.supabase.co"
SUPABASE_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRta2Flc3B3c2hkd2hnaHdiem16Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1OTE1MzI3NSwiZXhwIjoyMDc0NzI5Mjc1fQ.p9Jhu-NdFVh5bw24xeuLHzo1di-F_T6RI_reA1Xa0_c"

print(f"Starting bot with token: {TELEGRAM_BOT_TOKEN[:20]}...")

# Setup
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Keyboards
MAIN_KB = [
    [KeyboardButton("About BitID")],
    [KeyboardButton("Join Genesis.BitID")],
    [KeyboardButton("Discuss, ask about BitID.(ai)")],
]
BACK_KB = [[KeyboardButton("🔙 Back to Main Menu")]]

async def start(update, context):
    print(f"START from user {update.effective_user.id}")
    kb = ReplyKeyboardMarkup(MAIN_KB, resize_keyboard=True)
    await update.message.reply_text("Добро пожаловать! Пожалуйста, выберите опцию:", reply_markup=kb)
    context.user_data.clear()

async def about_bitid(update, context):
    print(f"ABOUT from user {update.effective_user.id}")
    kb = ReplyKeyboardMarkup(BACK_KB, resize_keyboard=True) 
    await update.message.reply_text("BitID - это цифровой идентификатор на основе вашего лица.", reply_markup=kb)

async def join(update, context):
    print(f"JOIN from user {update.effective_user.id}")
    telegram_id = update.effective_user.id
    kb = ReplyKeyboardMarkup(BACK_KB, resize_keyboard=True)
    
    try:
        # Check if user exists
        response = supabase.table("users").select("id").eq("telegram_id", telegram_id).execute()
        print(f"DB check result: {response}")
        
        if response.data and len(response.data) > 0:
            # User exists - try to show photo
            try:
                import time
                # Add timestamp to avoid cache issues
                cache_buster = int(time.time())
                photo_url = supabase.storage.from_("user_selfies").get_public_url(f"{telegram_id}.jpg")
                photo_url_with_cache_buster = f"{photo_url}?v={cache_buster}"
                print(f"Photo URL with cache buster: {photo_url_with_cache_buster}")
                await update.message.reply_photo(
                    photo=photo_url_with_cache_buster,
                    caption="Вот твое фото для регистрации:\n\nЕсли хочешь заменить - пришли новое селфи.",
                    reply_markup=kb,
                )
                context.user_data['awaiting_selfie_replacement'] = True
            except Exception as photo_error:
                print(f"Photo error: {photo_error}")
                await update.message.reply_text("Вы зарегистрированы, но фото не найдено. Пришлите новое селфи.", reply_markup=kb)
                context.user_data['awaiting_selfie_replacement'] = True
        else:
            # User doesn't exist
            await update.message.reply_text("У тебя нет BitID. Пришли селфи чтобы получить BitID.", reply_markup=kb)
            context.user_data['awaiting_selfie_registration'] = True
            
    except Exception as e:
        print(f"DB error: {e}")
        await update.message.reply_text("У тебя нет BitID. Пришли селфи чтобы получить BitID.", reply_markup=kb)
        context.user_data['awaiting_selfie_registration'] = True

async def photo(update, context):
    print(f"PHOTO from user {update.effective_user.id}")
    print(f"User state: {context.user_data}")
    
    if context.user_data.get('awaiting_selfie_registration') or context.user_data.get('awaiting_selfie_replacement'):
        try:
            # Download photo
            photo_file = await update.message.photo[-1].get_file()
            file_content = await photo_file.download_as_bytearray()
            telegram_id = update.effective_user.id
            file_path = f"{telegram_id}.jpg"
            print(f"Photo downloaded, size: {len(file_content)} bytes")

            # Upload to storage (force overwrite)
            try:
                # Try to remove existing file first
                supabase.storage.from_("user_selfies").remove([file_path])
                print(f"Removed existing file: {file_path}")
            except:
                print(f"No existing file to remove: {file_path}")
                
            upload_result = supabase.storage.from_("user_selfies").upload(
                file=bytes(file_content), 
                path=file_path, 
                file_options={"content-type": "image/jpeg"}
            )
            print(f"Upload result: {upload_result}")

            if context.user_data.get('awaiting_selfie_registration'):
                # Register new user
                insert_result = supabase.table("users").insert({"telegram_id": telegram_id}).execute()
                print(f"User registration result: {insert_result}")
                await update.message.reply_text("Спасибо за регистрацию! Мы отправим тебе BitID как только он будет сформирован.")
            else:
                await update.message.reply_text("Ваше фото было обновлено!")
            
            context.user_data.clear()
            # Return to main menu
            import asyncio
            await asyncio.sleep(1)
            await start(update, context)
            
        except Exception as e:
            print(f"Photo processing error: {e}")
            await update.message.reply_text(f"Ошибка обработки фото: {e}")
    else:
        print("Photo sent without registration state")
        await update.message.reply_text("Нажмите 'Join Genesis.BitID' чтобы зарегистрироваться.")

async def ai_chat(update, context):
    print(f"AI CHAT from user {update.effective_user.id}")
    kb = ReplyKeyboardMarkup(BACK_KB, resize_keyboard=True) 
    await update.message.reply_text("Привет! Я - Бадди, я помогаю тебе узнать о BitID. Задавайте вопросы!", reply_markup=kb)
    context.user_data['ai_chat_enabled'] = True

async def back(update, context):
    print(f"BACK from user {update.effective_user.id}")
    await start(update, context)

async def text(update, context):
    print(f"TEXT: '{update.message.text}' from user {update.effective_user.id}")
    
    if context.user_data.get('ai_chat_enabled'):
        await update.message.reply_text("Это тестовый ответ ИИ. Спросите что-то о BitID!")

# Main
print("Creating application...")
app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

# Handlers
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.Regex("^🔙 Back to Main Menu$"), back))
app.add_handler(MessageHandler(filters.Regex("^About BitID$"), about_bitid))
app.add_handler(MessageHandler(filters.Regex("^Join Genesis.BitID$"), join))
app.add_handler(MessageHandler(filters.Regex("^Discuss, ask about BitID.\\(ai\\)$"), ai_chat))
app.add_handler(MessageHandler(filters.PHOTO, photo))
app.add_handler(MessageHandler(filters.TEXT, text))

print("Starting bot...")
app.run_polling()
