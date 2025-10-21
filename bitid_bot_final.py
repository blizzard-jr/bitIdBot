#!/usr/bin/env python3
from supabase import create_client
from openai import OpenAI
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton

# Direct config
TELEGRAM_BOT_TOKEN = TELEGRAM_TOKEN
SUPABASE_URL = SUPABASE_URL
SUPABASE_SERVICE_KEY = SUPABASE_SERVICE_KEY
OPENAI_API_KEY = OPENAI_API_KEY

print(f"Starting BitID bot with token: {TELEGRAM_BOT_TOKEN[:20]}...")

# Setup
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Inline Keyboards
MAIN_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("About BitID", callback_data="about")],
    [InlineKeyboardButton("Join Genesis.BitID", callback_data="join")],
    [InlineKeyboardButton("Discuss, ask about BitID.(ai)", callback_data="discuss")],
])

BACK_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back")]
])

# About submenu keyboards
ABOUT_SUBMENU = InlineKeyboardMarkup([
    [InlineKeyboardButton("What is BitID", callback_data="what_is")],
    [InlineKeyboardButton("BitID properties", callback_data="properties")],
    [InlineKeyboardButton("Use cases of BitID", callback_data="use_cases")],
    [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back")]
])

BACK_TO_ABOUT = InlineKeyboardMarkup([
    [InlineKeyboardButton("🔙 Back to About", callback_data="about")]
])

USE_CASES_SUBMENU = InlineKeyboardMarkup([
    [InlineKeyboardButton("Use case: Get Connected", callback_data="uc_connected")],
    [InlineKeyboardButton("Use case: Device-less Access", callback_data="uc_deviceless")],
    [InlineKeyboardButton("Use case: Fraud Prevention", callback_data="uc_fraud")],
    [InlineKeyboardButton("🔙 Back to About", callback_data="about")]
])

BACK_TO_USE_CASES = InlineKeyboardMarkup([
    [InlineKeyboardButton("🔙 Back to Use Cases", callback_data="use_cases")]
])

async def start(update, context):
    print(f"START from user {update.effective_user.id}")
    # Only greet once
    if not context.user_data.get('greeted'):
        greeting = """Welcome to BitID!

I'm Buddy, your guide to the BitID identity network. I'll help you understand how BitID works and register you in Genesis by collecting your selfie.

Please choose an option:"""
        await update.message.reply_text(
            greeting,
            reply_markup=MAIN_KEYBOARD
        )
        context.user_data['greeted'] = True
    else:
        # Just show menu without greeting
        await update.message.reply_text(
            "Choose an option:", 
            reply_markup=MAIN_KEYBOARD
        )
    # Clear only specific states, keep greeted flag
    context.user_data.pop('awaiting_selfie_registration', None)
    context.user_data.pop('awaiting_selfie_replacement', None)
    context.user_data.pop('ai_chat_enabled', None)
    context.user_data.pop('photo_message_id', None)

async def home(update, context):
    """Handle /home command - same as start but never greets."""
    print(f"HOME command from user {update.effective_user.id}")
    await update.message.reply_text(
        "Choose an option:", 
        reply_markup=MAIN_KEYBOARD
    )

async def button_callback(update, context):
    """Handle inline button callbacks."""
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    
    print(f"BUTTON CALLBACK: {data} from user {user_id}")
    
    # Answer the callback to remove loading state
    await query.answer()
    
    if data == "about":
        await query.edit_message_text(
            "About BitID\n\nChoose a topic:",
            reply_markup=ABOUT_SUBMENU
        )
        
    elif data == "what_is":
        what_is_text = """What is BitID

• Network of human participants running permissionless biometric identification protocol software

• Think ID issued by network of people you ever met and exchanged bits of identity information

• This network validates your identity to people you never met that are not part of the network"""
        
        await query.edit_message_text(
            what_is_text,
            reply_markup=BACK_TO_ABOUT
        )
        
    elif data == "properties":
        properties_text = """BitID Properties

• Your face is your public ID

• You can not have more than one BitID

• The only information publicly available is your face and your score

• You build your score by mutually connecting other people in network

• Your personal attributes are ZKP attestations of your personality and relations to other network participants

• You can make personal attributes public or accessible to certain groups of network

• You can ask how far any person from you in the network

• Algorithm defines core network consisting of real humans and edge networks comprised of bots"""
        
        await query.edit_message_text(
            properties_text,
            reply_markup=BACK_TO_ABOUT
        )
        
    elif data == "use_cases":
        await query.edit_message_text(
            "Use Cases of BitID\n\nChoose a use case:",
            reply_markup=USE_CASES_SUBMENU
        )
        
    elif data == "uc_connected":
        uc_connected_text = """Use Case: Get Connected

• There is no easy way to write somebody who did not gave you his identifier on one of centralized platforms

• Why can't I just write to the person I see on stage or on TV?

• BitID is identifier unique to the person and can be used to build permissionless messaging system"""
        
        await query.edit_message_text(
            uc_connected_text,
            reply_markup=BACK_TO_USE_CASES
        )
        
    elif data == "uc_deviceless":
        uc_deviceless_text = """Use Case: Device-less Access

• Venue host issues access permission for your BitID

• You present only your face at venue to get access"""
        
        await query.edit_message_text(
            uc_deviceless_text,
            reply_markup=BACK_TO_USE_CASES
        )
        
    elif data == "uc_fraud":
        uc_fraud_text = """Use Case: Fraud Prevention

• Bad actors can use faceless ID system to manufacture fake identities to exploit trust built online

• In contrast face identification system allows only one identity per person making every participant accountable for their actions

• Which in turn builds trust and reduce economical interaction friction"""
        
        await query.edit_message_text(
            uc_fraud_text,
            reply_markup=BACK_TO_USE_CASES
        )
        
    elif data == "join":
        telegram_id = query.from_user.id
        try:
            # Check if user exists
            response = supabase.table("users").select("id").eq("telegram_id", telegram_id).execute()
            print(f"DB check result: {response}")
            
            if response.data and len(response.data) > 0:
                # User exists - show photo
                try:
                    import time
                    cache_buster = int(time.time())
                    photo_url = supabase.storage.from_("user_selfies").get_public_url(f"{telegram_id}.jpg")
                    photo_url_with_cache_buster = f"{photo_url}?v={cache_buster}"
                    print(f"Photo URL: {photo_url_with_cache_buster}")
                    
                    await query.edit_message_text(
                        "Here is your registration photo:\n\nIf you want to replace it - send a new selfie.",
                        reply_markup=BACK_KEYBOARD
                    )
                    # Send photo separately and save message ID for later deletion
                    photo_message = await context.bot.send_photo(
                        chat_id=query.message.chat_id,
                        photo=photo_url_with_cache_buster
                    )
                    context.user_data['awaiting_selfie_replacement'] = True
                    context.user_data['photo_message_id'] = photo_message.message_id
                    
                except Exception as photo_error:
                    print(f"Photo error: {photo_error}")
                    await query.edit_message_text(
                        "You are registered but photo not found. Send a new selfie.",
                        reply_markup=BACK_KEYBOARD
                    )
                    context.user_data['awaiting_selfie_replacement'] = True
            else:
                # User doesn't exist
                await query.edit_message_text(
                    "You don't have BitID. Send a selfie to get BitID.",
                    reply_markup=BACK_KEYBOARD
                )
                context.user_data['awaiting_selfie_registration'] = True
                
        except Exception as e:
            print(f"DB error: {e}")
            await query.edit_message_text(
                "You don't have BitID. Send a selfie to get BitID.",
                reply_markup=BACK_KEYBOARD
            )
            context.user_data['awaiting_selfie_registration'] = True
            
    elif data == "discuss":
        await query.edit_message_text(
            "Hi! I'm Buddy, I help you learn about BitID and will register you in Genesis as soon as I get your selfie. Will you send a photo now or want to know more about the project?",
            reply_markup=BACK_KEYBOARD
        )
        context.user_data['ai_chat_enabled'] = True
        
    elif data == "back":
        # Delete photo if it exists
        if context.user_data.get('photo_message_id'):
            try:
                await context.bot.delete_message(
                    chat_id=query.message.chat_id,
                    message_id=context.user_data['photo_message_id']
                )
                print(f"Deleted photo message {context.user_data['photo_message_id']}")
            except Exception as e:
                print(f"Could not delete photo message: {e}")
        
        # Return to main menu without greeting
        await query.edit_message_text(
            "Choose an option:",
            reply_markup=MAIN_KEYBOARD
        )
        # Clear states but keep greeted flag
        greeted = context.user_data.get('greeted', False)
        context.user_data.clear()
        context.user_data['greeted'] = greeted

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
                await update.message.reply_text(
                    "Thank you for registration! We will send you BitID as soon as it is generated.",
                    reply_markup=MAIN_KEYBOARD
                )
            else:
                # Photo replacement
                await update.message.reply_text(
                    "Your photo has been updated!",
                    reply_markup=MAIN_KEYBOARD
                )
            
            # Clear registration states but keep greeted
            greeted = context.user_data.get('greeted', True)
            context.user_data.clear()
            context.user_data['greeted'] = greeted
            
        except Exception as e:
            print(f"Photo processing error: {e}")
            await update.message.reply_text(f"Error processing photo: {e}")
    else:
        # Photo sent outside registration - treat as AI chat
        print("Photo sent outside registration - treating as AI question")
        await handle_ai_message(update, context, "What can you tell me about this photo and BitID?")

async def handle_ai_message(update, context, user_message=None):
    """Handle AI chat messages."""
    if not user_message:
        user_message = update.message.text
        
    print(f"AI CHAT: '{user_message}' from user {update.effective_user.id}")
    
    bitid_knowledge = """WHAT IS BitID:
- Network of human participants running permissionless biometric identification protocol software
- Think ID issued by network of people you ever met and exchanged bits of identity information
- This network validates your identity to people you never met that are not part of the network

BitID PROPERTIES:
- Your face is your public ID
- You can not have more than one BitID
- The only information publicly available is your face and your score
- You build your score by mutually connecting other people in network
- Your personal attributes are ZKP attestations of your personality and relations to other network participants
- You can make personal attributes public or accessible to certain groups of network
- You can ask how far any person from you in the network
- Algorithm defines core network consisting of real humans and edge networks comprised of bots

USE CASES:

Get Connected:
- There is no easy way to write somebody who did not gave you his identifier on one of centralized platforms
- Why can't I just write to the person I see on stage or on TV?
- BitID is identifier unique to the person and can be used to build permissionless messaging system

Device-less Access:
- Venue host issues access permission for your BitID
- You present only your face at venue to get access

Fraud Prevention:
- Bad actors can use faceless ID system to manufacture fake identities to exploit trust built online
- In contrast face identification system allows only one identity per person making every participant accountable for their actions
- Which in turn builds trust and reduce economical interaction friction"""

    system_prompt = f"""You are Buddy, an assistant for the BitID project. Your goal is to help users understand BitID and encourage them to register by sending their selfie.

IMPORTANT: You can ONLY answer questions based on the following information about BitID:

{bitid_knowledge}

If a question cannot be answered using ONLY the information above, you MUST respond: "I don't have that information. Please contact the Architect for more details."

You speak English, politely and unobtrusively. Never make up information that is not in the knowledge base above."""
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
        )
        ai_response = response.choices[0].message.content
        await update.message.reply_text(ai_response)
        print(f"AI response sent to user {update.effective_user.id}")
        
    except Exception as e:
        print(f"OpenAI error: {e}")
        await update.message.reply_text(
            "Sorry, I'm having trouble connecting to my AI brain right now. Please try again later or use the menu buttons."
        )

async def text(update, context):
    """Handle all text messages - route to AI by default."""
    print(f"TEXT: '{update.message.text}' from user {update.effective_user.id}")
    
    # Always route text to AI (unless it's a command)
    if not update.message.text.startswith('/'):
        await handle_ai_message(update, context)

# Main
print("Creating application...")
app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

# Handlers
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("home", home))
app.add_handler(CallbackQueryHandler(button_callback))
app.add_handler(MessageHandler(filters.PHOTO, photo))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text))

# Setup bot menu commands
async def setup_bot_commands():
    """Set up bot menu commands."""
    from telegram import BotCommand
    commands = [
        BotCommand("home", "Return to main menu"),
    ]
    await app.bot.set_my_commands(commands)
    print("Bot menu commands configured")

print("Starting bot...")
print("Configuring bot menu...")
import asyncio
asyncio.get_event_loop().run_until_complete(setup_bot_commands())
app.run_polling()
