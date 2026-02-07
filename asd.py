#!/usr/bin/env python3
"""
Telegram Stars Bot - Рабочая версия
Исправлены все кнопки, одна админ-команда
"""

import os
import sqlite3
import logging
from datetime import datetime
from typing import Dict, Optional
import sys

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
SUPPORT_USERNAME = "@ir1sum"

STAR_PRICE = 1.6
MIN_STARS = 50
MAX_STARS = 5000

TELEGRAM_PREMIUM = {
    "3m": {"name": "3 месяца Premium", "price": 1099, "days": 90, "emoji": "🔵"},
    "6m": {"name": "6 месяцев Premium", "price": 1399, "days": 180, "emoji": "🟣"},
    "12m": {"name": "12 месяцев Premium", "price": 2499, "days": 365, "emoji": "🟠"}
}

PAYMENT_METHODS = {
    "card": {"name": "💳 Карта РФ", "details": "2202206713916687\nПолучатель: ROMAN IVANOV"},
    "usdt": {"name": "💎 USDT", "details": "TT6QmsrMhctAabpY9Cy5eSV3L1myxNeUwF"},
    "btc": {"name": "₿ Bitcoin", "details": "bc1qy9860j3zxjd3wpy6pj5tu7jpqkz84tzftq076p"},
    "ton": {"name": "⚡ TON", "details": "UQA2Xxf6CL2lx2XpiDvPPHr3heCJ5o6nRNBbxytj9eFVTpXx"}
}

# ==================== ПРОСТАЯ БАЗА ====================
db_path = "/data/bot.db" if os.path.exists("/data") else "bot.db"
print(f"📊 База данных: {db_path}")

def init_db():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        stars INTEGER DEFAULT 0
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        type TEXT,
        amount INTEGER,
        total REAL,
        status TEXT DEFAULT 'pending'
    )''')
    conn.commit()
    conn.close()

init_db()

def get_user(user_id: int, username: str = "", first_name: str = "") -> Dict:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    
    if row:
        user = {'user_id': row[0], 'username': row[1], 'first_name': row[2], 'stars': row[3]}
    else:
        cursor.execute('INSERT INTO users (user_id, username, first_name) VALUES (?, ?, ?)', 
                      (user_id, username, first_name))
        conn.commit()
        user = {'user_id': user_id, 'username': username, 'first_name': first_name, 'stars': 0}
    
    conn.close()
    return user

def create_order(user_id: int, username: str, order_type: str, amount: int, total: float) -> int:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO orders (user_id, username, type, amount, total) 
                   VALUES (?, ?, ?, ?, ?)''',
                   (user_id, username, order_type, amount, total))
    order_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return order_id

def update_order_status(order_id: int, status: str):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('UPDATE orders SET status = ? WHERE id = ?', (status, order_id))
    conn.commit()
    conn.close()

def get_all_user_ids():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users')
    user_ids = [row[0] for row in cursor.fetchall()]
    conn.close()
    return user_ids

# ==================== КЛАВИАТУРЫ ====================
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⭐ Купить звезды", callback_data="buy_stars")],
        [InlineKeyboardButton("👑 Telegram Premium", callback_data="premium_menu")],
        [InlineKeyboardButton("📊 Мой профиль", callback_data="profile")]
    ])

def back_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]])

def premium_menu_kb():
    buttons = []
    for plan_id, plan in TELEGRAM_PREMIUM.items():
        buttons.append([InlineKeyboardButton(
            f"{plan['emoji']} {plan['name']} - {plan['price']}₽",
            callback_data=f"premium_{plan_id}"
        )])
    buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)

def payment_menu_kb(order_type: str, order_id: int):
    buttons = []
    for method_id, method in PAYMENT_METHODS.items():
        buttons.append([InlineKeyboardButton(
            method["name"],
            callback_data=f"pay_{order_type}_{method_id}_{order_id}"
        )])
    buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)

