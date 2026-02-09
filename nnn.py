#!/usr/bin/env python3
"""
Telegram Stars Bot - Полностью рабочий с уведомлениями
Пользователь: оплачивает → нажимает "Я оплатил" → админ проверяет → подтверждает
"""

import os
import logging
import sqlite3
from datetime import datetime

try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
    print("✅ Библиотеки загружены успешно")
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("Установите: pip install python-telegram-bot==20.7")
    exit()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== КОНФИГУРАЦИЯ ====================
BOT_TOKEN = "8196751032:AAGwizPBRuq_uh0zd9GQ6C2BFiseAfnp_xo"
ADMIN_ID = 741906407
SUPPORT_USERNAME = "@ir1sum"

# Цены
STAR_PRICE = 1.6
MIN_STARS = 50
MAX_STARS = 5000

# Цены на Premium
PREMIUM_PRICES = {
    '3': {"месяца": 3, "цена": 1099},
    '6': {"месяца": 6, "цена": 1399},
    '12': {"месяца": 12, "цена": 2499}
}

# База данных
DB_PATH = "bot_database.db"

# ==================== СПОСОБЫ ОПЛАТЫ ====================
PAYMENT_METHODS = {
    'card_ru': {
        'name': '💳 Карта РФ',
        'details': '2202206713916687\nПолучатель: ROMAN IVANOV',
        'instructions': 'Оплатите указанную сумму на карту',
        'enabled': True
    },
    'usdt_trc20': {
        'name': '🌐 USDT (TRC20)',
        'details': 'TT6QmsrMhctAabpY9Cy5eSV3L1myxNeUwF\nСеть: TRC20 (Tron)',
        'instructions': 'Переведите USDT на указанный адрес',
        'enabled': True
    },
    'bitcoin': {
        'name': '₿ Bitcoin',
        'details': 'bc1qy9860j3zxjd3wpy6pj5tu7jpqkz84tzftq076p\nСеть: Bitcoin (SegWit)',
        'instructions': 'Переведите Bitcoin на указанный адрес',
        'enabled': True
    },
    'ton': {
        'name': '⚡ TON',
        'details': 'UQA2Xxf6CL2lx2XpiDvPPHr3heCJ5o6nRNBbxytj9eFVTpXx\nСеть: TON',
        'instructions': 'Переведите TON на указанный адрес',
        'enabled': True
    },
}

# ==================== БАЗА ДАННЫХ ====================
def init_database():
    """Инициализация базы данных"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        registration_date TIMESTAMP,
        total_spent REAL DEFAULT 0,
        total_stars INTEGER DEFAULT 0
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS orders (
        order_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        product_type TEXT,
        amount INTEGER,
        price REAL,
        total REAL,
        payment_method TEXT,
        status TEXT DEFAULT 'создан',
        created_at TIMESTAMP,
        paid_at TIMESTAMP,
        user_paid INTEGER DEFAULT 0,
        admin_confirmed INTEGER DEFAULT 0
    )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("База данных инициализирована")

def get_pending_confirmations():
    """Получить заказы, где пользователь нажал "Я оплатил", но админ еще не проверил"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
    SELECT o.order_id, o.user_id, u.username, u.first_name, 
           o.product_type, o.amount, o.total, o.payment_method, o.created_at
    FROM orders o
    LEFT JOIN users u ON o.user_id = u.user_id
    WHERE o.user_paid = 1 AND o.admin_confirmed = 0 AND o.status != 'отменен'
    ORDER BY o.created_at DESC
    ''')
    orders = cursor.fetchall()
    conn.close()
    return orders

def update_user_paid(order_id):
    """Пользователь нажал "Я оплатил" """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
    UPDATE orders 
    SET user_paid = 1, status = 'ожидает проверки'
    WHERE order_id = ?
    ''', (order_id,))
    conn.commit()
    conn.close()
    return True

