#!/usr/bin/env python3
"""
Telegram Stars Bot - Полная версия с вашими реквизитами
"""

import os
import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

# Проверяем доступность библиотек
try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
    print("✅ Библиотеки загружены")
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

STAR_PRICE = 1.6
MIN_STARS = 50
MAX_STARS = 5000

# База данных
DB_PATH = "bot_database.db"

# ==================== ВАШИ СПОСОБЫ ОПЛАТЫ ====================
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
        amount INTEGER,
        price REAL,
        total REAL,
        payment_method TEXT,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP,
        paid_at TIMESTAMP
    )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("База данных инициализирована")

# ==================== КЛАВИАТУРЫ ====================
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⭐ Купить звезды", callback_data="buy")],
        [InlineKeyboardButton("👑 Premium", callback_data="premium")],
        [InlineKeyboardButton("📊 Профиль", callback_data="profile")],
        [InlineKeyboardButton("📦 Мои заказы", callback_data="my_orders")],
    ])

def payment_methods_keyboard():
    """Клавиатура с вашими способами оплаты"""
    # Создаем 2 колонки для лучшего вида
    buttons = []
    
    methods = list(PAYMENT_METHODS.items())
    
    # Первый ряд: Карта РФ и USDT
    row1 = []
    if 'card_ru' in PAYMENT_METHODS and PAYMENT_METHODS['card_ru'].get('enabled', True):
        row1.append(InlineKeyboardButton("💳 Карта РФ", callback_data="pay_card_ru"))
    if 'usdt_trc20' in PAYMENT_METHODS and PAYMENT_METHODS['usdt_trc20'].get('enabled', True):
        row1.append(InlineKeyboardButton("🌐 USDT", callback_data="pay_usdt_trc20"))
    if row1:
        buttons.append(row1)
    
    # Второй ряд: Bitcoin и TON
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

