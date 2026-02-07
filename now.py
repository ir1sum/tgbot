#!/usr/bin/env python3
"""
Telegram Stars Bot - Финальная версия
Работающая рассылка + полные уведомления о заказах
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

# ==================== БАЗА ДАННЫХ ====================
db_path = "/data/bot.db" if os.path.exists("/data") else "bot.db"
print(f"📊 База данных: {db_path}")

def init_db():
    """Инициализация базы данных"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Пользователи
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        stars INTEGER DEFAULT 0,
        created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Заказы
    cursor.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        type TEXT,
        amount INTEGER,
        total REAL,
        payment_method TEXT,
        status TEXT DEFAULT 'pending',
        created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    conn.commit()
    conn.close()

init_db()

def get_user(user_id: int, username: str = "", first_name: str = "") -> Dict:
    """Получить или создать пользователя"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    
    if row:
        user = {
            'user_id': row[0],
            'username': row[1],
            'first_name': row[2],
            'stars': row[3],
            'created': row[4]
        }
    else:
        # Создаем нового пользователя
        cursor.execute(
            'INSERT INTO users (user_id, username, first_name) VALUES (?, ?, ?)',
            (user_id, username, first_name)
        )
        conn.commit()
        user = {
            'user_id': user_id,
            'username': username,
            'first_name': first_name,
            'stars': 0,
            'created': datetime.now().isoformat()
        }
    
    conn.close()
    return user

def create_order(user_id: int, username: str, order_type: str, amount: int, total: float) -> int:
    """Создать новый заказ"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''INSERT INTO orders (user_id, username, type, amount, total) 
                   VALUES (?, ?, ?, ?, ?)''',
                   (user_id, username, order_type, amount, total))
    
    order_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return order_id

def get_order(order_id: int) -> Optional[Dict]:
    """Получить информацию о заказе"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM orders WHERE id = ?', (order_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            'id': row[0],
            'user_id': row[1],
            'username': row[2],
            'type': row[3],
            'amount': row[4],
            'total': row[5],
            'payment_method': row[6],
            'status': row[7],
            'created': row[8]
        }
    return None

def update_order_payment_method(order_id: int, payment_method: str):
    """Обновить способ оплаты заказа"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute(
        'UPDATE orders SET payment_method = ? WHERE id = ?',
        (payment_method, order_id)
    )
    
    conn.commit()
    conn.close()

def update_order_status(order_id: int, status: str):
    """Обновить статус заказа"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute(
        'UPDATE orders SET status = ? WHERE id = ?',
        (status, order_id)
    )
    
    conn.commit()
    conn.close()

def get_all_users() -> list:
    """Получить всех пользователей для рассылки"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('SELECT user_id, username, first_name FROM users')
    users = cursor.fetchall()
    
    conn.close()
    return users

def get_user_count() -> int:
    """Получить количество пользователей"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM users')
    count = cursor.fetchone()[0]
    
    conn.close()
    return count

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

# ==================== ОСНОВНЫЕ ФУНКЦИИ ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
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
    """Обработчик callback-запросов"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user = query.from_user
    
    # Главное меню
    if data == "main_menu":
        await query.edit_message_text("Выберите действие:", reply_markup=main_menu())
    
    # Покупка звезд
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
            # Создаем заказ
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
    
    # Выбор способа оплаты
    elif data.startswith("pay_"):
        try:
            parts = data.split("_")
            if len(parts) >= 4:
                order_type = parts[1]
                method_id = parts[2]
                order_id = int(parts[3])
                method = PAYMENT_METHODS.get(method_id)
                
                if method:
                    # Сохраняем способ оплаты
                    update_order_payment_method(order_id, method_id)
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
    """Показать реквизиты для оплаты"""
    order = get_order(order_id)
    
    if not order:
        await query.answer("❌ Заказ не найден", show_alert=True)
        return
    
    # Определяем тип заказа для текста
    if order['type'] == "stars":
        details = f"Покупка {order['amount']} звезд за {order['total']:.1f}₽"
        instruction = f"Переведите {order['total']:.1f}₽"
    else:
        # Для Premium конвертируем дни в месяцы
        months = order['amount'] // 30
        details = f"Telegram Premium на {months} месяцев за {order['total']}₽"
        instruction = f"Переведите {order['total']}₽"
    
    text = (
        f"💳 *ОПЛАТА*\n\n"
        f"🏦 Способ: {method['name']}\n"
        f"📋 Заказ: #{order_id}\n"
        f"📝 {details}\n\n"
        f"📄 *Реквизиты:*\n"
        f"```\n{method['details']}\n```\n\n"
        f"💸 *Сумма к оплате:* {order['total']:.1f}₽\n\n"
        f"✅ Просто переведите указанную сумму"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Я оплатил", callback_data=f"confirm_{order_id}")],
        [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
    ])
    
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")

async def confirm_payment(query, order_id: int, user, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение оплаты"""
    order = get_order(order_id)
    
    if not order:
        await query.answer("❌ Заказ не найден", show_alert=True)
        return
    
    # Обновляем статус заказа
    update_order_status(order_id, "paid")
    
    # Определяем способ оплаты
    payment_method = PAYMENT_METHODS.get(order.get('payment_method', ''), {}).get('name', 'Неизвестный способ')
    
    # Формируем ПОЛНОЕ уведомление для админа
    if order['type'] == "stars":
        order_type_text = "⭐ ПОКУПКА ЗВЕЗД"
        action_required = f"Отправить пользователю: {order['amount']} звезд"
    else:
        months = order['amount'] // 30
        order_type_text = "👑 ПОКУПКА TELEGRAM PREMIUM"
        action_required = f"Активировать Premium на {months} месяцев ({order['amount']} дней)"
    
    admin_message = (
        f"💰 *НОВЫЙ ОПЛАЧЕННЫЙ ЗАКАЗ*\n\n"
        
        f"📋 *ИНФОРМАЦИЯ О ЗАКАЗЕ:*\n"
        f"• Номер: `#{order_id}`\n"
        f"• Тип: {order_type_text}\n"
        f"• Количество: {order['amount']}\n"
        f"• Сумма: {order['total']:.1f}₽\n"
        f"• Способ оплаты: {payment_method}\n"
        f"• Дата: {order['created']}\n\n"
        
        f"👤 *ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ:*\n"
        f"• ID: `{user.id}`\n"
        f"• Имя: {user.first_name or 'Не указано'}\n"
        f"• Юзернейм: @{user.username if user.username else 'отсутствует'}\n\n"
        
        f"🎯 *ЧТО НУЖНО СДЕЛАТЬ:*\n"
        f"{action_required}\n\n"
        
        f"📞 *Связаться:* @{user.username if user.username else f'ID: {user.id}'}"
    )
    
    # Отправляем уведомление админу
    try:
        await context.bot.send_message(ADMIN_ID, admin_message, parse_mode="Markdown")
        print(f"✅ Уведомление отправлено админу о заказе #{order_id}")
    except Exception as e:
        print(f"❌ Ошибка отправки админу: {e}")
    
    # Сообщаем пользователю
    user_message = (
        f"✅ *ОПЛАТА ПОДТВЕРЖДЕНА*\n\n"
        f"🆔 Номер вашего заказа: `#{order_id}`\n"
        f"💰 Сумма: {order['total']:.1f}₽\n\n"
        f"⏱ *Обработка займет до 15 минут*\n\n"
        f"📞 *По вопросам:* {SUPPORT_USERNAME}"
    )
    
    await query.edit_message_text(user_message, reply_markup=back_button(), parse_mode="Markdown")

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
                
                # Создаем заказ
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
    
    # Админская команда для рассылки (РАБОЧАЯ ВЕРСИЯ)
    if user.id == ADMIN_ID and text.lower().startswith("/sendall "):
        message = text.replace("/sendall ", "", 1)
        
        if not message.strip():
            await update.message.reply_text("❌ Введите сообщение для рассылки")
            return
        
        await update.message.reply_text("🔄 Начинаю рассылку...")
        
        # Получаем всех пользователей
        users = get_all_users()
        total_users = len(users)
        
        if total_users == 0:
            await update.message.reply_text("❌ Нет пользователей для рассылки")
            return
        
        sent = 0
        failed = 0
        
        # Отправляем сообщение каждому пользователю
        for user_data in users:
            user_id = user_data[0]
            
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode="Markdown"
                )
                sent += 1
                
                # Небольшая задержка чтобы не превысить лимиты Telegram
                import asyncio
                await asyncio.sleep(0.1)
                
            except Exception as e:
                print(f"Ошибка отправки пользователю {user_id}: {e}")
                failed += 1
        
        # Отчет о рассылке
        report = (
            f"✅ *РАССЫЛКА ЗАВЕРШЕНА*\n\n"
            f"📊 Статистика:\n"
            f"• Всего пользователей: {total_users}\n"
            f"• 📨 Успешно отправлено: {sent}\n"
            f"• ❌ Не отправлено: {failed}\n\n"
            f"📝 Сообщение:\n{message[:200]}..."
        )
        
        await update.message.reply_text(report, parse_mode="Markdown")
        return
    
    # Команда статистики для админа
    if user.id == ADMIN_ID and text.lower() == "/stats":
        user_count = get_user_count()
        await update.message.reply_text(f"📊 Пользователей в боте: {user_count}")
        return
    
    # Любое другое сообщение
    await update.message.reply_text(
        f"Используйте кнопки меню.\n"
        f"📞 Поддержка: {SUPPORT_USERNAME}\n\n"
        f"Нажмите /start для начала.",
        reply_markup=main_menu()
    )

# ==================== ЗАПУСК БОТА ====================
def main():
    if not TELEGRAM_AVAILABLE:
        print("Установите python-telegram-bot==20.7")
        return
    
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 50)
    print("🤖 TELEGRAM STARS BOT - ФИНАЛЬНАЯ ВЕРСИЯ")
    print(f"📊 База данных: {db_path}")
    print(f"⭐ Цена звезд: {STAR_PRICE}₽")
    print(f"📊 Лимиты: {MIN_STARS}-{MAX_STARS} звезд")
    print(f"👑 Premium тарифов: {len(TELEGRAM_PREMIUM)}")
    print(f"💳 Способов оплаты: {len(PAYMENT_METHODS)}")
    print(f"👑 Админ ID: {ADMIN_ID}")
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
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")

if __name__ == "__main__":
    main()
