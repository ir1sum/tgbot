#!/usr/bin/env python3
"""
Telegram Stars Bot - Оптимизированная версия для Amvera
Все в одном файле, минимум зависимостей
"""

import os
import json
import logging
import asyncio
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Optional, List

# Telegram импорты (минимум)
try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
    TELEGRAM_AVAILABLE = True
except ImportError:
    print("⚠️ Библиотека python-telegram-bot не установлена")
    print("Установите: pip install python-telegram-bot==20.7")
    TELEGRAM_AVAILABLE = False

# ==================== КОНФИГУРАЦИЯ ====================
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN", "8196751032:AAGwizPBRuq_uh0zd9GQ6C2BFiseAfnp_xo")
ADMIN_ID = 741906407

# Цены
STAR_PRICE_BUY = 1.6
STAR_PRICE_SELL = 1.0
MIN_STARS = 50
MAX_STARS = 5000

# Премиум тарифы (3 варианта + год)
PREMIUM_PLANS = {
    "1month": {"name": "1 Месяц", "price": 299, "days": 30, "emoji": "🟢"},
    "3months": {"name": "3 Месяца", "price": 799, "days": 90, "emoji": "🔵"},
    "6months": {"name": "6 Месяцев", "price": 1499, "days": 180, "emoji": "🟣"},
    "1year": {"name": "1 Год", "price": 2599, "days": 365, "emoji": "🟠"}
}

# Способы оплаты (4 варианта)
PAYMENT_METHODS = {
    "card": {
        "name": "💳 Карта РФ", 
        "details": "2202206713916687\nПолучатель: ROMAN IVANOV"
    },
    "usdt": {
        "name": "💎 USDT (TRC20)", 
        "details": "TT6QmsrMhctAabpY9Cy5eSV3L1myxNeUwF"
    },
    "btc": {
        "name": "₿ Bitcoin", 
        "details": "bc1qy9860j3zxjd3wpy6pj5tu7jpqkz84tzftq076p"
    },
    "ton": {
        "name": "⚡ TON", 
        "details": "UQA2Xxf6CL2lx2XpiDvPPHr3heCJ5o6nRNBbxytj9eFVTpXx"
    }
}