def admin_menu():
    """Меню администратора"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("📦 Заказы", callback_data="admin_orders")],
        [InlineKeyboardButton("👥 Пользователи", callback_data="admin_users")],
        [InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🔙 Главное меню", callback_data="main")]
    ])

def back_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="main")]])

# ==================== ОСНОВНЫЕ ФУНКЦИИ ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    try:
        user = update.effective_user
        logger.info(f"Пользователь {user.id} запустил бота")
        
        # Регистрируем пользователя в базе
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
        INSERT OR IGNORE INTO users (user_id, username, first_name, registration_date)
        VALUES (?, ?, ?, ?)
        ''', (user.id, user.username, user.first_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
        
        text = f"👋 Привет, {user.first_name or 'друг'}!\n\n"
        text += "Я бот для покупки Telegram Stars ⭐\n\n"
        text += "Выберите действие:"
        
        # Если админ - показываем админ-меню
        if user.id == ADMIN_ID:
            text += "\n\n👑 Вы вошли как администратор"
            await update.message.reply_text(text, reply_markup=admin_menu())
        else:
            await update.message.reply_text(text, reply_markup=main_menu())
        
        logger.info("Команда /start выполнена успешно")
        
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
        
        if data == "main":
            await query.edit_message_text("Главное меню:", reply_markup=main_menu())
        
        elif data == "buy":
            text = f"⭐ Купить звезды\n\nЦена: {STAR_PRICE}₽ за 1 звезду\nВведите количество от {MIN_STARS} до {MAX_STARS}:"
            await query.edit_message_text(text, reply_markup=back_button())
            context.user_data['waiting_amount'] = True
        
        elif data == "premium":
            text = "👑 Telegram Premium\n\nТарифы:\n• 3 месяца - 1099₽\n• 6 месяцев - 1399₽\n• 12 месяцев - 2499₽"
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Назад", callback_data="main")]
            ])
            await query.edit_message_text(text, reply_markup=keyboard)
        
        elif data == "profile":
            # Получаем данные из базы
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('SELECT total_spent, total_stars FROM users WHERE user_id = ?', (user.id,))
            result = cursor.fetchone()
            conn.close()
            
            total_spent = result[0] if result else 0
            total_stars = result[1] if result else 0
            
            text = f"📊 Профиль\n\n"
            text += f"🆔 ID: {user.id}\n"
            text += f"👤 Имя: {user.first_name or 'Не указано'}\n"
            text += f"📛 Юзернейм: @{user.username or 'отсутствует'}\n"
            text += f"⭐ Всего звезд куплено: {total_stars}\n"
            text += f"💰 Всего потрачено: {total_spent:.2f}₽\n\n"
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📦 История заказов", callback_data="my_orders")],
                [InlineKeyboardButton("🔙 Назад", callback_data="main")]
            ])
            
            await query.edit_message_text(text, reply_markup=keyboard)
        
        elif data == "my_orders":
            # Получаем заказы пользователя
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''
            SELECT order_id, amount, total, status, created_at 
            FROM orders WHERE user_id = ? 
            ORDER BY created_at DESC 
            LIMIT 10
            ''', (user.id,))
            
            orders = cursor.fetchall()
            conn.close()
            
            if orders:
                text = "📦 Ваши последние заказы:\n\n"
                for order in orders:
                    order_id, amount, total, status, created_at = order
                    status_emoji = "✅" if status == "paid" else "⏳" if status == "pending" else "❌"
                    text += f"{status_emoji} Заказ #{order_id}\n"
                    text += f"   ⭐ {amount} звезд\n"
                    text += f"   💰 {total:.2f}₽\n"
                    text += f"   📅 {created_at[:16]}\n\n"
            else:
                text = "📦 У вас пока нет заказов"
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("⭐ Купить звезды", callback_data="buy")],
                [InlineKeyboardButton("🔙 Назад", callback_data="main")]
            ])
            
            await query.edit_message_text(text, reply_markup=keyboard)
        
        # Админские функции
        elif data == "admin_stats":
            if user.id != ADMIN_ID:
                await query.edit_message_text("⛔ Доступ запрещен", reply_markup=main_menu())
                return
            
            # Статистика
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Общая статистика
            cursor.execute('SELECT COUNT(*) FROM users')
            total_users = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM orders')
            total_orders = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM orders WHERE status = "paid"')
            paid_orders = cursor.fetchone()[0]
            
            cursor.execute('SELECT SUM(total) FROM orders WHERE status = "paid"')
            total_revenue = cursor.fetchone()[0] or 0
            
            cursor.execute('SELECT SUM(amount) FROM orders WHERE status = "paid"')
            total_stars = cursor.fetchone()[0] or 0
            
            conn.close()
            
            text = f"📊 Статистика бота\n\n"
            text += f"👥 Пользователей: {total_users}\n"
            text += f"📦 Всего заказов: {total_orders}\n"
            text += f"✅ Оплаченных: {paid_orders}\n"
            text += f"💰 Общая выручка: {total_revenue:.2f}₽\n"
            text += f"⭐ Всего звезд продано: {total_stars}\n"
            
            await query.edit_message_text(text, reply_markup=admin_menu())
        
        elif data == "admin_orders":
            if user.id != ADMIN_ID:
                await query.edit_message_text("⛔ Доступ запрещен", reply_markup=main_menu())
                return
            
            # Показать последние заказы
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''
            SELECT o.order_id, o.user_id, u.username, o.amount, o.total, o.status, o.created_at
            FROM orders o
            LEFT JOIN users u ON o.user_id = u.user_id
            ORDER BY o.created_at DESC 
            LIMIT 10
            ''')
            
            orders = cursor.fetchall()
            conn.close()
            
            if orders:
                text = "📦 Последние заказы:\n\n"
                for order in orders:
                    order_id, user_id, username, amount, total, status, created_at = order
                    status_emoji = "✅" if status == "paid" else "⏳" if status == "pending" else "❌"
                    text += f"{status_emoji} Заказ #{order_id}\n"
                    text += f"   👤 ID: {user_id} (@{username or 'нет'})\n"
                    text += f"   ⭐ {amount} звезд\n"
                    text += f"   💰 {total:.2f}₽\n"
                    text += f"   📅 {created_at[:16]}\n\n"
            else:
                text = "📦 Заказов пока нет"
            
            await query.edit_message_text(text, reply_markup=admin_menu())
        
        # Обработка способов оплаты
        elif data == "pay_card_ru":
            method_id = "card_ru"
            if method_id not in PAYMENT_METHODS:
                await query.edit_message_text("❌ Этот способ оплаты недоступен", reply_markup=main_menu())
                return
            
            method_data = PAYMENT_METHODS[method_id]
            if not method_data.get('enabled', True):
                await query.edit_message_text("❌ Этот способ оплаты временно недоступен", reply_markup=main_menu())
                return
            
            if 'order_data' in context.user_data:
                order_data = context.user_data['order_data']
                await process_payment(query, order_data, method_id)
            else:
                await query.edit_message_text("❌ Ошибка: данные заказа не найдены", reply_markup=main_menu())
        
        elif data == "pay_usdt_trc20":
            method_id = "usdt_trc20"
            if method_id not in PAYMENT_METHODS:
                await query.edit_message_text("❌ Этот способ оплаты недоступен", reply_markup=main_menu())
                return
            
            method_data = PAYMENT_METHODS[method_id]
            if not method_data.get('enabled', True):
                await query.edit_message_text("❌ Этот способ оплаты временно недоступен", reply_markup=main_menu())
                return
            
            if 'order_data' in context.user_data:
                order_data = context.user_data['order_data']
                await process_payment(query, order_data, method_id)
            else:
                await query.edit_message_text("❌ Ошибка: данные заказа не найдены", reply_markup=main_menu())
        
        elif data == "pay_bitcoin":
            method_id = "bitcoin"
            if method_id not in PAYMENT_METHODS:
                await query.edit_message_text("❌ Этот способ оплаты недоступен", reply_markup=main_menu())
                return
            
            method_data = PAYMENT_METHODS[method_id]
            if not method_data.get('enabled', True):
                await query.edit_message_text("❌ Этот способ оплаты временно недоступен", reply_markup=main_menu())
                return
            
            if 'order_data' in context.user_data:
                order_data = context.user_data['order_data']
                await process_payment(query, order_data, method_id)
            else:
                await query.edit_message_text("❌ Ошибка: данные заказа не найдены", reply_markup=main_menu())
        
        elif data == "pay_ton":
            method_id = "ton"
            if method_id not in PAYMENT_METHODS:
                await query.edit_message_text("❌ Этот способ оплаты недоступен", reply_markup=main_menu())
                return
            
            method_data = PAYMENT_METHODS[method_id]
            if not method_data.get('enabled', True):
                await query.edit_message_text("❌ Этот способ оплаты временно недоступен", reply_markup=main_menu())
                return
            
            if 'order_data' in context.user_data:
                order_data = context.user_data['order_data']
                await process_payment(query, order_data, method_id)
            else:
                await query.edit_message_text("❌ Ошибка: данные заказа не найдены", reply_markup=main_menu())
        
        else:
            await query.edit_message_text("Неизвестная команда", reply_markup=main_menu())
            
    except Exception as e:
        logger.error(f"Ошибка в callback: {e}")

async def process_payment(query, order_data, payment_method_id):
    """Обработка платежа"""
    amount = order_data['amount']
    total = order_data['total']
    
    # Получаем данные способа оплаты
    method = PAYMENT_METHODS.get(payment_method_id)
    
    if not method:
        await query.edit_message_text("❌ Способ оплаты не найден", reply_markup=main_menu())
        return
    
    payment_text = (
        f"✅ Заказ создан!\n\n"
        f"⭐ Количество: {amount} звезд\n"
        f"💰 Сумма: {total:.2f}₽\n"
        f"💳 Способ оплаты: {method['name']}\n\n"
        f"{method['instructions']}:\n"
        f"```\n{method['details']}\n```\n\n"
        f"📞 После оплаты напишите: {SUPPORT_USERNAME}\n"
        f"⚠️ В комментарии укажите: stars{query.from_user.id}"
    )
    
    # Особые инструкции для криптовалют
    if payment_method_id in ['usdt_trc20', 'bitcoin', 'ton']:
        payment_text += f"\n\n🔔 ВАЖНО для криптоплатежей:\n"
        payment_text += f"1. Переведите ТОЧНУЮ сумму в рублях по текущему курсу\n"
        payment_text += f"2. Дождитесь подтверждения в сети\n"
        payment_text += f"3. Пришлите хэш транзакции (TXID)\n"
        payment_text += f"4. Мы зачислим звезды после 1 подтверждения сети\n"
    
    # Создаем заказ в базе
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO orders (user_id, amount, price, total, payment_method, created_at)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', (query.from_user.id, amount, STAR_PRICE, total, method['name'], 
          datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    
    order_id = cursor.lastrowid
    
    # Обновляем статистику пользователя
    cursor.execute('''
    UPDATE users 
    SET total_stars = total_stars + ?, 
        total_spent = total_spent + ?
    WHERE user_id = ?
    ''', (amount, total, query.from_user.id))
    
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
            f"⭐ Количество: {amount} звезд\n"
            f"💰 Сумма: {total:.2f}₽\n"
            f"💳 Способ: {method['name']}\n"
            f"📅 Время: {datetime.now().strftime('%H:%M:%S')}",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Ошибка уведомления админу: {e}")
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 Мои заказы", callback_data="my_orders")],
        [InlineKeyboardButton("⭐ Новый заказ", callback_data="buy")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main")]
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
            
            if MIN_STARS <= amount <= MAX_STARS:
                total = amount * STAR_PRICE
                
                # Сохраняем данные заказа
                order_data = {
                    'amount': amount,
                    'total': total
                }
                
                context.user_data['order_data'] = order_data
                
                # Спрашиваем способ оплаты
                text = f"⭐ Заказ: {amount} звезд\n💰 Сумма: {total:.2f}₽\n\nВыберите способ оплаты:"
                await update.message.reply_text(text, reply_markup=payment_methods_keyboard())
                
            else:
                await update.message.reply_text(f"❌ Введите число от {MIN_STARS} до {MAX_STARS}")
            
            context.user_data.pop('waiting_amount', None)
            return
        
        # Админские команды
        if user.id == ADMIN_ID:
            if text.startswith("/sendall "):
                message = text.replace("/sendall ", "", 1)
                await update.message.reply_text(f"✅ Рассылка: {message}")
                return
            
            elif text.startswith("/payment "):
                # Включить/выключить способ оплаты
                parts = text.split()
                if len(parts) >= 3:
                    method_id = parts[1]
                    action = parts[2].lower()
                    
                    if method_id in PAYMENT_METHODS:
                        if action == "on":
                            PAYMENT_METHODS[method_id]['enabled'] = True
                            await update.message.reply_text(f"✅ Способ оплаты '{PAYMENT_METHODS[method_id]['name']}' включен")
                        elif action == "off":
                            PAYMENT_METHODS[method_id]['enabled'] = False
                            await update.message.reply_text(f"❌ Способ оплаты '{PAYMENT_METHODS[method_id]['name']}' выключен")
                    else:
                        await update.message.reply_text("❌ Способ оплаты не найден")
                return
            
            elif text == "/stats":
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM users')
                total_users = cursor.fetchone()[0]
                cursor.execute('SELECT SUM(total) FROM orders WHERE status = "paid"')
                revenue = cursor.fetchone()[0] or 0
                conn.close()
                
                await update.message.reply_text(f"📊 Статистика:\n👥 Пользователей: {total_users}\n💰 Выручка: {revenue:.2f}₽")
                return
        
        # Любое другое сообщение
        await update.message.reply_text(
            "Используйте команду /start для доступа к меню",
            reply_markup=main_menu()
        )
        
    except Exception as e:
        logger.error(f"Ошибка обработки сообщения: {e}")

# ==================== ЗАПУСК БОТА ====================
def main():
    """Запуск бота"""
    print("=" * 50)
    print("🤖 ЗАПУСК БОТА С ВАШИМИ РЕКВИЗИТАМИ")
    print(f"🔑 Токен: {BOT_TOKEN[:10]}...")
    print(f"👑 Админ: {ADMIN_ID}")
    print("=" * 50)
    
    # Показываем ваши способы оплаты
    print("\n📋 ВАШИ СПОСОБЫ ОПЛАТЫ:")
    print("1. 💳 Карта РФ")
    print("   Номер: 2202206713916687")
    print("   Получатель: ROMAN IVANOV")
    print()
    print("2. 🌐 USDT (TRC20)")
    print("   Адрес: TT6QmsrMhctAabpY9Cy5eSV3L1myxNeUwF")
    print("   Сеть: TRC20 (Tron)")
    print()
    print("3. ₿ Bitcoin")
    print("   Адрес: bc1qy9860j3zxjd3wpy6pj5tu7jpqkz84tzftq076p")
    print("   Сеть: Bitcoin (SegWit)")
    print()
    print("4. ⚡ TON")
    print("   Адрес: UQA2Xxf6CL2lx2XpiDvPPHr3heCJ5o6nRNBbxytj9eFVTpXx")
    print("   Сеть: TON")
    print("=" * 50)
    
    # Инициализируем базу данных
    init_database()
    
    try:
        # Создаем приложение
        app = Application.builder().token(BOT_TOKEN).build()
        logger.info("Приложение создано")
        
        # Добавляем обработчики
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("stats", start))
        app.add_handler(CallbackQueryHandler(handle_callback))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        logger.info("Обработчики добавлены")
        
        # Запускаем бота
        print("🔄 Запускаю polling...")
        app.run_polling(
            poll_interval=1.0,
            timeout=30,
            drop_pending_updates=True
        )
        
    except Exception as e:
        logger.error(f"КРИТИЧЕСКАЯ ОШИБКА: {e}")
        print(f"❌ Ошибка запуска: {e}")

if __name__ == "__main__":
    main()
