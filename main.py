import logging
import asyncio
import config
from supabase import create_client, Client
from openai import OpenAI

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# Enable detailed logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.DEBUG
)
logger = logging.getLogger(__name__)

# Supabase setup
supabase: Client = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
BUCKET_NAME = "user_selfies"

# OpenAI setup
openai_client = OpenAI(api_key=config.OPENAI_API_KEY)

# Keyboards
MAIN_KEYBOARD = [
    [KeyboardButton("About BitID")],
    [KeyboardButton("Join Genesis.BitID")],
    [KeyboardButton("Discuss, ask about BitID.(ai)")],
]
BACK_KEYBOARD = [[KeyboardButton("🔙 Back to Main Menu")]]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a message with three buttons."""
    logger.info(f"Start command from user {update.message.from_user.id}")
    context.user_data.clear()  # Clear state on /start
    reply_markup = ReplyKeyboardMarkup(MAIN_KEYBOARD, resize_keyboard=True)
    await update.message.reply_text(
        "Добро пожаловать! Пожалуйста, выберите опцию:", reply_markup=reply_markup
    )


async def about_bitid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the 'About BitID' button."""
    logger.info(f"About BitID clicked by user {update.message.from_user.id}")
    reply_markup = ReplyKeyboardMarkup(BACK_KEYBOARD, resize_keyboard=True)
    await update.message.reply_text(
        "BitID - это цифровой идентификатор на основе вашего лица. Он позволяет безопасно подтверждать вашу личность в различных сервисах без паролей и документов. BitID создается на основе уникальных характеристик вашего лица и обеспечивает высокий уровень безопасности.",
        reply_markup=reply_markup,
    )