# ==================== УПРОЩЕННАЯ БАЗА ДАННЫХ ====================
class SimpleDB:
    """Ультра-легкая база данных для Amvera"""
    
    def __init__(self):
        self.db_path = "amvera_bot.db"
        self._init_db()
    
    def _init_db(self):
        """Создаем только самые необходимые таблицы"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        cursor = conn.cursor()
        
        # Только 2 таблицы для экономии
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                balance REAL DEFAULT 0.0,
                stars INTEGER DEFAULT 0,
                premium_until TEXT,
                created TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                user_id INTEGER,
                type TEXT,
                amount INTEGER,
                total REAL,
                status TEXT DEFAULT 'pending',
                created TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_user(self, user_id: int) -> Dict:
        """Получить пользователя"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()
        
        if user:
            result = dict(user)
            conn.close()
            return result
        
        # Создаем нового
        cursor.execute('''
            INSERT INTO users (user_id, balance, stars) VALUES (?, 0.0, 0)
        ''', (user_id,))
        
        conn.commit()
        conn.close()
        
        return {
            "user_id": user_id,
            "balance": 0.0,
            "stars": 0,
            "premium_until": None,
            "created": datetime.now().isoformat()
        }
    
    def update_balance(self, user_id: int, amount: float) -> bool:
        """Обновить баланс"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE users SET balance = balance + ? WHERE user_id = ?',
                (amount, user_id)
            )
            conn.commit()
            conn.close()
            return True
        except:
            return False
    
    def update_stars(self, user_id: int, amount: int) -> bool:
        """Обновить звезды"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE users SET stars = stars + ? WHERE user_id = ?',
                (amount, user_id)
            )
            conn.commit()
            conn.close()
            return True
        except:
            return False
    
    def create_order(self, order_id: str, user_id: int, order_type: str, 
                    amount: int, total: float) -> bool:
        """Создать заказ"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO orders (order_id, user_id, type, amount, total, status, created)
                VALUES (?, ?, ?, ?, ?, 'pending', ?)
            ''', (order_id, user_id, order_type, amount, total, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Ошибка создания заказа: {e}")
            return False

# Глобальная БД
db = SimpleDB()

# ==================== УПРОЩЕННЫЕ КЛАВИАТУРЫ ====================
def main_menu() -> InlineKeyboardMarkup:
    """Главное меню"""
    keyboard = [
        [
            InlineKeyboardButton("⭐ Купить", callback_data="buy"),
            InlineKeyboardButton("💰 Продать", callback_data="sell")
        ],
        [
            InlineKeyboardButton("👑 Премиум", callback_data="premium"),
            InlineKeyboardButton("💎 Баланс", callback_data="balance")
        ],
        [
            InlineKeyboardButton("📊 Профиль", callback_data="profile"),
            InlineKeyboardButton("🆘 Помощь", callback_data="help")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def back_button() -> InlineKeyboardMarkup:
    """Кнопка назад"""
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="main")]])

def quick_amounts(action: str) -> InlineKeyboardMarkup:
    """Быстрые суммы"""
    amounts = [50, 100, 250, 500, 1000]
    buttons = []
    
    for i in range(0, len(amounts), 2):
        row = []
        if i < len(amounts):
            row.append(InlineKeyboardButton(
                f"{amounts[i]}⭐", 
                callback_data=f"amt_{action}_{amounts[i]}"
            ))
        if i + 1 < len(amounts):
            row.append(InlineKeyboardButton(
                f"{amounts[i+1]}⭐", 
                callback_data=f"amt_{action}_{amounts[i+1]}"
            ))
        if row:
            buttons.append(row)
    
    buttons.append([InlineKeyboardButton("✏️ Свое число", callback_data=f"custom_{action}")])
    buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="main")])
    
    return InlineKeyboardMarkup(buttons)

def payment_buttons(order_id: str = None) -> InlineKeyboardMarkup:
    """Кнопки оплаты"""
    buttons = []
    
    for method_id, method in PAYMENT_METHODS.items():
        if order_id:
            callback = f"pay_{method_id}_{order_id}"
        else:
            callback = f"deposit_{method_id}"
        
        buttons.append([InlineKeyboardButton(method["name"], callback_data=callback)])
    
    buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="main")])
    
    return InlineKeyboardMarkup(buttons)

def premium_buttons() -> InlineKeyboardMarkup:
    """Кнопки премиум"""
    buttons = []
    
    for plan_id, plan in PREMIUM_PLANS.items():
        text = f"{plan['emoji']} {plan['name']} - {plan['price']}₽"
        buttons.append([InlineKeyboardButton(text, callback_data=f"prem_{plan_id}")])
    
    buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="main")])
    
    return InlineKeyboardMarkup(buttons)

# ==================== ОСНОВНЫЕ ОБРАБОТЧИКИ ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    user = update.effective_user
    user_data = db.get_user(user.id)
    
    text = (
        f"👋 Привет, {user.first_name}!\n\n"
        f"💰 Баланс: {user_data['balance']:.1f}₽\n"
        f"⭐ Звезд: {user_data['stars']}\n\n"
        f"Купить: {STAR_PRICE_BUY}₽ | Продать: {STAR_PRICE_SELL}₽\n\n"
        f"Выберите действие:"
    )
    
    await update.message.reply_text(text, reply_markup=main_menu())

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопок"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    # Главное меню
    if data == "main":
        user_data = db.get_user(user_id)
        text = f"Баланс: {user_data['balance']:.1f}₽ | Звезд: {user_data['stars']}"
        await query.edit_message_text(text, reply_markup=main_menu())
        return
    
    # Покупка/продажа
    if data in ["buy", "sell"]:
        action = "ПОКУПКИ" if data == "buy" else "ПРОДАЖИ"
        price = STAR_PRICE_BUY if data == "buy" else STAR_PRICE_SELL
        
        text = f"{action} ⭐\nЦена: {price}₽/шт\nМин: {MIN_STARS}, Макс: {MAX_STARS}"
        await query.edit_message_text(text, reply_markup=quick_amounts(data))
        return
    
    # Быстрый выбор количества
    if data.startswith("amt_"):
        _, action, amount_str = data.split("_")
        amount = int(amount_str)
        await process_order(user_id, query, action, amount)
        return
    
    # Ручной ввод
    if data.startswith("custom_"):
        action = data.replace("custom_", "")
        context.user_data['action'] = action
        
        await query.edit_message_text(
            f"Введите количество звезд для {'покупки' if action == 'buy' else 'продажи'}:\n"
            f"От {MIN_STARS} до {MAX_STARS}",
            reply_markup=back_button()
        )
        return
    
    # Премиум
    if data == "premium":
        text = "👑 ПРЕМИУМ ПОДПИСКА\n\nВыберите срок:"
        await query.edit_message_text(text, reply_markup=premium_buttons())
        return
    
    # Выбор премиум тарифа
    if data.startswith("prem_"):
        plan_id = data.replace("prem_", "")
        plan = PREMIUM_PLANS.get(plan_id)
        
        if plan:
            order_id = f"premium_{user_id}_{int(datetime.now().timestamp())}"
            db.create_order(order_id, user_id, "premium", plan["days"], plan["price"])
            
            text = f"👑 {plan['name']}\nЦена: {plan['price']}₽\nВыберите способ оплаты:"
            await query.edit_message_text(text, reply_markup=payment_buttons(order_id))
        return
    
    # Профиль
    if data == "profile":
        user_data = db.get_user(user_id)
        text = (
            f"📊 ПРОФИЛЬ\n\n"
            f"🆔 ID: {user_id}\n"
            f"💰 Баланс: {user_data['balance']:.1f}₽\n"
            f"⭐ Звезд: {user_data['stars']}\n"
            f"👑 Премиум: {'Да' if user_data['premium_until'] else 'Нет'}\n\n"
            f"🎁 Промокод: IRIS666"
        )
        await query.edit_message_text(text, reply_markup=back_button())
        return
    
    # Баланс/пополнение
    if data == "balance":
        text = f"Ваш ID для оплаты: `{user_id}`\nВыберите способ пополнения:"
        await query.edit_message_text(text, reply_markup=payment_buttons(), parse_mode="Markdown")
        return
    
    # Помощь
    if data == "help":
        text = "📞 Поддержка: @iris_support\n\nПромокод: IRIS666"
        await query.edit_message_text(text, reply_markup=back_button())
        return
    
    # Оплата
    if data.startswith("pay_") or data.startswith("deposit_"):
        parts = data.split("_")
        
        if len(parts) >= 2:
            method_id = parts[1]
            method = PAYMENT_METHODS.get(method_id)
            
            if method:
                if len(parts) >= 3:
                    order_id = parts[2]
                    text = f"Оплата заказа #{order_id}\n\n{method['name']}:\n```\n{method['details']}\n```"
                    
                    keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton("✅ Я оплатил", callback_data=f"paid_{order_id}")],
                        [InlineKeyboardButton("🔙 Назад", callback_data="main")]
                    ])
                else:
                    text = f"Пополнение баланса\n\n{method['name']}:\n```\n{method['details']}\n```\n\nВаш ID: `{user_id}`"
                    keyboard = back_button()
                
                await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
        return
    
    # Подтверждение оплаты
    if data.startswith("paid_"):
        order_id = data.replace("paid_", "")
        
        # Обновляем статус заказа
        conn = sqlite3.connect("amvera_bot.db")
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE orders SET status = 'paid' WHERE order_id = ?",
            (order_id,)
        )
        conn.commit()
        conn.close()
        
        # Уведомляем админа
        try:
            await context.bot.send_message(
                ADMIN_ID,
                f"💰 Новая оплата #{order_id}\n"
                f"👤 Пользователь: {user_id}"
            )
        except:
            pass
        
        await query.edit_message_text(
            f"✅ Оплата подтверждена #{order_id}\n\n"
            f"Ожидайте зачисления в течение 15 минут.\n"
            f"По вопросам: @iris_support",
            reply_markup=back_button()
        )

async def process_order(user_id: int, query, action: str, amount: int):
    """Обработка заказа"""
    # Проверка лимитов
    if amount < MIN_STARS or amount > MAX_STARS:
        await query.edit_message_text(
            f"Лимит: {MIN_STARS}-{MAX_STARS} звезд",
            reply_markup=back_button()
        )
        return
    
    # Для продажи проверяем наличие
    if action == "sell":
        user_data = db.get_user(user_id)
        if user_data["stars"] < amount:
            await query.edit_message_text(
                f"Недостаточно звезд!\nДоступно: {user_data['stars']}",
                reply_markup=back_button()
            )
            return
    
    # Расчет суммы
    price = STAR_PRICE_BUY if action == "buy" else STAR_PRICE_SELL
    total = amount * price
    
    # Создаем заказ
    order_id = f"{action}_{user_id}_{int(datetime.now().timestamp())}"
    db.create_order(order_id, user_id, f"{action}_stars", amount, total)
    
    # Показываем реквизиты
    text = (
        f"✅ Заказ #{order_id}\n\n"
        f"Количество: {amount} ⭐\n"
        f"Сумма: {total:.1f}₽\n\n"
        f"Выберите способ оплаты:"
    )
    
    await query.edit_message_text(text, reply_markup=payment_buttons(order_id))

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    # Проверяем, не вводим ли мы количество
    if 'action' in context.user_data and text.isdigit():
        action = context.user_data.pop('action', None)
        amount = int(text)
        
        if MIN_STARS <= amount <= MAX_STARS:
            # Создаем временный query объект
            class MockQuery:
                def __init__(self, user_id, chat_id):
                    self.from_user = type('obj', (object,), {'id': user_id})()
                    self.message = type('obj', (object,), {'chat': type('obj', (object,), {'id': chat_id})()})()
            
            mock_query = MockQuery(user_id, update.message.chat_id)
            
            # Обрабатываем заказ
            await process_order(user_id, mock_query, action, amount)
            
            # Отправляем сообщение с кнопками оплаты
            price = STAR_PRICE_BUY if action == "buy" else STAR_PRICE_SELL
            total = amount * price
            order_id = f"{action}_{user_id}_{int(datetime.now().timestamp())}"
            
            response = (
                f"✅ Заказ создан!\n\n"
                f"Количество: {amount} ⭐\n"
                f"Сумма: {total:.1f}₽\n\n"
                f"Выберите способ оплаты:"
            )
            
            await update.message.reply_text(response, reply_markup=payment_buttons(order_id))
        else:
            await update.message.reply_text(f"Лимит: {MIN_STARS}-{MAX_STARS} звезд")
    
    # Обычное сообщение
    else:
        await update.message.reply_text(
            "Используйте кнопки меню или команды.\n"
            "Нажмите /start для начала.",
            reply_markup=main_menu()
        )

# ==================== АДМИН КОМАНДЫ ====================
async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Админ команды"""
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("Нет доступа")
        return
    
    command = update.message.text.split()
    
    if len(command) > 1:
        if command[1] == "stats":
            # Простая статистика
            conn = sqlite3.connect("amvera_bot.db")
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM users")
            users = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'paid'")
            orders = cursor.fetchone()[0]
            
            conn.close()
            
            await update.message.reply_text(
                f"📊 Статистика:\n"
                f"👥 Пользователей: {users}\n"
                f"📦 Оплаченных заказов: {orders}"
            )
        
        elif command[1] == "users":
            conn = sqlite3.connect("amvera_bot.db")
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, balance, stars FROM users ORDER BY user_id DESC LIMIT 10")
            users = cursor.fetchall()
            conn.close()
            
            text = "👥 Последние пользователи:\n"
            for user in users:
                text += f"🆔 {user[0]} | 💰 {user[1]:.1f}₽ | ⭐ {user[2]}\n"
            
            await update.message.reply_text(text)
        
        elif command[1] == "orders":
            conn = sqlite3.connect("amvera_bot.db")
            cursor = conn.cursor()
            cursor.execute("SELECT order_id, user_id, amount, total, status FROM orders ORDER BY created DESC LIMIT 10")
            orders = cursor.fetchall()
            conn.close()
            
            text = "📦 Последние заказы:\n"
            for order in orders:
                status = "✅" if order[4] == "paid" else "⏳" if order[4] == "pending" else "❌"
                text += f"{status} #{order[0]} | 👤 {order[1]} | ⭐ {order[2]} | 💰 {order[3]:.1f}₽\n"
            
            await update.message.reply_text(text)

