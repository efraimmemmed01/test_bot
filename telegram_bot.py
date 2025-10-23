import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, 
    ContextTypes, ConversationHandler
)
from datetime import datetime, timedelta
import json
import os
import csv

# Bot token
BOT_TOKEN = "7771454463:AAEcaanRr2QzheE39FT_EXR1vBnnXTMXnSQ"

# Fayl yolları
USERS_FILE = "/tmp/users.json"
CODES_FILE = "/tmp/codes.json"
ATTENDANCE_FILE = "/tmp/attendance.csv"

# Konversasiya vəziyyətləri
ENTER_CODE, ENTER_NAME, ENTER_FIN, ENTER_SERIES = range(4)

# Admin ID
ADMIN_IDS = [1376245682]

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class WorkBot:
    def __init__(self):
        self.users = {}
        self.codes = {}
        self.attendance = []
        self.load_data()
    
    def load_data(self):
        try:
            # Users
            if os.path.exists(USERS_FILE):
                with open(USERS_FILE, 'r', encoding='utf-8') as f:
                    self.users = json.load(f)
            
            # Codes
            if os.path.exists(CODES_FILE):
                with open(CODES_FILE, 'r', encoding='utf-8') as f:
                    self.codes = json.load(f)
            
            # Attendance
            if os.path.exists(ATTENDANCE_FILE):
                with open(ATTENDANCE_FILE, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    self.attendance = list(reader)
                    
        except Exception as e:
            logger.error(f"Yükləmə xətası: {e}")
            self.users = {}
            self.codes = {}
            self.attendance = []
    
    def save_data(self):
        try:
            with open(USERS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.users, f, ensure_ascii=False, indent=2)
            
            with open(CODES_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.codes, f, ensure_ascii=False, indent=2)
            
            # CSV faylını yaz
            if self.attendance:
                with open(ATTENDANCE_FILE, 'w', encoding='utf-8', newline='') as f:
                    fieldnames = ['user_id', 'name', 'fin', 'series', 'type', 'datetime', 'code']
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(self.attendance)
                    
        except Exception as e:
            logger.error(f"Saxlama xətası: {e}")
    
    def is_admin(self, user_id):
        return user_id in ADMIN_IDS
    
    def is_code_valid(self, code):
        if code in self.codes:
            try:
                expiry_date = datetime.strptime(self.codes[code]['expiry'], '%Y-%m-%d')
                return datetime.now() <= expiry_date
            except:
                return False
        return False
    
    def has_user_registered_today(self, user_id, record_type):
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            for record in self.attendance:
                if (str(record['user_id']) == str(user_id) and 
                    record['datetime'].startswith(today) and 
                    record['type'] == record_type):
                    return True
            return False
        except:
            return False

# Bot instance
bot = WorkBot()

# Əmrlər (qısaldılmış versiya)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if str(user_id) in bot.users:
        keyboard = [['/giris', '/cixis']]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            f"Xoş gəldiniz, {bot.users[str(user_id)]['name']}!",
            reply_markup=reply_markup
        )
        return ConversationHandler.END
    else:
        await update.message.reply_text("Qeydiyyat üçün kodu daxil edin:")
        return ENTER_CODE

async def enter_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text.strip()
    if bot.is_code_valid(code):
        context.user_data['code'] = code
        await update.message.reply_text("✅ Kod düzgündür! Adınızı daxil edin:")
        return ENTER_NAME
    else:
        await update.message.reply_text("❌ Yanlış kod! Yenidən daxil edin:")
        return ENTER_CODE

async def enter_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text.strip()
    await update.message.reply_text("FIN nömrənizi daxil edin:")
    return ENTER_FIN

async def enter_fin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['fin'] = update.message.text.strip().upper()
    await update.message.reply_text("Şəxsiyyət vəsiqəsi seriyasını daxil edin:")
    return ENTER_SERIES

async def enter_series(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    series = update.message.text.strip().upper()
    
    bot.users[user_id] = {
        'name': context.user_data['name'],
        'fin': context.user_data['fin'],
        'series': series,
        'code': context.user_data['code'],
        'registration_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    bot.save_data()
    
    keyboard = [['/giris', '/cixis']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        f"🎉 Qeydiyyat tamamlandı!\nAd: {context.user_data['name']}",
        reply_markup=reply_markup
    )
    return ConversationHandler.END

async def giris(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if str(user_id) not in bot.users:
        await update.message.reply_text("❌ Əvvəlcə qeydiyyatdan keçin: /start")
        return
    
    if bot.has_user_registered_today(user_id, 'giris'):
        await update.message.reply_text("ℹ️ Bu gün üçün artıq giriş etmisiniz.")
        return
    
    user_data = bot.users[str(user_id)]
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    new_record = {
        'user_id': user_id,
        'name': user_data['name'],
        'fin': user_data['fin'],
        'series': user_data['series'],
        'type': 'giris',
        'datetime': current_time,
        'code': user_data['code']
    }
    
    bot.attendance.append(new_record)
    bot.save_data()
    
    await update.message.reply_text(f"✅ Giriş qeyd edildi: {current_time}")

async def cixis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if str(user_id) not in bot.users:
        await update.message.reply_text("❌ Əvvəlcə qeydiyyatdan keçin: /start")
        return
    
    if bot.has_user_registered_today(user_id, 'cixis'):
        await update.message.reply_text("ℹ️ Bu gün üçün artıq çıxış etmisiniz.")
        return
    
    user_data = bot.users[str(user_id)]
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    new_record = {
        'user_id': user_id,
        'name': user_data['name'],
        'fin': user_data['fin'],
        'series': user_data['series'],
        'type': 'cixis',
        'datetime': current_time,
        'code': user_data['code']
    }
    
    bot.attendance.append(new_record)
    bot.save_data()
    
    await update.message.reply_text(f"✅ Çıxış qeyd edildi: {current_time}")

async def addcode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not bot.is_admin(user_id):
        await update.message.reply_text("❌ Bu əmr yalnız admin üçündür.")
        return
    
    if not context.args:
        await update.message.reply_text("ℹ️ İstifadə: /addcode <kod>")
        return
    
    code = context.args[0]
    expiry_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
    
    bot.codes[code] = {
        'created_by': user_id,
        'created_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'expiry': expiry_date
    }
    
    bot.save_data()
    await update.message.reply_text(f"✅ Kod əlavə edildi: {code}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Bot Əmrləri:\n/start - Qeydiyyat\n/giris - Giriş\n/cixis - Çıxış\n/help - Kömək"
    )

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            ENTER_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_code)],
            ENTER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_name)],
            ENTER_FIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_fin)],
            ENTER_SERIES: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_series)],
        },
        fallbacks=[]
    )
    
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('giris', giris))
    application.add_handler(CommandHandler('cixis', cixis))
    application.add_handler(CommandHandler('addcode', addcode))
    application.add_handler(CommandHandler('help', help_command))
    
    logger.info("🤖 Bot işə salınır...")
    application.run_polling()

if __name__ == '__main__':
    main()