def update_admin_confirmed(order_id):
    """Админ подтвердил оплату"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
    UPDATE orders 
    SET admin_confirmed = 1, status = 'оплачен', paid_at = ?
    WHERE order_id = ?
    ''', (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), order_id))
    conn.commit()
    conn.close()
    return True

def update_admin_rejected(order_id):
    """Админ отклонил оплату (не пришли деньги)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
    UPDATE orders 
    SET user_paid = 0, admin_confirmed = 0, status = 'оплата не найдена'
    WHERE order_id = ?
    ''', (order_id,))
    conn.commit()
    conn.close()
    return True

def get_order_details(order_id):
    """Получить детали заказа"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
    SELECT o.order_id, o.user_id, u.username, u.first_name, 
           o.product_type, o.amount, o.total, o.payment_method, 
           o.status, o.created_at, o.user_paid, o.admin_confirmed
    FROM orders o
    LEFT JOIN users u ON o.user_id = u.user_id
    WHERE o.order_id = ?
    ''', (order_id,))
    order = cursor.fetchone()
    conn.close()
    return order

# ==================== КЛАВИАТУРЫ ====================
def main_menu():
    """Главное меню"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⭐ Купить звезды", callback_data="buy_stars")],
        [InlineKeyboardButton("👑 Купить Premium", callback_data="buy_premium")],
        [InlineKeyboardButton("📊 Мой профиль", callback_data="profile")],
        [InlineKeyboardButton("📦 Мои заказы", callback_data="my_orders")],
    ])

def premium_menu():
    """Меню выбора Premium тарифа"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("3 месяца - 1099₽", callback_data="premium_3")],
        [InlineKeyboardButton("6 месяцев - 1399₽", callback_data="premium_6")],
        [InlineKeyboardButton("12 месяцев - 2499₽", callback_data="premium_12")],
        [InlineKeyboardButton("🔙 Назад", callback_data="main")]
    ])

def payment_methods_keyboard():
    """Клавиатура с выбором способа оплаты"""
    buttons = []
    
    # Первый ряд
    row1 = []
    if 'card_ru' in PAYMENT_METHODS and PAYMENT_METHODS['card_ru'].get('enabled', True):
        row1.append(InlineKeyboardButton("💳 Карта РФ", callback_data="pay_card_ru"))
    if 'usdt_trc20' in PAYMENT_METHODS and PAYMENT_METHODS['usdt_trc20'].get('enabled', True):
        row1.append(InlineKeyboardButton("🌐 USDT", callback_data="pay_usdt_trc20"))
    if row1:
        buttons.append(row1)
    
    # Второй ряд
    row2 = []
    if 'bitcoin' in PAYMENT_METHODS and PAYMENT_METHODS['bitcoin'].get('enabled', True):
        row2.append(InlineKeyboardButton("₿ Bitcoin", callback_data="pay_bitcoin"))
    if 'ton' in PAYMENT_METHODS and PAYMENT_METHODS['ton'].get('enabled', True):
        row2.append(InlineKeyboardButton("⚡ TON", callback_data="pay_ton"))
    if row2:
        buttons.append(row2)
    
    # Кнопка назад
    buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="main")])
    
    return InlineKeyboardMarkup(buttons)

def back_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="main")]])

def user_paid_keyboard(order_id):
    """Клавиатура для пользователя после получения реквизитов"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Я ОПЛАТИЛ", callback_data=f"user_paid_{order_id}")],
        [InlineKeyboardButton("💬 Поддержка", url=f"https://t.me/{SUPPORT_USERNAME.replace('@', '')}")],
        [InlineKeyboardButton("📦 Мои заказы", callback_data="my_orders")]
    ])

def admin_confirmation_keyboard(order_id):
    """Клавиатура для админа, когда пользователь нажал "Я оплатил" """
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Деньги пришли", callback_data=f"admin_confirm_{order_id}")],
        [InlineKeyboardButton("❌ Денег нет", callback_data=f"admin_reject_{order_id}")],
        [InlineKeyboardButton("📋 Все заявки", callback_data="admin_orders")]
    ])

def admin_main_keyboard():
    """Главное меню админа"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Проверить оплаты", callback_data="admin_orders")],
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("👥 Пользователи", callback_data="admin_users")],
        [InlineKeyboardButton("🔙 Главное меню", callback_data="main")]
    ])

