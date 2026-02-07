#!/usr/bin/env python3
"""
Telegram Stars Bot - Исправленная версия
"""

import os
import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Optional

try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
    TELEGRAM_AVAILABLE = True
except ImportError:
    print("Установите: pip install python-telegram-bot==20.7")
    TELEGRAM_AVAILABLE = False

# ==================== КОНФИГУРАЦИЯ ====================
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN", "8196751032:AAGwizPBRuq_uh0zd9GQ6C2BFiseAfnp_xo")
ADMIN_ID = 741906407
SUPPORT_USERNAME = "@ir1sum"  # ОБНОВЛЕННЫЙ ЮЗЕРНЕЙМ ПОДДЕРЖКИ

# Цена покупки звезд
STAR_PRICE = 1.6
MIN_STARS = 50
MAX_STARS = 5000

# Telegram Premium тарифы
TELEGRAM_PREMIUM = {
    "3m": {"name": "3 месяца Premium", "price": 1099, "days": 90, "emoji": "🔵"},
    "6m": {"name": "6 месяцев Premium", "price": 1399, "days": 180, "emoji": "🟣"},
    "12m": {"name": "12 месяцев Premium", "price": 2499, "days": 365, "emoji": "🟠"}
}

# Способы оплаты
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

# ==================== БАЗА ДАННЫХ ====================
class Database:
    def __init__(self):
        self.conn = sqlite3.connect("bot.db", check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._init_db()
    
    def _init_db(self):
        """Создаем таблицы"""
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                stars INTEGER DEFAULT 0,
                created TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                type TEXT,
                amount INTEGER,
                total REAL,
                status TEXT DEFAULT 'pending',
                created TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.commit()
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        self.cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        row = self.cursor.fetchone()
        
        if row:
            return {
                'user_id': row[0],
                'username': row[1],
                'first_name': row[2],
                'stars': row[3],
                'created': row[4]
            }
        return None
    
    def create_user(self, user_id: int, username: str, first_name: str) -> Dict:
        self.cursor.execute(
            'INSERT INTO users (user_id, username, first_name) VALUES (?, ?, ?)',
            (user_id, username, first_name)
        )
        self.conn.commit()
        
        return {
            'user_id': user_id,
            'username': username,
            'first_name': first_name,
            'stars': 0,
            'created': datetime.now().isoformat()
        }
    
    def get_or_create_user(self, user_id: int, username: str, first_name: str) -> Dict:
        user = self.get_user(user_id)
        if user:
            # Обновляем username если изменился
            if username and username != user['username']:
                self.cursor.execute(
                    'UPDATE users SET username = ? WHERE user_id = ?',
                    (username, user_id)
                )
                self.conn.commit()
                user['username'] = username
            return user
        return self.create_user(user_id, username, first_name)
    
    def update_stars(self, user_id: int, amount: int) -> bool:
        try:
            self.cursor.execute(
                'UPDATE users SET stars = stars + ? WHERE user_id = ?',
                (amount, user_id)
            )
            self.conn.commit()
            return True
        except:
            return False
    
    def create_order(self, user_id: int, username: str, order_type: str, amount: int, total: float) -> int:
        self.cursor.execute(
            'INSERT INTO orders (user_id, username, type, amount, total) VALUES (?, ?, ?, ?, ?)',
            (user_id, username, order_type, amount, total)
        )
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_order(self, order_id: int) -> Optional[Dict]:
        self.cursor.execute('SELECT * FROM orders WHERE id = ?', (order_id,))
        row = self.cursor.fetchone()
        if row:
            return {
                'id': row[0],
                'user_id': row[1],
                'username': row[2],
                'type': row[3],
                'amount': row[4],
                'total': row[5],
                'status': row[6],
                'created': row[7]
            }
        return None
    
    def update_order_status(self, order_id: int, status: str) -> bool:
        try:
            self.cursor.execute(
                'UPDATE orders SET status = ? WHERE id = ?',
                (status, order_id)
            )
            self.conn.commit()
            return True
        except:
            return False
    
    def get_all_users(self) -> List[Dict]:
        self.cursor.execute('SELECT user_id, username, first_name, stars FROM users')
        rows = self.cursor.fetchall()
        return [{'user_id': r[0], 'username': r[1], 'first_name': r[2], 'stars': r[3]} for r in rows]
    
    def get_user_count(self) -> int:
        self.cursor.execute('SELECT COUNT(*) FROM users')
        return self.cursor.fetchone()[0]

db = Database()

# ==================== КЛАВИАТУРЫ ====================
def main_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("⭐ Купить звезды", callback_data="buy_stars")],
        [InlineKeyboardButton("👑 Telegram Premium", callback_data="premium")],
        [InlineKeyboardButton("📊 Мой профиль", callback_data="profile")],
    ]
    return InlineKeyboardMarkup(keyboard)