async def join_genesis(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the 'Join Genesis.BitID' button according to README.md specs."""
    telegram_id = update.message.from_user.id
    logger.info(f"Join Genesis clicked by user {telegram_id}")
    reply_markup = ReplyKeyboardMarkup(BACK_KEYBOARD, resize_keyboard=True)
    
    try:
        # Check if user exists in database
        logger.debug(f"Checking if user {telegram_id} exists in database")
        response = supabase.table("users").select("id, bit_id").eq("telegram_id", telegram_id).execute()
        logger.debug(f"Database response: {response}")
        
        if response.data and len(response.data) > 0:
            # User is registered - try to show their photo
            logger.info(f"User {telegram_id} is registered, showing photo")
            try:
                photo_url = supabase.storage.from_(BUCKET_NAME).get_public_url(f"{telegram_id}.jpg")
                logger.debug(f"Photo URL for user {telegram_id}: {photo_url}")
                
                await update.message.reply_photo(
                    photo=photo_url,
                    caption="Вот твое фото для регистрации:\n\nЕсли хочешь заменить - пришли новое селфи.",
                    reply_markup=reply_markup,
                )
                context.user_data['awaiting_selfie_replacement'] = True
                logger.info(f"Successfully showed photo for user {telegram_id}")
                
            except Exception as photo_error:
                logger.error(f"Error showing photo for user {telegram_id}: {photo_error}")
                # If photo doesn't exist but user is registered, ask for new photo
                await update.message.reply_text(
                    "Вы зарегистрированы, но фото не найдено. Пришлите новое селфи.",
                    reply_markup=reply_markup,
                )
                context.user_data['awaiting_selfie_replacement'] = True
        else:
            # User is not registered
            logger.info(f"User {telegram_id} is not registered, prompting for selfie")
            await update.message.reply_text(
                "У тебя нет BitID. Пришли селфи чтобы получить BitID.",
                reply_markup=reply_markup,
            )
            context.user_data['awaiting_selfie_registration'] = True

    except Exception as e:
        logger.error(f"Error checking user registration for {telegram_id}: {e}")
        # Fallback: assume user is not registered
        await update.message.reply_text(
            "У тебя нет BitID. Пришли селфи чтобы получить BitID.",
            reply_markup=reply_markup,
        )
        context.user_data['awaiting_selfie_registration'] = True


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles user's selfie according to README.md specs."""
    telegram_id = update.message.from_user.id
    logger.info(f"Photo received from user {telegram_id}")
    logger.debug(f"User data state: {context.user_data}")
    
    if context.user_data.get('awaiting_selfie_registration') or context.user_data.get('awaiting_selfie_replacement'):
        logger.info(f"Processing photo for user {telegram_id}")
        try:
            # Download photo from Telegram
            photo_file = await update.message.photo[-1].get_file()
            logger.debug(f"Got photo file: {photo_file}")
            
            file_content = await photo_file.download_as_bytearray()
            logger.debug(f"Downloaded photo, size: {len(file_content)} bytes")
            
            file_path = f"{telegram_id}.jpg"

            # Upload to Supabase Storage
            logger.info(f"Uploading photo to Supabase storage: {file_path}")
            try:
                upload_result = supabase.storage.from_(BUCKET_NAME).upload(
                    file=bytes(file_content), 
                    path=file_path, 
                    file_options={"content-type": "image/jpeg", "upsert": "true"}
                )
                logger.info(f"Photo uploaded successfully: {upload_result}")
            except Exception as upload_error:
                logger.error(f"Upload error: {upload_error}")
                # Try alternative upload method
                try:
                    upload_result = supabase.storage.from_(BUCKET_NAME).upload(
                        file=bytes(file_content), 
                        path=file_path
                    )
                    logger.info(f"Photo uploaded with alternative method: {upload_result}")
                except Exception as upload_error2:
                    logger.error(f"Alternative upload also failed: {upload_error2}")
                    raise upload_error2

            if context.user_data.get('awaiting_selfie_registration'):
                # New user registration - add to database
                logger.info(f"Registering new user {telegram_id} in database")
                try:
                    insert_result = supabase.table("users").insert({"telegram_id": telegram_id}).execute()
                    logger.info(f"User registered successfully: {insert_result}")
                except Exception as insert_error:
                    logger.warning(f"Insert error for user {telegram_id}: {insert_error}")
                    
                # Send success message according to README.md
                await update.message.reply_text(
                    "Спасибо за регистрацию! Мы отправим тебе BitID как только он будет сформирован."
                )
                logger.info(f"Registration complete for user {telegram_id}")
            
            elif context.user_data.get('awaiting_selfie_replacement'):
                # Photo replacement
                await update.message.reply_text(
                    "Ваше фото было обновлено!"
                )
                logger.info(f"Photo updated for user {telegram_id}")
            
            # Clear state and return to main menu
            context.user_data.clear()
            await asyncio.sleep(1)
            await start(update, context)

        except Exception as e:
            logger.error(f"Error processing photo for user {telegram_id}: {e}")
            await update.message.reply_text(
                "Не удалось сохранить ваше фото. Попробуйте снова."
            )
    else:
        logger.info(f"Photo sent outside of registration flow by user {telegram_id}")
        # Photo sent outside of registration flow - redirect to AI chat
        if not context.user_data.get('ai_chat_enabled'):
            await start_ai_chat(update, context)
        else:
            await update.message.reply_text(
                "Отличное селфи! Если хотите зарегистрироваться, нажмите 'Join Genesis.BitID' в главном меню."
            )


async def start_ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Starts a chat session with the AI assistant according to README.md specs."""
    logger.info(f"AI chat started by user {update.message.from_user.id}")
    context.user_data['ai_chat_enabled'] = True
    reply_markup = ReplyKeyboardMarkup(BACK_KEYBOARD, resize_keyboard=True)
    await update.message.reply_text(
        "Привет! Я - Бадди, я помогаю тебе узнать о BitID и зарегистрирую тебя в Genesis как только получу твое селфи. пришлешь фото сейчас или хочешь узнать больше о проекте?",
        reply_markup=reply_markup,
    )


async def handle_ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles messages when in AI chat mode."""
    logger.info(f"RECEIVED MESSAGE: '{update.message.text}' from user {update.message.from_user.id}")
    
    # Skip processing button clicks to avoid duplication
    button_texts = ["About BitID", "Join Genesis.BitID", "Discuss, ask about BitID.(ai)", "🔙 Back to Main Menu"]
    if update.message.text in button_texts:
        logger.debug(f"Skipping button text: {update.message.text}")
        return
    
    if context.user_data.get('ai_chat_enabled'):
        user_message = update.message.text
        logger.info(f"AI chat message from user {update.message.from_user.id}: {user_message}")
        
        try:
            response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Твоя задача - рассказать пользователю о проекте BitID отвечая на его вопросы. Твоя цель - убедить пользователя зарегистрироваться прислав свое селфи. Ты говоришь по-русски, вежливо и ненавязчиво. BitID - это цифровой идентификатор на основе биометрии лица человека."},
                    {"role": "user", "content": user_message}
                ]
            )
            ai_response = response.choices[0].message.content
            await update.message.reply_text(ai_response)
        except Exception as e:
            logger.error(f"Error calling OpenAI: {e}")
            await update.message.reply_text("Извините, у меня временные проблемы с подключением к ИИ. Попробуйте позже или обратитесь в главное меню.")


async def handle_back_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the back button."""
    logger.info(f"Back button pressed by user {update.message.from_user.id}")
    await start(update, context)


def main() -> None:
    """Start the bot."""
    logger.info("Creating Telegram application...")
    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    # Command handlers
    application.add_handler(CommandHandler("start", start))
    
    # Button handlers (order matters - specific buttons before general text handler!)
    application.add_handler(MessageHandler(filters.Regex("^🔙 Back to Main Menu$"), handle_back_button))
    application.add_handler(MessageHandler(filters.Regex("^About BitID$"), about_bitid))
    application.add_handler(MessageHandler(filters.Regex("^Join Genesis\\.BitID$"), join_genesis))
    application.add_handler(MessageHandler(filters.Regex("^Discuss, ask about BitID\\.\\(ai\\)$"), start_ai_chat))
    
    # Catch-all text handler for debugging
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ai_chat))
    
    # Photo handler
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    logger.info("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()