# ==================== ОСНОВНЫЕ ФУНКЦИИ ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    try:
        user = update.effective_user
        logger.info(f"Пользователь {user.id} запустил бота")
        
        # Регистрируем пользователя
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
        INSERT OR IGNORE INTO users (user_id, username, first_name, registration_date)
        VALUES (?, ?, ?, ?)
        ''', (user.id, user.username, user.first_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
        
        text = f"👋 Привет, {user.first_name or 'друг'}!\n\n"
        text += "Я бот для покупки Telegram Stars ⭐ и Premium 👑\n\n"
        text += "Выберите действие:"
        
        # Если админ - показываем админ-меню
        if user.id == ADMIN_ID:
            text += "\n\n👑 Вы вошли как администратор"
            await update.message.reply_text(text, reply_markup=admin_main_keyboard())
        else:
            await update.message.reply_text(text, reply_markup=main_menu())
        
        logger.info("Команда /start выполнена")
        
    except Exception as e:
        logger.error(f"Ошибка в /start: {e}")
        await update.message.reply_text("Ошибка. Попробуйте позже.")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик callback-запросов"""
    try:
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user = query.from_user
        
        logger.info(f"Callback от {user.id}: {data}")
        
        # Главное меню
        if data == "main":
            await query.edit_message_text("Главное меню:", reply_markup=main_menu())
        
        # Купить звезды
        elif data == "buy_stars":
            text = f"⭐ Купить звезды\n\nЦена: {STAR_PRICE}₽ за 1 звезду\n\nВведите количество от {MIN_STARS} до {MAX_STARS}:"
            await query.edit_message_text(text, reply_markup=back_button())
            context.user_data['waiting_amount'] = True
            context.user_data['product'] = 'stars'
        
        # Купить Premium
        elif data == "buy_premium":
            text = "👑 Telegram Premium\n\nВыберите срок подпики:"
            await query.edit_message_text(text, reply_markup=premium_menu())
        
        # Выбор тарифа Premium
        elif data.startswith("premium_"):
            months = data.replace("premium_", "")
            premium_data = PREMIUM_PRICES.get(months)
            
            if premium_data:
                context.user_data['order_data'] = {
                    'product': 'premium',
                    'description': f"Premium на {premium_data['месяца']} месяцев",
                    'amount': 1,
                    'total': premium_data['цена']
                }
                
                text = f"👑 Premium на {premium_data['месяца']} месяцев\n💰 Сумма: {premium_data['цена']}₽\n\nВыберите способ оплаты:"
                await query.edit_message_text(text, reply_markup=payment_methods_keyboard())
        
        # Профиль
        elif data == "profile":
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('SELECT total_spent, total_stars FROM users WHERE user_id = ?', (user.id,))
            result = cursor.fetchone()
            conn.close()
            
            total_spent = result[0] if result else 0
            total_stars = result[1] if result else 0
            
            text = f"📊 Ваш профиль\n\n"
            text += f"🆔 ID: {user.id}\n"
            text += f"👤 Имя: {user.first_name or 'Не указано'}\n"
            text += f"📛 Юзернейм: @{user.username or 'отсутствует'}\n"
            text += f"⭐ Всего звезд куплено: {total_stars}\n"
            text += f"💰 Всего потрачено: {total_spent:.2f}₽"
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📦 Мои заказы", callback_data="my_orders")],
                [InlineKeyboardButton("🔙 Назад", callback_data="main")]
            ])
            
            await query.edit_message_text(text, reply_markup=keyboard)
        
        # Мои заказы
        elif data == "my_orders":
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''
            SELECT order_id, product_type, amount, total, status, created_at 
            FROM orders WHERE user_id = ? 
            ORDER BY created_at DESC 
            LIMIT 10
            ''', (user.id,))
            
            orders = cursor.fetchall()
            conn.close()
            
            if orders:
                text = "📦 Ваши последние заказы:\n\n"
                for order in orders:
                    order_id, product_type, amount, total, status, created_at = order
                    if status == 'оплачен':
                        status_emoji = "✅"
                    elif status == 'ожидает проверки':
                        status_emoji = "🔄"
                    elif status == 'оплата не найдена':
                        status_emoji = "❌"
                    else:
                        status_emoji = "⏳"
                    
                    product_emoji = "⭐" if product_type == "stars" else "👑"
                    text += f"{status_emoji} {product_emoji} Заказ #{order_id}\n"
                    text += f"   {product_type.capitalize()}: {amount} шт\n"
                    text += f"   💰 {total:.2f}₽\n"
                    text += f"   📊 Статус: {status}\n"
                    text += f"   📅 {created_at[:16]}\n\n"
            else:
                text = "📦 У вас пока нет заказов"
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("⭐ Купить звезды", callback_data="buy_stars")],
                [InlineKeyboardButton("🔙 Назад", callback_data="main")]
            ])
            
            await query.edit_message_text(text, reply_markup=keyboard)
        
        # ПОЛЬЗОВАТЕЛЬ нажал "Я ОПЛАТИЛ"
        elif data.startswith("user_paid_"):
            order_id = data.replace("user_paid_", "")
            order_details = get_order_details(order_id)
            
            if order_details:
                order_id, user_id, username, first_name, product_type, amount, total, payment_method, status, created_at, user_paid, admin_confirmed = order_details
                
                # Проверяем, что это действительно заказ этого пользователя
                if user.id != user_id:
                    await query.edit_message_text("❌ Это не ваш заказ", reply_markup=main_menu())
                    return
                
                # Обновляем статус - пользователь нажал "Я оплатил"
                update_user_paid(order_id)
                
                # 🔔 УВЕДОМЛЕНИЕ АДМИНУ: ПОЛЬЗОВАТЕЛЬ НАЖАЛ "Я ОПЛАТИЛ"
                try:
                    admin_message = (
                        f"🔄 ПОЛЬЗОВАТЕЛЬ НАЖАЛ 'Я ОПЛАТИЛ'\n\n"
                        f"🆔 Заказ #{order_id}\n"
                        f"👤 Пользователь: {first_name or 'Без имени'}\n"
                        f"📛 @{username or 'нет'}\n"
                        f"🆔 ID: {user_id}\n"
                        f"📦 Товар: {product_type} ({amount} шт)\n"
                        f"💰 Сумма: {total:.2f}₽\n"
                        f"💳 Способ: {payment_method}\n"
                        f"📅 Время оплаты: {datetime.now().strftime('%H:%M:%S')}\n\n"
                        f"⚠️ Проверьте поступление денег!"
                    )
                    
                    await query.bot.send_message(
                        ADMIN_ID,
                        admin_message,
                        reply_markup=admin_confirmation_keyboard(order_id)
                    )
                except Exception as e:
                    logger.error(f"Ошибка уведомления админу: {e}")
                
                # Сообщаем пользователю
                user_text = (
                    f"🔄 Заявка отправлена!\n\n"
                    f"📦 Заказ #{order_id}\n"
                    f"💰 Сумма: {total:.2f}₽\n"
                    f"💳 Способ: {payment_method}\n\n"
                    f"✅ Мы получили ваше уведомление об оплате\n"
                    f"⏳ Ожидайте подтверждения от администратора\n"
                    f"📞 Обычно проверка занимает 5-15 минут"
                )
                
                await query.edit_message_text(
                    user_text,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📦 Мои заказы", callback_data="my_orders")],
                        [InlineKeyboardButton("💬 Поддержка", url=f"https://t.me/{SUPPORT_USERNAME.replace('@', '')}")]
                    ])
                )
            else:
                await query.edit_message_text("❌ Заказ не найден", reply_markup=main_menu())
        
        # АДМИН: Список заявок на проверку
        elif data == "admin_orders":
            if user.id != ADMIN_ID:
                await query.edit_message_text("⛔ Доступ запрещен", reply_markup=main_menu())
                return
            
            orders = get_pending_confirmations()
            
            if orders:
                text = "📋 ЗАЯВКИ НА ПРОВЕРКУ:\n\n"
                for order in orders:
                    order_id, user_id, username, first_name, product_type, amount, total, payment_method, created_at = order
                    text += f"🆔 Заказ #{order_id}\n"
                    text += f"👤 Пользователь: {first_name or 'Без имени'} (@{username or 'нет'})\n"
                    text += f"📦 Товар: {product_type} ({amount} шт)\n"
                    text += f"💰 Сумма: {total:.2f}₽\n"
                    text += f"💳 Способ: {payment_method}\n"
                    text += f"📅 Время: {created_at[:16]}\n"
                    text += f"🎯 Действие: /check_{order_id}\n\n"
                
                text += "Используйте /check_номер для проверки конкретного заказа"
                await query.edit_message_text(text, reply_markup=admin_main_keyboard())
            else:
                text = "📋 Нет заявок на проверку"
                await query.edit_message_text(text, reply_markup=admin_main_keyboard())
        
        # АДМИН: Подтверждает, что деньги пришли
        elif data.startswith("admin_confirm_"):
            if user.id != ADMIN_ID:
                await query.edit_message_text("⛔ Доступ запрещен", reply_markup=main_menu())
                return
            
            order_id = data.replace("admin_confirm_", "")
            order_details = get_order_details(order_id)
            
            if order_details:
                order_id, user_id, username, first_name, product_type, amount, total, payment_method, status, created_at, user_paid, admin_confirmed = order_details
                
                # Обновляем статус - админ подтвердил оплату
                update_admin_confirmed(order_id)
                
                # Уведомляем пользователя
                try:
                    user_text = (
                        f"✅ ОПЛАТА ПОДТВЕРЖДЕНА!\n\n"
                        f"🆔 Заказ #{order_id}\n"
                        f"📦 Товар: {product_type} ({amount} шт)\n"
                        f"💰 Сумма: {total:.2f}₽\n\n"
                    )
                    
                    if product_type == 'stars':
                        user_text += f"⭐ Ваши {amount} звезд будут зачислены в ближайшее время!\n"
                    else:
                        user_text += f"👑 Ваш Premium аккаунт будет активирован в ближайшее время!\n"
                    
                    user_text += f"\n📞 По вопросам: {SUPPORT_USERNAME}"
                    
                    await query.bot.send_message(user_id, user_text)
                except Exception as e:
                    logger.error(f"Ошибка уведомления пользователя: {e}")
                
                # Сообщаем админу
                text = (
                    f"✅ Заказ #{order_id} подтвержден\n\n"
                    f"👤 Пользователь уведомлен\n"
                    f"📦 Товар: {product_type} ({amount} шт)\n"
                    f"💰 Сумма: {total:.2f}₽\n\n"
                    f"⚠️ Не забудьте отправить товар!"
                )
                
                await query.edit_message_text(text, reply_markup=admin_main_keyboard())
            else:
                await query.edit_message_text("❌ Заказ не найден", reply_markup=admin_main_keyboard())
        
        # АДМИН: Отклоняет (денег нет)
        elif data.startswith("admin_reject_"):
            if user.id != ADMIN_ID:
                await query.edit_message_text("⛔ Доступ запрещен", reply_markup=main_menu())
                return
            
            order_id = data.replace("admin_reject_", "")
            order_details = get_order_details(order_id)
            
            if order_details:
                order_id, user_id, username, first_name, product_type, amount, total, payment_method, status, created_at, user_paid, admin_confirmed = order_details
                
                # Обновляем статус - админ не нашел оплату
                update_admin_rejected(order_id)
                
                # Уведомляем пользователя
                try:
                    user_text = (
                        f"❌ ОПЛАТА НЕ НАЙДЕНА\n\n"
                        f"🆔 Заказ #{order_id}\n"
                        f"📦 Товар: {product_type} ({amount} шт)\n"
                        f"💰 Сумма: {total:.2f}₽\n\n"
                        f"⚠️ Мы не обнаружили поступление средств\n"
                        f"📞 Свяжитесь с поддержкой: {SUPPORT_USERNAME}\n\n"
                        f"Возможные причины:\n"
                        f"• Неправильно указан комментарий\n"
                        f"• Платеж еще в обработке\n"
                        f"• Ошибка в сумме перевода"
                    )
                    
                    await query.bot.send_message(user_id, user_text)
                except Exception as e:
                    logger.error(f"Ошибка уведомления пользователя: {e}")
                
                # Сообщаем админу
                text = f"❌ Заказ #{order_id} отклонен (деньги не найдены)"
                await query.edit_message_text(text, reply_markup=admin_main_keyboard())
            else:
                await query.edit_message_text("❌ Заказ не найден", reply_markup=admin_main_keyboard())
        
        # Админ: Статистика
        elif data == "admin_stats":
            if user.id != ADMIN_ID:
                await query.edit_message_text("⛔ Доступ запрещен", reply_markup=main_menu())
                return
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM users')
            total_users = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM orders')
            total_orders = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM orders WHERE status = "оплачен"')
            paid_orders = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM orders WHERE status = "ожидает проверки"')
            pending_orders = cursor.fetchone()[0]
            
            cursor.execute('SELECT SUM(total) FROM orders WHERE status = "оплачен"')
            total_revenue = cursor.fetchone()[0] or 0
            
            conn.close()
            
            text = f"📊 СТАТИСТИКА БОТА\n\n"
            text += f"👥 Пользователей: {total_users}\n"
            text += f"📦 Всего заказов: {total_orders}\n"
            text += f"✅ Оплаченных: {paid_orders}\n"
            text += f"🔄 Ожидают проверки: {pending_orders}\n"
            text += f"💰 Общая выручка: {total_revenue:.2f}₽\n"
            
            await query.edit_message_text(text, reply_markup=admin_main_keyboard())
        
        # Выбор способа оплаты
        elif data.startswith("pay_"):
            payment_method_id = data.replace("pay_", "")
            
            if payment_method_id not in PAYMENT_METHODS:
                await query.edit_message_text("❌ Этот способ оплаты недоступен", reply_markup=main_menu())
                return
            
            method_data = PAYMENT_METHODS[payment_method_id]
            if not method_data.get('enabled', True):
                await query.edit_message_text("❌ Этот способ оплаты временно недоступен", reply_markup=main_menu())
                return
            
            if 'order_data' in context.user_data:
                order_data = context.user_data['order_data']
                await process_payment(query, order_data, payment_method_id)
            else:
                await query.edit_message_text("❌ Ошибка: данные заказа не найдены", reply_markup=main_menu())
        
        else:
            await query.edit_message_text("Неизвестная команда", reply_markup=main_menu())
            
    except Exception as e:
        logger.error(f"Ошибка в callback: {e}")