def back_to_main() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 В главное меню", callback_data="main")]])

def premium_menu() -> InlineKeyboardMarkup:
    keyboard = []
    for plan_id, plan in TELEGRAM_PREMIUM.items():
        text = f"{plan['emoji']} {plan['name']} - {plan['price']}₽"
        keyboard.append([InlineKeyboardButton(text, callback_data=f"premium_{plan_id}")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="main")])
    return InlineKeyboardMarkup(keyboard)

def payment_menu(order_type: str, order_id: int) -> InlineKeyboardMarkup:
    keyboard = []
    for method_id, method in PAYMENT_METHODS.items():
        callback = f"pay_{order_type}_{method_id}_{order_id}"
        keyboard.append([InlineKeyboardButton(method["name"], callback_data=callback)])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="main")])
    return InlineKeyboardMarkup(keyboard)

# ==================== ОСНОВНЫЕ ФУНКЦИИ ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    user = update.effective_user
    user_data = db.get_or_create_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name
    )
    
    text = (
        f"👋 Привет, {user.first_name}!\n\n"
        f"⭐ *Купить Telegram Stars*\n"
        f"💎 Цена: {STAR_PRICE}₽ за 1 звезду\n"
        f"📊 От {MIN_STARS} до {MAX_STARS} звезд\n\n"
        f"👑 *Telegram Premium* тарифы\n\n"
        f"Выберите действие:"
    )
    
    await update.message.reply_text(text, reply_markup=main_menu(), parse_mode="Markdown")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопок"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user = query.from_user
    
    # Обновляем данные пользователя
    db.get_or_create_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name
    )
    
    # Главное меню
    if data == "main":
        await query.edit_message_text("Выберите действие:", reply_markup=main_menu())
    
    # Покупка звезд
    elif data == "buy_stars":
        await query.edit_message_text(
            f"⭐ *ПОКУПКА ЗВЕЗД*\n\n"
            f"Введите количество звезд от {MIN_STARS} до {MAX_STARS}:\n\n"
            f"Цена: {STAR_PRICE}₽ за 1 звезду\n"
            f"Пример: 100 звезд = {100 * STAR_PRICE}₽",
            reply_markup=back_to_main(),
            parse_mode="Markdown"
        )
        context.user_data['awaiting_stars'] = True
    
    # Telegram Premium
    elif data == "premium":
        text = "👑 *TELEGRAM PREMIUM*\n\nВыберите тариф:"
        await query.edit_message_text(text, reply_markup=premium_menu(), parse_mode="Markdown")
    
    # Выбор тарифа Premium
    elif data.startswith("premium_"):
        plan_id = data.replace("premium_", "")
        plan = TELEGRAM_PREMIUM.get(plan_id)
        
        if plan:
            # Создаем заказ с username
            order_id = db.create_order(
                user_id=user.id,
                username=user.username or f"id{user.id}",
                order_type="premium",
                amount=plan["days"],
                total=plan["price"]
            )
            
            text = (
                f"👑 *{plan['name']}*\n\n"
                f"💰 Стоимость: {plan['price']}₽\n"
                f"⏱ Срок: {plan['days']} дней\n\n"
                f"Выберите способ оплаты:"
            )
            
            await query.edit_message_text(
                text,
                reply_markup=payment_menu("premium", order_id),
                parse_mode="Markdown"
            )
    
    # Профиль
    elif data == "profile":
        user_data = db.get_user(user.id) or {}
        
        text = (
            f"📊 *ПРОФИЛЬ*\n\n"
            f"🆔 ID: {user.id}\n"
            f"👤 Имя: {user.first_name or 'Не указано'}\n"
            f"📛 Юзернейм: @{user.username if user.username else 'отсутствует'}\n"
            f"⭐ Звезд: {user_data.get('stars', 0)}\n\n"
            f"Выберите действие:"
        )
        
        await query.edit_message_text(text, reply_markup=main_menu(), parse_mode="Markdown")
    
    # Оплата (ИСПРАВЛЕНО)
    elif data.startswith("pay_"):
        parts = data.split("_")
        if len(parts) >= 4:
            order_type = parts[1]
            method_id = parts[2]
            order_id = int(parts[3])
            method = PAYMENT_METHODS.get(method_id)
            
            if method:
                await show_payment_details(query, order_type, order_id, method, user.id)
    
    # Подтверждение оплаты
    elif data.startswith("confirm_"):
        try:
            order_id = int(data.replace("confirm_", ""))
            await confirm_payment(query, order_id, user, context)
        except ValueError:
            await query.answer("❌ Ошибка в номере заказа", show_alert=True)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений"""
    user = update.effective_user
    
    # Обновляем данные пользователя
    db.get_or_create_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name
    )
    
    text = update.message.text.strip()
    
    # Ожидаем количество звезд
    if context.user_data.get('awaiting_stars') and text.isdigit():
        amount = int(text)
        
        if MIN_STARS <= amount <= MAX_STARS:
            total = amount * STAR_PRICE
            
            # Создаем заказ с username
            order_id = db.create_order(
                user_id=user.id,
                username=user.username or f"id{user.id}",
                order_type="stars",
                amount=amount,
                total=total
            )
            
            # Показываем реквизиты
            response = (
                f"✅ *ЗАКАЗ #{order_id}*\n\n"
                f"Количество: {amount} звезд\n"
                f"Сумма: {total:.1f}₽\n\n"
                f"Выберите способ оплаты:"
            )
            
            await update.message.reply_text(
                response,
                reply_markup=payment_menu("stars", order_id),
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                f"❌ Введите число от {MIN_STARS} до {MAX_STARS}",
                reply_markup=back_to_main()
            )
        
        context.user_data.pop('awaiting_stars', None)
    
    # Проверяем админские команды
    elif text.startswith("/admin") and user.id == ADMIN_ID:
        await handle_admin_command(update, context, text)
    
    else:
        await update.message.reply_text(
            f"Используйте кнопки меню для навигации.\n"
            f"📞 Поддержка: {SUPPORT_USERNAME}\n\n"
            f"Нажмите /start для начала.",
            reply_markup=main_menu()
        )

# ==================== ОПЛАТА ====================
async def show_payment_details(query, order_type: str, order_id: int, method: Dict, user_id: int):
    """Показать реквизиты для оплаты"""
    # Получаем детали заказа
    order = db.get_order(order_id)
    
    if not order:
        await query.answer("❌ Заказ не найден", show_alert=True)
        return
    
    if order_type == "stars":
        details = f"Покупка {order['amount']} звезд за {order['total']:.1f}₽"
    else:
        days = order['amount']
        price = order['total']
        details = f"Telegram Premium на {days} дней за {price}₽"
    
    text = (
        f"💳 *ОПЛАТА*\n\n"
        f"🏦 Способ: {method['name']}\n"
        f"📋 Заказ: #{order_id}\n"
        f"📝 Детали: {details}\n\n"
        f"📄 *Реквизиты:*\n"
        f"```\n{method['details']}\n```\n\n"
        f"🔢 *В комментарии укажите:*\n"
        f"`{order_id}`\n\n"
        f"✅ После оплаты нажмите кнопку ниже"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Я оплатил", callback_data=f"confirm_{order_id}")],
        [InlineKeyboardButton("🔙 Назад", callback_data="main")]
    ])
    
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

async def confirm_payment(query, order_id: int, user, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение оплаты"""
    order = db.get_order(order_id)
    
    if not order:
        await query.answer("❌ Заказ не найден", show_alert=True)
        return
    
    if order['user_id'] != user.id:
        await query.answer("❌ Это не ваш заказ", show_alert=True)
        return
    
    # Обновляем статус заказа
    db.update_order_status(order_id, "paid")
    
    # Отправляем уведомление админу С ЮЗЕРНЕЙМОМ
    admin_message = (
        f"💰 *НОВАЯ ОПЛАТА*\n\n"
        f"🆔 *Заказ:* #{order_id}\n"
        f"👤 *Пользователь:*\n"
        f"   • ID: `{user.id}`\n"
        f"   • Имя: {user.first_name or 'Не указано'}\n"
        f"   • Юзернейм: @{user.username if user.username else 'отсутствует'}\n"
        f"📦 *Тип:* {'звезды' if order['type'] == 'stars' else 'Telegram Premium'}\n"
        f"⭐ *Количество:* {order['amount']}\n"
        f"💰 *Сумма:* {order['total']:.1f}₽\n\n"
        f"✅ Требует проверки"
    )
    
    try:
        await context.bot.send_message(
            ADMIN_ID,
            admin_message,
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"Ошибка отправки админу: {e}")
    
    # Сообщаем пользователю
    text = (
        f"✅ *ОПЛАТА ПОДТВЕРЖДЕНА*\n\n"
        f"🆔 Заказ: `{order_id}`\n"
        f"💰 Сумма: {order['total']:.1f}₽\n\n"
        f"⏱ *Обработка займет до 15 минут*\n\n"
        f"📞 *По вопросам:* {SUPPORT_USERNAME}"
    )
    
    await query.edit_message_text(text, reply_markup=back_to_main(), parse_mode="Markdown")

