import os
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
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
    
    if not args:
        await context.bot.send_message(chat_id=chat_id, text="Xin chào! Để kết nối nhận cảnh báo khẩn cấp, vui lòng nhập mã kết nối theo cú pháp: /start <CODE>")
        return

    connection_code = args[0].upper()
    
    # Update DB
    async with SessionLocal() as db:
        contact = await crud.update_contact_telegram_id(db, connection_code=connection_code, chat_id=chat_id)
        
    if contact:
        await context.bot.send_message(chat_id=chat_id, text=f"✅ Kết nối thành công với {contact.name}! Bạn sẽ nhận được cảnh báo khi tài xế gặp nguy hiểm.")
    else:
        await context.bot.send_message(chat_id=chat_id, text="❌ Mã kết nối không hợp lệ hoặc không tìm thấy.")

async def send_telegram_alert(chat_id: str, message: str):
    """
    Helper function to send alert message
    """
    try:
        from telegram import Bot
        bot = Bot(token=TELEGRAM_TOKEN)
        await bot.send_message(chat_id=chat_id, text=message)
    except Exception as e:
        print(f"Failed to send Telegram alert: {e}")

async def send_telegram_photo(chat_id: str, photo_data: bytes, caption: str = None):
    """
    Send photo directly to Telegram (no DB storage)
    """
    try:
        from telegram import Bot
        bot = Bot(token=TELEGRAM_TOKEN)
        await bot.send_photo(chat_id=chat_id, photo=photo_data, caption=caption)
    except Exception as e:
        print(f"Failed to send Telegram photo: {e}")

# --- Background Task to Run Bot ---
application = None

async def run_telegram_bot():
    global application
    if not TELEGRAM_TOKEN or "AAG" not in TELEGRAM_TOKEN: # Basic check
        print("Telegram Token not set properly.")
        return

    from telegram.request import HTTPXRequest
    
    # Increase timeout significantly for slow connections
    trequest = HTTPXRequest(connection_pool_size=8, connect_timeout=20.0, read_timeout=20.0)
    
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).request(trequest).build()
    
    start_handler = CommandHandler('start', start)
    application.add_handler(start_handler)
    
    # Run polling
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    print("Telegram Bot Started Polling...")