# ==================== ЗАПУСК БОТА ====================
def main():
    """Главная функция запуска"""
    if not TELEGRAM_AVAILABLE:
        print("❌ Библиотека python-telegram-bot не доступна")
        print("Установите: pip install python-telegram-bot==20.7")
        return
    
    # Настройка логирования
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    
    # Создаем приложение
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # Запускаем бота
    print("=" * 50)
    print("🤖 БОТ ДЛЯ AMVERA ЗАПУСКАЕТСЯ")
    print(f"🔑 Токен: {BOT_TOKEN[:10]}...")
    print(f"👑 Админ: {ADMIN_ID}")
    print(f"⭐ Покупка: {STAR_PRICE_BUY}₽ | Продажа: {STAR_PRICE_SELL}₽")
    print(f"📦 Лимит: {MIN_STARS}-{MAX_STARS} звезд")
    print(f"👑 Премиум тарифов: {len(PREMIUM_PLANS)}")
    print(f"💳 Способов оплаты: {len(PAYMENT_METHODS)}")
    print("=" * 50)
    
    # Простой health check
    async def health_check():
        while True:
            await asyncio.sleep(300)  # Каждые 5 минут
            print(f"[{datetime.now()}] Бот работает... Пользователей: {len(os.listdir('.'))}")
    
    # Запускаем health check в фоне
    loop = asyncio.get_event_loop()
    loop.create_task(health_check())
    
    # Запускаем polling
    app.run_polling()

if __name__ == "__main__":
    # Проверяем и создаем БД
    if not os.path.exists("amvera_bot.db"):
        print("📦 Создаю базу данных...")
        db = SimpleDB()
        print("✅ База данных создана")
    
    # Запускаем бота
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