# ==================== ОБРАБОТЧИКИ ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_user(user.id, user.username or "", user.first_name or "")
    
    text = (
        f"👋 Привет, {user.first_name or 'друг'}!\n\n"
        f"⭐ *Купить Telegram Stars*\n"
        f"💎 Цена: {STAR_PRICE}₽ за звезду\n"
        f"📊 От {MIN_STARS} до {MAX_STARS} звезд\n\n"
        f"👑 *Telegram Premium* тарифы\n\n"
        f"Выберите действие:"
    )
    
    await update.message.reply_text(text, reply_markup=main_menu(), parse_mode="Markdown")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user = query.from_user
    
    print(f"DEBUG: Callback data = {data}")  # Для отладки
    
    # Главное меню
    if data == "main_menu":
        await query.edit_message_text("Выберите действие:", reply_markup=main_menu())
    
    # Кнопка КУПИТЬ ЗВЕЗДЫ (ИСПРАВЛЕНА)
    elif data == "buy_stars":
        text = (
            f"⭐ *ПОКУПКА ЗВЕЗД*\n\n"
            f"Введите количество от {MIN_STARS} до {MAX_STARS}:\n\n"
            f"Цена: {STAR_PRICE}₽ за 1 звезду\n"
            f"Пример: 100 звезд = {100 * STAR_PRICE}₽\n\n"
            f"Просто напишите число в чат:"
        )
        await query.edit_message_text(text, reply_markup=back_button(), parse_mode="Markdown")
        context.user_data['awaiting_stars'] = True
    
    # Меню Premium
    elif data == "premium_menu":
        await query.edit_message_text("👑 *TELEGRAM PREMIUM*\n\nВыберите тариф:", 
                                     reply_markup=premium_menu_kb(), parse_mode="Markdown")
    
    # Выбор тарифа Premium
    elif data.startswith("premium_"):
        plan_id = data.replace("premium_", "")
        plan = TELEGRAM_PREMIUM.get(plan_id)
        
        if plan:
            order_id = create_order(
                user_id=user.id,
                username=user.username or f"id{user.id}",
                order_type="premium",
                amount=plan["days"],
                total=plan["price"]
            )
            
            text = f"👑 *{plan['name']}*\n\nЦена: {plan['price']}₽\n\nВыберите способ оплаты:"
            await query.edit_message_text(text, reply_markup=payment_menu_kb("premium", order_id), parse_mode="Markdown")
    
    # Профиль
    elif data == "profile":
        user_data = get_user(user.id)
        text = (
            f"📊 *ПРОФИЛЬ*\n\n"
            f"🆔 ID: {user.id}\n"
            f"👤 Имя: {user.first_name or 'Не указано'}\n"
            f"📛 Юзернейм: @{user.username if user.username else 'отсутствует'}\n"
            f"⭐ Звезд: {user_data.get('stars', 0)}\n\n"
            f"Выберите действие:"
        )
        await query.edit_message_text(text, reply_markup=main_menu(), parse_mode="Markdown")
    
    # Оплата
    elif data.startswith("pay_"):
        try:
            parts = data.split("_")
            if len(parts) >= 4:
                order_type = parts[1]
                method_id = parts[2]
                order_id = int(parts[3])
                method = PAYMENT_METHODS.get(method_id)
                
                if method:
                    await show_payment(query, order_id, method, user)
        except Exception as e:
            print(f"Ошибка обработки оплаты: {e}")
            await query.answer("❌ Ошибка", show_alert=True)
    
    # Подтверждение оплаты
    elif data.startswith("confirm_"):
        try:
            order_id = int(data.replace("confirm_", ""))
            await confirm_payment(query, order_id, user, context)
        except:
            await query.answer("❌ Ошибка", show_alert=True)