async def process_payment(query, order_data, payment_method_id):
    """Создание заказа и показ реквизитов"""
    product = order_data.get('product', 'stars')
    description = order_data.get('description', '')
    amount = order_data['amount']
    total = order_data['total']
    
    # Получаем данные способа оплаты
    method = PAYMENT_METHODS.get(payment_method_id)
    
    if not method:
        await query.edit_message_text("❌ Способ оплаты не найден", reply_markup=main_menu())
        return
    
    # Формируем текст для оплаты
    if product == 'stars':
        product_text = f"⭐ {amount} звезд"
    else:
        product_text = description
    
    payment_text = (
        f"✅ Заказ создан!\n\n"
        f"{product_text}\n"
        f"💰 Сумма: {total:.2f}₽\n"
        f"💳 Способ оплаты: {method['name']}\n\n"
        f"{method['instructions']}:\n"
        f"```\n{method['details']}\n```\n\n"
        f"💡 После оплаты нажмите кнопку ✅ 'Я ОПЛАТИЛ'"
    )
    
    # Для криптовалют добавляем инструкции
    if payment_method_id in ['usdt_trc20', 'bitcoin', 'ton']:
        payment_text += f"\n\n🔔 *Для криптоплатежей:*\n"
        payment_text += f"• Переведите точную сумму\n"
        payment_text += f"• Дождитесь подтверждения сети\n"
        payment_text += f"• Сохраните хэш транзакции\n"
    
    # Создаем заказ в базе
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Определяем цену за единицу
    unit_price = STAR_PRICE if product == 'stars' else total
    
    cursor.execute('''
    INSERT INTO orders (user_id, product_type, amount, price, total, payment_method, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (query.from_user.id, product, amount, unit_price, total, method['name'], 
          datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    
    order_id = cursor.lastrowid
    
    # Обновляем статистику пользователя (только после оплаты)
    conn.commit()
    conn.close()
    
    # 🔔 УВЕДОМЛЕНИЕ АДМИНУ ПРИ СОЗДАНИИ ЗАКАЗА
    try:
        admin_notification = (
            f"🆕 НОВЫЙ ЗАКАЗ #{order_id}\n\n"
            f"👤 Пользователь: {query.from_user.first_name or 'Без имени'}\n"
            f"📛 @{query.from_user.username or 'нет'}\n"
            f"🆔 ID: {query.from_user.id}\n"
            f"📦 Товар: {description if product == 'premium' else f'{amount} звезд'}\n"
            f"💰 Сумма: {total:.2f}₽\n"
            f"💳 Способ оплаты: {method['name']}\n"
            f"📅 Время: {datetime.now().strftime('%H:%M:%S')}\n\n"
            f"⚠️ Ждем, когда пользователь оплатит и нажмет 'Я ОПЛАТИЛ'"
        )
        
        await query.bot.send_message(
            ADMIN_ID,
            admin_notification,
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Ошибка уведомления админу о новом заказе: {e}")
    
    # Показываем пользователю реквизиты и кнопку "Я ОПЛАТИЛ"
    await query.edit_message_text(
        payment_text, 
        parse_mode="Markdown",
        reply_markup=user_paid_keyboard(order_id)
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    try:
        user = update.effective_user
        text = update.message.text.strip()
        
        logger.info(f"Сообщение от {user.id}: {text}")
        
        # Обработка команды /check для админа
        if text.startswith("/check_"):
            if user.id != ADMIN_ID:
                await update.message.reply_text("⛔ Доступ запрещен", reply_markup=main_menu())
                return
            
            try:
                order_id = text.replace("/check_", "")
                order_details = get_order_details(order_id)
                
                if order_details:
                    order_id, user_id, username, first_name, product_type, amount, total, payment_method, status, created_at, user_paid, admin_confirmed = order_details
                    
                    admin_text = (
                        f"📋 ПРОВЕРКА ЗАКАЗА #{order_id}\n\n"
                        f"👤 Пользователь: {first_name or 'Без имени'}\n"
                        f"📛 @{username or 'нет'}\n"
                        f"🆔 ID: {user_id}\n"
                        f"📦 Товар: {product_type} ({amount} шт)\n"
                        f"💰 Сумма: {total:.2f}₽\n"
                        f"💳 Способ: {payment_method}\n"
                        f"📊 Статус: {status}\n"
                        f"📅 Создан: {created_at[:16]}\n\n"
                        f"Пользователь нажал 'Я оплатил': {'✅' if user_paid else '❌'}\n"
                        f"Админ подтвердил: {'✅' if admin_confirmed else '❌'}"
                    )
                    
                    await update.message.reply_text(
                        admin_text,
                        reply_markup=admin_confirmation_keyboard(order_id)
                    )
                else:
                    await update.message.reply_text("❌ Заказ не найден", reply_markup=admin_main_keyboard())
            except Exception as e:
                logger.error(f"Ошибка обработки /check: {e}")
                await update.message.reply_text("❌ Ошибка обработки команды", reply_markup=admin_main_keyboard())
            
            return
        
        # Если пользователь вводит количество звезд
        if context.user_data.get('waiting_amount') and text.isdigit():
            amount = int(text)
            product = context.user_data.get('product', 'stars')
            
            if product == 'stars':
                if MIN_STARS <= amount <= MAX_STARS:
                    total = amount * STAR_PRICE
                    
                    # Сохраняем данные заказа
                    context.user_data['order_data'] = {
                        'product': 'stars',
                        'description': f'Звезды',
                        'amount': amount,
                        'total': total
                    }
                    
                    # Спрашиваем способ оплаты
                    text = f"⭐ Заказ: {amount} звезд\n💰 Сумма: {total:.2f}₽\n\nВыберите способ оплаты:"
                    await update.message.reply_text(text, reply_markup=payment_methods_keyboard())
                    
                else:
                    await update.message.reply_text(f"❌ Введите число от {MIN_STARS} до {MAX_STARS}")
            
            context.user_data.pop('waiting_amount', None)
            context.user_data.pop('product', None)
            return
        
        # Админские команды
        if user.id == ADMIN_ID:
            if text.startswith("/sendall "):
                message = text.replace("/sendall ", "", 1)
                await update.message.reply_text(f"✅ Рассылка: {message}")
                return
            
            elif text == "/orders":
                orders = get_pending_confirmations()
                
                if orders:
                    text = "📋 ЗАЯВКИ НА ПРОВЕРКУ:\n\n"
                    for order in orders:
                        order_id, user_id, username, first_name, product_type, amount, total, payment_method, created_at = order
                        text += f"🆔 Заказ #{order_id}\n"
                        text += f"👤 Пользователь: {first_name or 'Без имени'} (@{username or 'нет'})\n"
                        text += f"📦 Товар: {product_type} ({amount} шт)\n"
                        text += f"💰 Сумма: {total:.2f}₽\n"
                        text += f"💳 Способ: {payment_method}\n"
                        text += f"📅 Время: {created_at[:16]}\n"
                        text += f"🎯 Действие: /check_{order_id}\n\n"
                    
                    await update.message.reply_text(text, reply_markup=admin_main_keyboard())
                else:
                    await update.message.reply_text("📋 Нет заявок на проверку", reply_markup=admin_main_keyboard())
                return
            
            elif text == "/stats":
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                
                cursor.execute('SELECT COUNT(*) FROM users')
                total_users = cursor.fetchone()[0]
                
                cursor.execute('SELECT SUM(total) FROM orders WHERE status = "оплачен"')
                revenue = cursor.fetchone()[0] or 0
                
                conn.close()
                
                await update.message.reply_text(f"📊 Статистика:\n👥 Пользователей: {total_users}\n💰 Выручка: {revenue:.2f}₽")
                return
        
        # Любое другое сообщение
        if user.id == ADMIN_ID:
            await update.message.reply_text(
                "Используйте админ-меню для управления",
                reply_markup=admin_main_keyboard()
            )
        else:
            await update.message.reply_text(
                "Используйте меню для выбора действия",
                reply_markup=main_menu()
            )
        
    except Exception as e:
        logger.error(f"Ошибка обработки сообщения: {e}")

# ==================== ЗАПУСК БОТА ====================
def main():
    """Запуск бота"""
    print("=" * 60)
    print("🤖 ЗАПУСК ТЕЛЕГРАМ БОТА")
    print(f"🔑 Токен: {BOT_TOKEN[:12]}...")
    print(f"👑 Админ ID: {ADMIN_ID}")
    print(f"💬 Поддержка: {SUPPORT_USERNAME}")
    print("=" * 60)
    print("\n📊 НАСТРОЙКИ:")
    print(f"⭐ Цена звезды: {STAR_PRICE}₽")
    print(f"⭐ Диапазон: {MIN_STARS}-{MAX_STARS} звезд")
    print(f"👑 Premium: 3м({PREMIUM_PRICES['3']['цена']}₽), 6м({PREMIUM_PRICES['6']['цена']}₽), 12м({PREMIUM_PRICES['12']['цена']}₽)")
    print("\n💳 СПОСОБЫ ОПЛАТЫ:")
    for method_id, method in PAYMENT_METHODS.items():
        if method['enabled']:
            print(f"  ✅ {method['name']}")
    print("=" * 60)
    
    # Инициализируем базу данных
    init_database()
    
    try:
        # Создаем приложение
        app = Application.builder().token(BOT_TOKEN).build()
        logger.info("Приложение создано")
        
        # Добавляем обработчики
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("orders", start))
        app.add_handler(CommandHandler("stats", start))
        app.add_handler(CallbackQueryHandler(handle_callback))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        logger.info("Обработчики добавлены")
        
        # Запускаем бота
        print("\n🔄 Запускаю бота...")
        print("📱 Откройте Telegram и напишите боту /start")
        print("👑 Админ получит уведомления о новых заказах")
        print("=" * 60)
        
        app.run_polling(
            poll_interval=1.0,
            timeout=30,
            drop_pending_updates=True
        )
        
    except Exception as e:
        logger.error(f"ОШИБКА ЗАПУСКА: {e}")
        print(f"❌ Ошибка запуска: {e}")
        print("\n🔧 Возможные причины:")
        print("1. Неверный токен бота")
        print("2. Бот заблокирован в @BotFather")
        print("3. Нет интернет-соединения")
        print("4. Библиотека не установлена: pip install python-telegram-bot==20.7")

if __name__ == "__main__":
    main()
