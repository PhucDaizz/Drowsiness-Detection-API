import os
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from database import SessionLocal
import crud

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /start command.
    Format: /start <CONNECTION_CODE>
    """
    args = context.args
    chat_id = str(update.effective_chat.id)
    print(f"DEBUG: Received /start from {chat_id} with args: {args}")
    
    try:
        if not args:
            await context.bot.send_message(
                chat_id=chat_id, 
                text="👋 Xin chào! Đây là Bot cảnh báo buồn ngủ GatGu.\n\n"
                     "Để kết nối, vui lòng nhập mã code theo cú pháp:\n"
                     "👉 `/start <MÃ_CODE>`\n\n"
                     "(Ví dụ: /start ABC123)",
                parse_mode='Markdown'
            )
            return

        connection_code = args[0].upper()
        contact_name = None
        
        # Update DB
        print(f"DEBUG: Connecting to DB to link code {connection_code} for chat_id {chat_id}...")
        async with SessionLocal() as db:
            contact = await crud.update_contact_telegram_id(db, connection_code=connection_code, chat_id=chat_id)
            if contact:
                contact_name = contact.name
            
        if contact_name:
            print(f"DEBUG: Success. Linked to {contact_name}")
            await context.bot.send_message(chat_id=chat_id, text=f"✅ Kết nối thành công với {contact_name}! Bạn sẽ nhận được cảnh báo khi tài xế gặp nguy hiểm.")
        else:
            print("DEBUG: Failed. Code not found.")
            await context.bot.send_message(chat_id=chat_id, text="❌ Mã kết nối không hợp lệ hoặc không tìm thấy.")
            
    except Exception as e:
        print(f"ERROR in /start handler: {e}")
        import traceback
        traceback.print_exc()
        await context.bot.send_message(chat_id=chat_id, text="⚠ Đã xảy ra lỗi hệ thống. Vui lòng thử lại sau.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reply to unknown messages with help instructions"""
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="🤖 Tôi không hiểu tin nhắn này.\n\n"
             "Vui lòng sử dụng các lệnh sau:\n"
             "▶️ `/start <CODE>`: Kết nối nhận cảnh báo\n"
             "⏹️ `/stop`: Hủy kết nối\n",
        parse_mode='Markdown'
    )

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /stop command.
    Unlink chat_id from emergency contact.
    """
    chat_id = str(update.effective_chat.id)
    contact_name = None
    
    async with SessionLocal() as db:
        contact, code = await crud.remove_contact_telegram_id(db, chat_id=chat_id)
        if contact:
            contact_name = contact.name
        
    if contact_name:
        await context.bot.send_message(
            chat_id=chat_id, 
            text=f"🔕 Đã hủy nhận cảnh báo cho {contact_name}.\n\nNếu muốn kết nối lại, hãy nhập:\n/start {code}"
        )
    else:
        await context.bot.send_message(chat_id=chat_id, text="Bạn chưa kết nối với tài khoản nào.")

async def send_telegram_alert(chat_id: str, message: str):
    """
    Helper function to send alert message
    """
    try:
        from telegram import Bot
        bot = Bot(token=TELEGRAM_TOKEN)
        await bot.send_message(chat_id=chat_id, text=message, parse_mode='HTML')
    except Exception as e:
        print(f"Failed to send Telegram alert: {e}")

async def send_telegram_photo(chat_id: str, photo_data: bytes, caption: str = None):
    """
    Send photo directly to Telegram (no DB storage)
    """
    try:
        from telegram import Bot
        bot = Bot(token=TELEGRAM_TOKEN)
        await bot.send_photo(chat_id=chat_id, photo=photo_data, caption=caption, parse_mode='HTML')
    except Exception as e:
        print(f"Failed to send Telegram photo: {e}")

# --- Background Task to Run Bot ---
application = None

async def run_telegram_bot():
    global application
    if not TELEGRAM_TOKEN: 
        print("Telegram Token not set properly.")
        return

    from telegram.request import HTTPXRequest
    
    # Increase timeout significantly for slow connections
    trequest = HTTPXRequest(connection_pool_size=8, connect_timeout=60.0, read_timeout=60.0)
    
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).request(trequest).build()
    
    start_handler = CommandHandler('start', start)
    stop_handler = CommandHandler('stop', stop)
    unknown_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)

    application.add_handler(start_handler)
    application.add_handler(stop_handler)
    application.add_handler(unknown_handler)
    
    # Run polling
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    print("Telegram Bot Started Polling...")
