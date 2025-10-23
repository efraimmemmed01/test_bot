import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, 
    ContextTypes, ConversationHandler
)
import pandas as pd
from datetime import datetime, timedelta
import json
import os
import io

# Bot konfiqurasiyası
BOT_TOKEN = "7771454463:AAEcaanRr2QzheE39FT_EXR1vBnnXTMXnSQ"

# Verilənlər bazası faylları
USERS_FILE = "users.json"
CODES_FILE = "codes.json"
ATTENDANCE_FILE = "attendance.csv"

# Konversasiya vəziyyətləri
ENTER_CODE, ENTER_NAME, ENTER_FIN, ENTER_SERIES = range(4)

# Admin ID
ADMIN_IDS = [1376245682]

# Logging konfiqurasiyası
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class WorkBot:
    def __init__(self):
        self.load_data()
    
    def load_data(self):
        # İstifadəçilər
        try:
            if os.path.exists(USERS_FILE):
                with open(USERS_FILE, 'r', encoding='utf-8') as f:
                    self.users = json.load(f)
            else:
                self.users = {}
                logger.info("users.json faylı yaradıldı")
        except Exception as e:
            logger.error(f"users.json yüklənərkən xəta: {e}")
            self.users = {}
        
        # Kodlar
        try:
            if os.path.exists(CODES_FILE):
                with open(CODES_FILE, 'r', encoding='utf-8') as f:
                    self.codes = json.load(f)
            else:
                self.codes = {}
                logger.info("codes.json faylı yaradıldı")
        except Exception as e:
            logger.error(f"codes.json yüklənərkən xəta: {e}")
            self.codes = {}
        
        # İş qeydləri
        try:
            if os.path.exists(ATTENDANCE_FILE):
                self.attendance_df = pd.read_csv(ATTENDANCE_FILE)
                logger.info("attendance.csv faylı yükləndi")
            else:
                self.attendance_df = pd.DataFrame(columns=[
                    'user_id', 'name', 'fin', 'series', 'type', 
                    'datetime', 'latitude', 'longitude', 'address', 'code'
                ])
                logger.info("attendance.csv faylı yaradıldı")
        except Exception as e:
            logger.error(f"attendance.csv yüklənərkən xəta: {e}")
            self.attendance_df = pd.DataFrame(columns=[
                'user_id', 'name', 'fin', 'series', 'type', 
                'datetime', 'latitude', 'longitude', 'address', 'code'
            ])
    
    def save_data(self):
        try:
            with open(USERS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.users, f, ensure_ascii=False, indent=2)
            
            with open(CODES_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.codes, f, ensure_ascii=False, indent=2)
            
            self.attendance_df.to_csv(ATTENDANCE_FILE, index=False)
            logger.info("Məlumatlar saxlanıldı")
        except Exception as e:
            logger.error(f"Məlumatlar saxlanarkən xəta: {e}")
    
    def is_admin(self, user_id):
        return user_id in ADMIN_IDS
    
    def is_code_valid(self, code):
        if code in self.codes:
            try:
                expiry_date = datetime.strptime(self.codes[code]['expiry'], '%Y-%m-%d')
                return datetime.now() <= expiry_date
            except Exception as e:
                logger.error(f"Kod yoxlanarkən xəta: {e}")
                return False
        return False
    
    def has_user_registered_today(self, user_id, record_type):
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            if len(self.attendance_df) == 0:
                return False
            
            # Tarixi düzgün formatda yoxla
            user_records = self.attendance_df[
                (self.attendance_df['user_id'].astype(str) == str(user_id)) & 
                (self.attendance_df['datetime'].str.startswith(today)) &
                (self.attendance_df['type'] == record_type)
            ]
            return len(user_records) > 0
        except Exception as e:
            logger.error(f"Qeyd yoxlanarkən xəta: {e}")
            return False

# Bot instance
bot = WorkBot()

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    
    logger.info(f"İstifadəçi {user_id} ({user_name}) /start əmrini işlətdi")
    
    if str(user_id) in bot.users:
        keyboard = [
            [KeyboardButton("📍 Giriş Et", request_location=True)],
            [KeyboardButton("📍 Çıxış Et", request_location=True)]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            f"Xoş gəldiniz, {bot.users[str(user_id)]['name']}! 🙋‍♂️\n\n"
            "Giriş/çıxış etmək üçün aşağıdakı düymələrdən istifadə edin:",
            reply_markup=reply_markup
        )
        return ConversationHandler.END
    else:
        await update.message.reply_text(
            "🤖 **İş Qeydiyyat Botuna Xoş Gəldiniz!**\n\n"
            "Qeydiyyatdan keçmək üçün admin tərəfindən verilən kodu daxil edin:"
        )
        return ENTER_CODE