async def show_payment(query, order_id: int, method: Dict, user):
    """Показать реквизиты оплаты"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT type, amount, total FROM orders WHERE id = ?', (order_id,))
    order_data = cursor.fetchone()
    conn.close()
    
    if not order_data:
        await query.answer("❌ Заказ не найден", show_alert=True)
        return
    
    order_type, amount, total = order_data
    
    if order_type == "stars":
        details = f"Покупка {amount} звезд за {total:.1f}₽"
    else:
        details = f"Telegram Premium на {amount} дней за {total}₽"
    
    text = (
        f"💳 *ОПЛАТА*\n\n"
        f"🏦 {method['name']}\n"
        f"📋 Заказ: #{order_id}\n"
        f"📝 {details}\n\n"
        f"📄 *Реквизиты:*\n"
        f"```\n{method['details']}\n```\n\n"
        f"✅ Просто переведите указанную сумму"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Я оплатил", callback_data=f"confirm_{order_id}")],
        [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
    ])
    
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

async def confirm_payment(query, order_id: int, user, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение оплаты"""
    update_order_status(order_id, "paid")
    
    # Уведомление админу
    try:
        admin_msg = (
            f"💰 *НОВАЯ ОПЛАТА*\n\n"
            f"🆔 Заказ: #{order_id}\n"
            f"👤 Пользователь: {user.first_name or 'Без имени'}\n"
            f"📛 Юзернейм: @{user.username or 'отсутствует'}\n"
            f"🆔 ID: `{user.id}`"
        )
        await context.bot.send_message(ADMIN_ID, admin_msg, parse_mode="Markdown")
    except Exception as e:
        print(f"Ошибка уведомления админу: {e}")
    
    # Сообщение пользователю
    text = (
        f"✅ *ОПЛАТА ПОДТВЕРЖДЕНА*\n\n"
        f"🆔 Заказ: `{order_id}`\n\n"
        f"⏱ Обработка займет до 15 минут\n\n"
        f"📞 Поддержка: {SUPPORT_USERNAME}"
    )
    
    await query.edit_message_text(text, reply_markup=back_button(), parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений"""
    user = update.effective_user
    text = update.message.text.strip()
    
    # Если ожидаем количество звезд
    if context.user_data.get('awaiting_stars'):
        if text.isdigit():
            amount = int(text)
            
            if MIN_STARS <= amount <= MAX_STARS:
                total = amount * STAR_PRICE
                order_id = create_order(
                    user_id=user.id,
                    username=user.username or f"id{user.id}",
                    order_type="stars",
                    amount=amount,
                    total=total
                )
                
                response = (
                    f"✅ *ЗАКАЗ #{order_id}*\n\n"
                    f"Количество: {amount} звезд\n"
                    f"Сумма: {total:.1f}₽\n\n"
                    f"Выберите способ оплаты:"
                )
                
                await update.message.reply_text(
                    response,
                    reply_markup=payment_menu_kb("stars", order_id),
                    parse_mode="Markdown"
                )
            else:
                await update.message.reply_text(
                    f"❌ Введите число от {MIN_STARS} до {MAX_STARS}",
                    reply_markup=back_button()
                )
        else:
            await update.message.reply_text("❌ Введите число", reply_markup=back_button())
        
        context.user_data.pop('awaiting_stars', None)
        return
    
    # Админская команда для рассылки
    if user.id == ADMIN_ID and text.startswith("/sendall "):
        message = text.replace("/sendall ", "", 1)
        user_ids = get_all_user_ids()
        
        sent = 0
        failed = 0
        
        for uid in user_ids:
            try:
                await context.bot.send_message(uid, message, parse_mode="Markdown")
                sent += 1
            except:
                failed += 1
        
        await update.message.reply_text(
            f"✅ Рассылка завершена:\n"
            f"📨 Отправлено: {sent}\n"
            f"❌ Не отправлено: {failed}"
        )
        return
    
    # Любое другое сообщение
    await update.message.reply_text(
        f"Используйте кнопки меню.\n"
        f"📞 Поддержка: {SUPPORT_USERNAME}\n\n"
        f"Нажмите /start для начала.",
        reply_markup=main_menu()
    )

# ==================== ЗАПУСК ====================
def main():
    if not TELEGRAM_AVAILABLE:
        print("Установите python-telegram-bot==20.7")
        return
    
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 50)
    print("🤖 БОТ ЗАПУЩЕН (ИСПРАВЛЕННАЯ ВЕРСИЯ)")
    print(f"📊 База: {db_path}")
    print(f"⭐ Цена: {STAR_PRICE}₽ за звезду")
    print(f"👑 Premium: {len(TELEGRAM_PREMIUM)} тарифа")
    print(f"👑 Админ: {ADMIN_ID}")
    print(f"📞 Поддержка: {SUPPORT_USERNAME}")
    print("=" * 50)
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    try:
        app.run_polling()
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен")

if __name__ == "__main__":
    main()