# ==================== АДМИН-РАССЫЛКА ====================
async def handle_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Обработка админских команд"""
    parts = text.split(maxsplit=2)
    
    if len(parts) == 3 and parts[1] == "broadcast":
        message = parts[2]
        users = db.get_all_users()
        
        sent = 0
        failed = 0
        
        for user in users:
            try:
                await context.bot.send_message(
                    user['user_id'],
                    message,
                    parse_mode="Markdown"
                )
                sent += 1
            except:
                failed += 1
        
        await update.message.reply_text(
            f"✅ Рассылка завершена:\n"
            f"📨 Отправлено: {sent}\n"
            f"❌ Не отправлено: {failed}"
        )
    
    elif text == "/admin stats":
        users_count = db.get_user_count()
        await update.message.reply_text(f"📊 Пользователей в боте: {users_count}")
    
    elif text == "/admin users":
        users = db.get_all_users()
        text_response = "👥 *Пользователи:*\n\n"
        for user in users[:20]:
            username = f"@{user['username']}" if user['username'] else f"id{user['user_id']}"
            text_response += f"🆔 {user['user_id']} | {username} | ⭐ {user['stars']}\n"
        
        if len(users) > 20:
            text_response += f"\n... и еще {len(users) - 20} пользователей"
        
        await update.message.reply_text(text_response, parse_mode="Markdown")

# ==================== ЗАПУСК БОТА ====================
def main():
    if not TELEGRAM_AVAILABLE:
        print("Установите python-telegram-bot==20.7")
        return
    
    logging.basicConfig(level=logging.INFO)
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("=" * 50)
    print("🤖 БОТ ЗАПУЩЕН")
    print(f"⭐ Цена звезд: {STAR_PRICE}₽")
    print(f"📊 Лимиты: {MIN_STARS}-{MAX_STARS} звезд")
    print(f"👑 Premium тарифов: {len(TELEGRAM_PREMIUM)}")
    print(f"👑 Админ ID: {ADMIN_ID}")
    print(f"📞 Поддержка: {SUPPORT_USERNAME}")
    print("=" * 50)
    
    app.run_polling()

if __name__ == "__main__":
    main()
