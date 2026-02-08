#!/usr/bin/env python3
"""
Telegram Stars Bot - Русская версия
Бот для покупки Telegram Stars и Premium
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
STAR_PRICE = 1.6  # рубль за 1 звезду
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
    
    # Таблица пользователей
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
    
    # Таблица заказов
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS orders (
        order_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        product_type TEXT,
        amount INTEGER,
        price REAL,
        total REAL,
        payment_method TEXT,
        status TEXT DEFAULT 'ожидает',
        created_at TIMESTAMP,
        paid_at TIMESTAMP
    )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("База данных инициализирована")

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
            text = "👑 Telegram Premium\n\nВыберите срок подписки:"
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
            
            await query.edit_message_text(text, reply_mup=keyboard)
        
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
                    status_emoji = "✅" if status == "оплачен" else "⏳" if status == "ожидает" else "❌"
                    product_emoji = "⭐" if product_type == "stars" else "👑"
                    text += f"{status_emoji} {product_emoji} Заказ #{order_id}\n"
                    text += f"   {product_type.capitalize()}: {amount} шт\n"
                    text += f"   💰 {total:.2f}₽\n"
                    text += f"   📅 {created_at[:16]}\n\n"
            else:
                text = "📦 У вас пока нет заказов"
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("⭐ Купить звезды", callback_data="buy_stars")],
                [InlineKeyboardButton("🔙 Назад", callback_data="main")]
            ])
            
            await query.edit_message_text(text, reply_markup=keyboard)
        
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
    """Обработка платежа"""
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
        f"```\n{method['details']}\n```"
    )
    
    # Для криптовалют добавляем инструкции
    if payment_method_id in ['usdt_trc20', 'bitcoin', 'ton']:
        payment_text += f"\n\n🔔 *Для криптоплатежей:*\n"
        payment_text += f"• Переведите точную сумму\n"
        payment_text += f"• Дождитесь подтверждения сети\n"
        payment_text += f"• Пришлите хэш транзакции\n"
    
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
    
    # Обновляем статистику пользователя
    if product == 'stars':
        cursor.execute('''
        UPDATE users 
        SET total_stars = total_stars + ?, 
            total_spent = total_spent + ?
        WHERE user_id = ?
        ''', (amount, total, query.from_user.id))
    else:
        cursor.execute('''
        UPDATE users 
        SET total_spent = total_spent + ?
        WHERE user_id = ?
        ''', (total, query.from_user.id))
    
    conn.commit()
    conn.close()
    
    # Уведомление админу
    try:
        await query.bot.send_message(
            ADMIN_ID,
            f"💰 НОВЫЙ ЗАКАЗ #{order_id}\n\n"
            f"👤 Пользователь: {query.from_user.first_name or 'Без имени'}\n"
            f"📛 @{query.from_user.username or 'нет'}\n"
            f"🆔 ID: {query.from_user.id}\n"
            f"📦 Товар: {description if product == 'premium' else f'{amount} звезд'}\n"
            f"💰 Сумма: {total:.2f}₽\n"
            f"💳 Способ: {method['name']}\n"
            f"📅 Время: {datetime.now().strftime('%H:%M:%S')}",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Ошибка уведомления админу: {e}")
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 Мои заказы", callback_data="my_orders")],
        [InlineKeyboardButton("🛒 Новый заказ", callback_data="main")],
        [InlineKeyboardButton("💬 Поддержка", url=f"https://t.me/{SUPPORT_USERNAME.replace('@', '')}")]
    ])
    
    await query.edit_message_text(payment_text, parse_mode="Markdown", reply_markup=keyboard)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    try:
        user = update.effective_user
        text = update.message.text.strip()
        
        logger.info(f"Сообщение от {user.id}: {text}")
        
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
        if user.id == ADMIN_ID and text.startswith("/sendall "):
            message = text.replace("/sendall ", "", 1)
            await update.message.reply_text(f"✅ Рассылка: {message}")
            return
        
        # Любое другое сообщение
        await update.message.reply_text(
            "Используйте меню для выбора действия",
            reply_markup=main_menu()
        )
        
    except Exception as e:
        logger.error(f"Ошибка обработки сообщения: {e}")

# ==================== ЗАПУСК БОТА ====================
def main():
    """Запуск бота"""
    print("=" * 50)
    print("🤖 ЗАПУСК ТЕЛЕГРАМ БОТА")
    print(f"🔑 Токен: {BOT_TOKEN[:10]}...")
    print(f"👑 Админ: {ADMIN_ID}")
    print("=" * 50)
    
    # Инициализируем базу данных
    init_database()
    
    try:
        # Создаем приложение
        app = Application.builder().token(BOT_TOKEN).build()
        logger.info("Приложение создано")
        
        # Добавляем обработчики
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CallbackQueryHandler(handle_callback))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        logger.info("Обработчики добавлены")
        
        # Запускаем бота
        print("🔄 Запускаю бота...")
        app.run_polling(
            poll_interval=1.0,
            timeout=30,
            drop_pending_updates=True
        )
        
    except Exception as e:
        logger.error(f"ОШИБКА ЗАПУСКА: {e}")
        print(f"❌ Ошибка запуска: {e}")

if __name__ == "__main__":
    main()
