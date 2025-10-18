import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, 
    ContextTypes, ConversationHandler
)
import pandas as pd
from datetime import datetime, timedelta
import json
import os

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
            
            user_records = self.attendance_df[
                (self.attendance_df['user_id'] == user_id) & 
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
        keyboard = [['/giris', '/cixis']]
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
    
    keyboard = [['/giris', '/cixis']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "🎉 **Qeydiyyat tamamlandı!**\n\n"
        f"**Ad Soyad:** {context.user_data['name']}\n"
        f"**FIN:** {context.user_data['fin']}\n"
        f"**Seriya:** {series}\n\n"
        "⚠️ **Xəbərdarlıq:** Giriş və çıxışı yalnız işə başladığınız məkanda (marketdə) qeyd edin. "
        "Əks halda iş gününüz hesabatda qeyd olunmayacaq.",
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

# /giris command
async def giris(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    
    logger.info(f"İstifadəçi {user_id} giriş etmək istəyir")
    
    if str(user_id) not in bot.users:
        await update.message.reply_text(
            "❌ **Əvvəlcə qeydiyyatdan keçməlisiniz!**\n\n"
            "Qeydiyyat üçün /start yazın."
        )
        return
    
    if bot.has_user_registered_today(user_id, 'giris'):
        await update.message.reply_text(
            "ℹ️ **Bu gün üçün artıq giriş etmisiniz.**\n\n"
            "Növbəti girişi sabah edə bilərsiniz."
        )
        return
    
    # Giriş qeydini əlavə et
    user_data = bot.users[str(user_id)]
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    new_record = {
        'user_id': user_id,
        'name': user_data['name'],
        'fin': user_data['fin'],
        'series': user_data['series'],
        'type': 'giris',
        'datetime': current_time,
        'latitude': None,
        'longitude': None,
        'address': "Manual giriş",
        'code': user_data['code']
    }
    
    bot.attendance_df = pd.concat([bot.attendance_df, pd.DataFrame([new_record])], ignore_index=True)
    bot.save_data()
    
    logger.info(f"İstifadəçi {user_id} giriş etdi: {current_time}")
    
    await update.message.reply_text(
        "✅ **Giriş qeyd edildi!**\n\n"
        f"**Vaxt:** {current_time}\n"
        f"**Ad:** {user_data['name']}\n\n"
        "🌟 **Gününüz uğurlu keçsin!** 🌟"
    )

# /cixis command
async def cixis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    
    logger.info(f"İstifadəçi {user_id} çıxış etmək istəyir")
    
    if str(user_id) not in bot.users:
        await update.message.reply_text(
            "❌ **Əvvəlcə qeydiyyatdan keçməlisiniz!**\n\n"
            "Qeydiyyat üçün /start yazın."
        )
        return
    
    if bot.has_user_registered_today(user_id, 'cixis'):
        await update.message.reply_text(
            "ℹ️ **Bu gün üçün artıq çıxış etmisiniz.**\n\n"
            "Növbəti iş günündə görüşənədək!"
        )
        return
    
    # Çıxış qeydini əlavə et
    user_data = bot.users[str(user_id)]
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    new_record = {
        'user_id': user_id,
        'name': user_data['name'],
        'fin': user_data['fin'],
        'series': user_data['series'],
        'type': 'cixis',
        'datetime': current_time,
        'latitude': None,
        'longitude': None,
        'address': "Manual çıxış",
        'code': user_data['code']
    }
    
    bot.attendance_df = pd.concat([bot.attendance_df, pd.DataFrame([new_record])], ignore_index=True)
    bot.save_data()
    
    logger.info(f"İstifadəçi {user_id} çıxış etdi: {current_time}")
    
    await update.message.reply_text(
        "✅ **Çıxış qeyd edildi!**\n\n"
        f"**Vaxt:** {current_time}\n"
        f"**Ad:** {user_data['name']}\n\n"
        "😴 **Xoş istirahətlər!** 🛌"
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

async def addcode_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not bot.is_admin(user_id):
        await update.message.reply_text("❌ **Bu əmr yalnız admin üçündür.**")
        return
    
    code = datetime.now().strftime('%d%m%y')
    expiry_date = datetime.now().strftime('%Y-%m-%d')
    
    bot.codes[code] = {
        'created_by': user_id,
        'created_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'expiry': expiry_date
    }
    
    bot.save_data()
    
    logger.info(f"Admin {user_id} bugünkü kod əlavə etdi: {code}")
    
    await update.message.reply_text(
        f"✅ **Bugünkü kod uğurla əlavə edildi!**\n\n"
        f"**Kod:** `{code}`\n"
        f"**Bugün:** {expiry_date}\n"
        f"**Format:** GünAyİl (DDMMYY)"
    )

async def removecode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not bot.is_admin(user_id):
        await update.message.reply_text("❌ **Bu əmr yalnız admin üçündür.**")
        return
    
    if not context.args:
        await update.message.reply_text("ℹ️ **İstifadə:** `/removecode <kod>`")
        return
    
    code = context.args[0]
    
    if code in bot.codes:
        del bot.codes[code]
        bot.save_data()
        logger.info(f"Admin {user_id} kodu silindi: {code}")
        await update.message.reply_text(f"✅ **Kod `{code}` uğurla silindi.**")
    else:
        await update.message.reply_text("❌ **Belə bir kod tapılmadı.**")

async def listcodes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not bot.is_admin(user_id):
        await update.message.reply_text("❌ **Bu əmr yalnız admin üçündür.**")
        return
    
    if not bot.codes:
        await update.message.reply_text("ℹ️ **Aktiv kod yoxdur.**")
        return
    
    codes_list = []
    for code, data in bot.codes.items():
        if bot.is_code_valid(code):
            codes_list.append(f"• `{code}` (bitir: {data['expiry']})")
    
    if codes_list:
        await update.message.reply_text(
            "📋 **Aktiv kodlar:**\n\n" + "\n".join(codes_list)
        )
    else:
        await update.message.reply_text("ℹ️ **Aktiv kod yoxdur.**")

async def hesabat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not bot.is_admin(user_id):
        await update.message.reply_text("❌ **Bu əmr yalnız admin üçündür.**")
        return
    
    if len(context.args) != 3:
        await update.message.reply_text("ℹ️ **İstifadə:** `/hesabat <kod> <YYYY-MM-DD> <YYYY-MM-DD>`")
        return
    
    code, start_date, end_date = context.args
    
    try:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    except ValueError:
        await update.message.reply_text("❌ **Tarix formatı yanlışdır!**\nFormat: `YYYY-MM-DD`")
        return
    
    # Filtrlə
    try:
        filtered_df = bot.attendance_df[
            (bot.attendance_df['code'] == code) &
            (pd.to_datetime(bot.attendance_df['datetime']) >= start_dt) &
            (pd.to_datetime(bot.attendance_df['datetime']) <= end_dt)
        ]
        
        if filtered_df.empty:
            await update.message.reply_text(
                f"❌ **Bu parametrlərlə heç bir qeyd tapılmadı.**\n\n"
                f"Kod: `{code}`\n"
                f"Tarix: {start_date} - {end_date}"
            )
            return
        
        # Excel faylı yarat
        filename = f"hesabat_{code}_{start_date}_{end_date}.xlsx"
        filtered_df.to_excel(filename, index=False)
        
        await update.message.reply_document(
            document=open(filename, 'rb'),
            caption=f"📊 **Hesabat:** {code}\n"
                   f"📅 **Tarix:** {start_date} - {end_date}\n"
                   f"📋 **Qeyd sayı:** {len(filtered_df)}"
        )
        
        # Faylı sil
        os.remove(filename)
        logger.info(f"Admin {user_id} hesabat yaratdı: {filename}")
        
    except Exception as e:
        logger.error(f"Hesabat yaradarkən xəta: {e}")
        await update.message.reply_text("❌ **Hesabat yaradarkən xəta baş verdi.**")

async def send_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not bot.is_admin(user_id):
        await update.message.reply_text("❌ **Bu əmr yalnız admin üçündür.**")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text(
            "ℹ️ **İstifadə:**\n"
            "• `/send qrup <qrup_kodu> <mesaj>`\n"
            "• `/send umumi <mesaj>`"
        )
        return
    
    message_type = context.args[0]
    
    if message_type == 'qrup':
        if len(context.args) < 3:
            await update.message.reply_text("ℹ️ **İstifadə:** `/send qrup <qrup_kodu> <mesaj>`")
            return
        
        group_code = context.args[1]
        message = ' '.join(context.args[2:])
        
        # Qrup üzrə istifadəçiləri tap
        group_users = [user_id for user_id, data in bot.users.items() if data.get('code') == group_code]
        
    elif message_type == 'umumi':
        message = ' '.join(context.args[1:])
        group_users = list(bot.users.keys())
    
    else:
        await update.message.reply_text("❌ **Yanlış mesaj tipi!** 'qrup' və ya 'umumi' istifadə edin.")
        return
    
    # Mesajı göndər
    sent_count = 0
    failed_count = 0
    
    for user_id_str in group_users:
        try:
            await context.bot.send_message(
                chat_id=int(user_id_str), 
                text=f"📢 **Admin mesajı:**\n\n{message}"
            )
            sent_count += 1
        except Exception as e:
            logger.error(f"Mesaj {user_id_str} üçün göndərilmədi: {e}")
            failed_count += 1
    
    await update.message.reply_text(
        f"✅ **Mesaj göndərildi!**\n\n"
        f"• Uğurlu: {sent_count}\n"
        f"• Uğursuz: {failed_count}\n"
        f"• Ümumi: {len(group_users)}"
    )

# Kömək əmri
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if bot.is_admin(user_id):
        help_text = (
            "🤖 **İş Qeydiyyat Botu - Admin Kömək**\n\n"
            "**İstifadəçi Əmrləri:**\n"
            "• /start - Qeydiyyat və ya başlama\n"
            "• /giris - Giriş qeyd et\n"
            "• /cixis - Çıxış qeyd et\n\n"
            "**Admin Əmrləri:**\n"
            "• /addcode <kod> - Yeni kod əlavə et\n"
            "• /addcode_today - Bugünkü kod əlavə et\n"
            "• /removecode <kod> - Kodu sil\n"
            "• /listcodes - Aktiv kodları göstər\n"
            "• /hesabat <kod> <başlama> <bitmə> - Hesabat yarat\n"
            "• /send <qrup/umumi> ... - Mesaj göndər\n"
            "• /help - Bu mesajı göstər"
        )
    else:
        help_text = (
            "🤖 **İş Qeydiyyat Botu - Kömək**\n\n"
            "**Əmrlər:**\n"
            "• /start - Qeydiyyat və ya başlama\n"
            "• /giris - Giriş qeyd et\n"
            "• /cixis - Çıxış qeyd et\n"
            "• /help - Bu mesajı göstər\n\n"
            "⚠️ **Qeyd:** Giriş/çıxışları yalnız iş yerində edin!"
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
        application.add_handler(CommandHandler('addcode_today', addcode_today))
        application.add_handler(CommandHandler('removecode', removecode))
        application.add_handler(CommandHandler('listcodes', listcodes))
        application.add_handler(CommandHandler('hesabat', hesabat))
        application.add_handler(CommandHandler('send', send_message))
        application.add_handler(CommandHandler('help', help_command))
        
        logger.info("Bot işə salınır...")
        print("🤖 Bot işə salındı! CTRL+C ilə dayandırın.")
        
        # Botu işə sal
        application.run_polling()
        
    except Exception as e:
        logger.error(f"Bot işə salınarkən xəta: {e}")
        print(f"❌ Xəta: {e}")

if __name__ == '__main__':
    main()