# Kod yoxlama
async def enter_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text.strip()
    user_id = update.effective_user.id
    
    logger.info(f"İstifadəçi {user_id} kod daxil etdi: {code}")
    
    if bot.is_code_valid(code):
        context.user_data['code'] = code
        await update.message.reply_text(
            "✅ **Kod düzgündür!**\n\n"
            "Ad və soyadınızı daxil edin:\n"
            "*(Nümunə: Kəmalə Məmmədova)*"
        )
        return ENTER_NAME
    else:
        await update.message.reply_text(
            "❌ **Yanlış və ya müddəti bitmiş kod!**\n\n"
            "Zəhmət olmasa düzgün kodu daxil edin:"
        )
        return ENTER_CODE

# Ad qeydiyyatı
async def enter_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text.strip()
    await update.message.reply_text(
        "📋 **FIN nömrənizi** daxil edin:\n"
        "*(Nümunə: 12345678)*"
    )
    return ENTER_FIN

# FIN qeydiyyatı
async def enter_fin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['fin'] = update.message.text.strip().upper()
    await update.message.reply_text(
        "🆔 **Şəxsiyyət vəsiqəsinin seriyasını** daxil edin:\n"
        "*(Nümunə: AZE1234567)*"
    )
    return ENTER_SERIES

# Seriya qeydiyyatı və qeydiyyatın tamamlanması
async def enter_series(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_name = update.effective_user.first_name
    series = update.message.text.strip().upper()
    
    logger.info(f"İstifadəçi {user_id} qeydiyyatı tamamladı: {context.user_data['name']}")
    
    # İstifadəçi məlumatlarını saxla
    bot.users[user_id] = {
        'name': context.user_data['name'],
        'fin': context.user_data['fin'],
        'series': series,
        'code': context.user_data['code'],
        'registration_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    bot.save_data()
    
    keyboard = [
        [KeyboardButton("📍 Giriş Et", request_location=True)],
        [KeyboardButton("📍 Çıxış Et", request_location=True)]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "🎉 **Qeydiyyat tamamlandı!**\n\n"
        f"**Ad Soyad:** {context.user_data['name']}\n"
        f"**FIN:** {context.user_data['fin']}\n"
        f"**Seriya:** {series}\n\n"
        "📍 **İndi giriş/çıxış etmək üçün aşağıdakı düymələrdən istifadə edə bilərsiniz.**\n"
        "⚠️ **Xəbərdarlıq:** Giriş və çıxışı yalnız işə başladığınız məkanda (marketdə) qeyd edin.",
        reply_markup=reply_markup
    )
    
    # Adminə bildir
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=f"🆕 Yeni qeydiyyat:\n"
                     f"👤 {context.user_data['name']}\n"
                     f"🆔 {user_id}\n"
                     f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )
        except Exception as e:
            logger.error(f"Adminə bildiriş göndərilmədi: {e}")
    
    return ConversationHandler.END

# Location handler - giriş/çıxış üçün
async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    location = update.message.location
    user_text = update.message.text if update.message.text else ""
    
    logger.info(f"İstifadəçi {user_id} location göndərdi: {location.latitude}, {location.longitude}")
    
    # Əgər düymə ilə göndərilibsə, text-dən növü müəyyən et
    if "Giriş" in user_text:
        record_type = "giris"
    elif "Çıxış" in user_text:
        record_type = "cixis"
    else:
        # Əgər sadəcə location göndərilibsə, soruş
        keyboard = [
            [KeyboardButton("📍 Giriş Et", request_location=True)],
            [KeyboardButton("📍 Çıxış Et", request_location=True)]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            "📍 **Yeriniz qəbul edildi!**\n\n"
            "Zəhmət olmasa giriş və ya çıxış etdiyinizi seçin:",
            reply_markup=reply_markup
        )
        return
    
    # İstifadəçi yoxlanışı
    if str(user_id) not in bot.users:
        await update.message.reply_text(
            "❌ **Əvvəlcə qeydiyyatdan keçməlisiniz!**\n\n"
            "Qeydiyyat üçün /start yazın."
        )
        return
    
    # Eyni gündə eyni tip qeyd yoxlanışı
    if bot.has_user_registered_today(user_id, record_type):
        action_text = "giriş" if record_type == "giris" else "çıxış"
        await update.message.reply_text(
            f"ℹ️ **Bu gün üçün artıq {action_text} etmisiniz.**"
        )
        return
    
    # Qeydi əlavə et
    user_data = bot.users[str(user_id)]
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Google Maps linki yarat
    maps_link = f"https://maps.google.com/?q={location.latitude},{location.longitude}"
    
    new_record = {
        'user_id': user_id,
        'name': user_data['name'],
        'fin': user_data['fin'],
        'series': user_data['series'],
        'type': record_type,
        'datetime': current_time,
        'latitude': location.latitude,
        'longitude': location.longitude,
        'address': f"📍 Yer: {location.latitude:.6f}, {location.longitude:.6f}",
        'code': user_data['code']
    }
    
    bot.attendance_df = pd.concat([bot.attendance_df, pd.DataFrame([new_record])], ignore_index=True)
    bot.save_data()
    
    logger.info(f"İstifadəçi {user_id} {record_type} etdi: {current_time}")
    
    # Cavab mesajı
    action_text = "Giriş" if record_type == "giris" else "Çıxış"
    emoji = "✅" if record_type == "giris" else "🚪"
    greeting = "🌟 **Gününüz uğurlu keçsin!** 🌟" if record_type == "giris" else "😴 **Xoş istirahətlər!** 🛌"
    
    await update.message.reply_text(
        f"{emoji} **{action_text} qeyd edildi!**\n\n"
        f"**Vaxt:** {current_time}\n"
        f"**Ad:** {user_data['name']}\n"
        f"**Yer:** <a href='{maps_link}'>Xəritədə bax</a>\n"
        f"**Koordinatlar:** {location.latitude:.6f}, {location.longitude:.6f}\n\n"
        f"{greeting}",
        parse_mode='HTML'
    )

# Əl ilə giriş/çıxış əmrləri (location tələb edəcək)
async def giris(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if str(user_id) not in bot.users:
        await update.message.reply_text(
            "❌ **Əvvəlcə qeydiyyatdan keçməlisiniz!**\n\n"
            "Qeydiyyat üçün /start yazın."
        )
        return
    
    if bot.has_user_registered_today(user_id, 'giris'):
        await update.message.reply_text("ℹ️ **Bu gün üçün artıq giriş etmisiniz.**")
        return
    
    keyboard = [[KeyboardButton("📍 Giriş Üçün Yeri Paylaş", request_location=True)]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    await update.message.reply_text(
        "📍 **Giriş etmək üçün yerinizi paylaşın:**\n\n"
        "Zəhmət olmasa aşağıdakı düyməni istifadə edərək iş yerinizdən yerinizi paylaşın.",
        reply_markup=reply_markup
    )

async def cixis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if str(user_id) not in bot.users:
        await update.message.reply_text(
            "❌ **Əvvəlcə qeydiyyatdan keçməlisiniz!**\n\n"
            "Qeydiyyat üçün /start yazın."
        )
        return
    
    if bot.has_user_registered_today(user_id, 'cixis'):
        await update.message.reply_text("ℹ️ **Bu gün üçün artıq çıxış etmisiniz.**")
        return
    
    keyboard = [[KeyboardButton("📍 Çıxış Üçün Yeri Paylaş", request_location=True)]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    await update.message.reply_text(
        "📍 **Çıxış etmək üçün yerinizi paylaşın:**\n\n"
        "Zəhmət olmasa aşağıdakı düyməni istifadə edərək iş yerinizdən yerinizi paylaşın.",
        reply_markup=reply_markup
    )

# Admin əmrləri
async def addcode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not bot.is_admin(user_id):
        await update.message.reply_text("❌ **Bu əmr yalnız admin üçündür.**")
        return
    
    if not context.args:
        await update.message.reply_text("ℹ️ **İstifadə:** `/addcode <kod>`")
        return
    
    code = context.args[0]
    expiry_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
    
    bot.codes[code] = {
        'created_by': user_id,
        'created_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'expiry': expiry_date
    }
    
    bot.save_data()
    
    logger.info(f"Admin {user_id} yeni kod əlavə etdi: {code}")
    
    await update.message.reply_text(
        f"✅ **Kod uğurla əlavə edildi!**\n\n"
        f"**Kod:** `{code}`\n"
        f"**Bitmə tarixi:** {expiry_date}\n"
        f"**Qalıq gün:** 30 gün"
    )

async def gunluk_hesabat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not bot.is_admin(user_id):
        await update.message.reply_text("❌ **Bu əmr yalnız admin üçündür.**")
        return
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    try:
        # Bugünkü qeydləri filtrlə
        today_df = bot.attendance_df[
            bot.attendance_df['datetime'].str.startswith(today)
        ]
        
        if today_df.empty:
            await update.message.reply_text(f"📊 **{today} üçün heç bir qeyd yoxdur.**")
            return
        
        # Excel faylı yarat
        filename = f"hesabat_{today}.xlsx"
        today_df.to_excel(filename, index=False)
        
        # Mesaj hazırla
        total_records = len(today_df)
        giris_sayi = len(today_df[today_df['type'] == 'giris'])
        cixis_sayi = len(today_df[today_df['type'] == 'cixis'])
        
        await update.message.reply_document(
            document=open(filename, 'rb'),
            caption=f"📊 **Günlük Hesabat**\n"
                   f"📅 **Tarix:** {today}\n"
                   f"👥 **Ümumi qeyd:** {total_records}\n"
                   f"✅ **Giriş sayı:** {giris_sayi}\n"
                   f"🚪 **Çıxış sayı:** {cixis_sayi}"
        )
        
        # Faylı sil
        os.remove(filename)
        logger.info(f"Admin {user_id} günlük hesabat yaratdı: {filename}")
        
    except Exception as e:
        logger.error(f"Hesabat yaradarkən xəta: {e}")
        await update.message.reply_text("❌ **Hesabat yaradarkən xəta baş verdi.**")

async def tam_hesabat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not bot.is_admin(user_id):
        await update.message.reply_text("❌ **Bu əmr yalnız admin üçündür.**")
        return
    
    try:
        if bot.attendance_df.empty:
            await update.message.reply_text("📊 **Heç bir qeyd yoxdur.**")
            return
        
        # Excel faylı yarat
        filename = "tam_hesabat.xlsx"
        bot.attendance_df.to_excel(filename, index=False)
        
        # Statistikalar
        total_records = len(bot.attendance_df)
        giris_sayi = len(bot.attendance_df[bot.attendance_df['type'] == 'giris'])
        cixis_sayi = len(bot.attendance_df[bot.attendance_df['type'] == 'cixis'])
        unique_users = bot.attendance_df['user_id'].nunique()
        
        await update.message.reply_document(
            document=open(filename, 'rb'),
            caption=f"📊 **Tam İş Hesabatı**\n"
                   f"📋 **Ümumi qeyd:** {total_records}\n"
                   f"👥 **İstifadəçi sayı:** {unique_users}\n"
                   f"✅ **Giriş sayı:** {giris_sayi}\n"
                   f"🚪 **Çıxış sayı:** {cixis_sayi}\n"
                   f"📅 **Son qeyd:** {bot.attendance_df['datetime'].max()}"
        )
        
        # Faylı sil
        os.remove(filename)
        logger.info(f"Admin {user_id} tam hesabat yaratdı: {filename}")
        
    except Exception as e:
        logger.error(f"Tam hesabat yaradarkən xəta: {e}")
        await update.message.reply_text("❌ **Hesabat yaradarkən xəta baş verdi.**")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if bot.is_admin(user_id):
        help_text = (
            "🤖 **İş Qeydiyyat Botu - Admin Kömək**\n\n"
            "**İstifadəçi Əmrləri:**\n"
            "• /start - Qeydiyyat və ya başlama\n"
            "• '📍 Giriş Et' düyməsi - Giriş qeyd et\n"
            "• '📍 Çıxış Et' düyməsi - Çıxış qeyd et\n\n"
            "**Admin Əmrləri:**\n"
            "• /addcode <kod> - Yeni kod əlavə et\n"
            "• /gunluk_hesabat - Bugünkü hesabat\n"
            "• /tam_hesabat - Tam hesabat\n"
            "• /help - Bu mesajı göstər\n\n"
            "📍 **Qeyd:** Bütün giriş/çıxışlarda yer tələb olunur!"
        )
    else:
        help_text = (
            "🤖 **İş Qeydiyyat Botu - Kömək**\n\n"
            "**Əmrlər:**\n"
            "• /start - Qeydiyyat və ya başlama\n"
            "• '📍 Giriş Et' düyməsi - Giriş qeyd et\n"
            "• '📍 Çıxış Et' düyməsi - Çıxış qeyd et\n"
            "• /help - Bu mesajı göstər\n\n"
            "📍 **Qeyd:** Giriş/çıxışları yalnız iş yerində edin!\n"
            "📱 **Yerinizi paylaşmaq üçün düymələrdən istifadə edin.**"
        )
    
    await update.message.reply_text(help_text)

# Əsas funksiya
def main():
    try:
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Konversasiya handler (qeydiyyat üçün)
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
        
        # Digər əmrlər
        application.add_handler(CommandHandler('giris', giris))
        application.add_handler(CommandHandler('cixis', cixis))
        application.add_handler(CommandHandler('addcode', addcode))
        application.add_handler(CommandHandler('gunluk_hesabat', gunluk_hesabat))
        application.add_handler(CommandHandler('tam_hesabat', tam_hesabat))
        application.add_handler(CommandHandler('help', help_command))
        
        # Location handler
        application.add_handler(MessageHandler(filters.LOCATION, handle_location))
        
        logger.info("Bot işə salınır...")
        print("🤖 Bot işə salındı! CTRL+C ilə dayandırın.")
        
        # Botu işə sal
        application.run_polling()
        
    except Exception as e:
        logger.error(f"Bot işə salınarkən xəta: {e}")
        print(f"❌ Xəta: {e}")

if __name__ == '__main__':
    main()
