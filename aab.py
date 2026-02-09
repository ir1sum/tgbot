#!/usr/bin/env python3
"""
Telegram Stars Bot - Упрощенный рабочий вариант
Гарантированные уведомления админу
"""

import logging
import sqlite3
from datetime import datetime

try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
    print("✅ Библиотеки загружены")
except ImportError:
    print("❌ Установите: pip install python-telegram-bot==20.7")
    exit()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== КОНФИГУРАЦИЯ ====================
BOT_TOKEN = "8196751032:AAGwizPBRuq_uh0zd9GQ6C2BFiseAfnp_xo"
ADMIN_ID = 741906407  # Ваш ID
SUPPORT_USERNAME = "@ir1sum"

STAR_PRICE = 1.6
MIN_STARS = 50
MAX_STARS = 5000

# База данных
DB_PATH = "bot_database.db"

# ==================== БАЗА ДАННЫХ ====================
def init_db():
    """Инициализация базы данных"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Таблица заказов
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        first_name TEXT,
        amount INTEGER,
        total REAL,
        status TEXT DEFAULT 'ожидает',
        created_at TIMESTAMP
    )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ База данных готова")

def add_order(user_id, username, first_name, amount, total):
    """Добавить новый заказ"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT INTO orders (user_id, username, first_name, amount, total, created_at)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, username, first_name, amount, total, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    
    order_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return order_id

def update_order_status(order_id, status):
    """Обновить статус заказа"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE orders SET status = ? WHERE id = ?', (status, order_id))
    conn.commit()
    conn.close()

# ==================== КЛАВИАТУРЫ ====================
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⭐ Купить звезды", callback_data="buy_stars")],
        [InlineKeyboardButton("📦 Мои заказы", callback_data="my_orders")]
    ])

def payment_keyboard(order_id):
    """Клавиатура после реквизитов"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Я ОПЛАТИЛ", callback_data=f"paid_{order_id}")],
        [InlineKeyboardButton("💬 Поддержка", url=f"https://t.me/{SUPPORT_USERNAME.replace('@', '')}")]
    ])

def admin_keyboard(order_id):
    """Клавиатура для админа"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Подтвердить оплату", callback_data=f"confirm_{order_id}")],
        [InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{order_id}")]
    ])

# ==================== СПОСОБЫ ОПЛАТЫ ====================
def get_payment_details():
    """Реквизиты для оплаты"""
    return (
        "💳 Карта РФ: 2202206713916687\n"
        "Получатель: ROMAN IVANOV\n\n"
        "🌐 USDT (TRC20): TT6QmsrMhctAabpY9Cy5eSV3L1myxNeUwF\n\n"
        "₿ Bitcoin: bc1qy9860j3zxjd3wpy6pj5tu7jpqkz84tzftq076p\n\n"
        "⚡ TON: UQA2Xxf6CL2lx2XpiDvPPHr3heCJ5o6nRNBbxytj9eFVTpXx"
    )

# ==================== ОСНОВНЫЕ ФУНКЦИИ ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    user = update.effective_user
    
    text = f"👋 Привет, {user.first_name}!\n\n"
    text += "Я бот для покупки Telegram Stars ⭐\n"
    text += f"Цена: {STAR_PRICE}₽ за 1 звезду\n\n"
    text += "Выберите действие:"
    
    await update.message.reply_text(text, reply_markup=main_menu())

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопок"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user = query.from_user
    
    print(f"DEBUG: Нажата кнопка {data} пользователем {user.id}")
    
    # Купить звезды
    if data == "buy_stars":
        await query.edit_message_text(
            f"⭐ Купить звезды\n\n"
            f"Цена: {STAR_PRICE}₽ за 1 звезду\n"
            f"Введите количество от {MIN_STARS} до {MAX_STARS}:"
        )
        context.user_data['waiting_amount'] = True
    
    # Пользователь нажал "Я ОПЛАТИЛ"
    elif data.startswith("paid_"):
        order_id = int(data.replace("paid_", ""))
        
        # ⚡ ОТПРАВКА УВЕДОМЛЕНИЯ АДМИНУ
        try:
            admin_text = (
                f"🚨 ПОЛЬЗОВАТЕЛЬ НАЖАЛ 'Я ОПЛАТИЛ'!\n\n"
                f"🆔 Заказ: #{order_id}\n"
                f"👤 Пользователь: {user.first_name or 'Без имени'}\n"
                f"📛 @{user.username or 'нет юзернейма'}\n"
                f"🆔 ID: {user.id}\n"
                f"⏰ Время: {datetime.now().strftime('%H:%M:%S')}\n\n"
                f"Проверьте оплату и нажмите кнопку ниже:"
            )
            
            # Отправляем админу
            await query.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_text,
                reply_markup=admin_keyboard(order_id)
            )
            print(f"DEBUG: Уведомление отправлено админу {ADMIN_ID}")
            
        except Exception as e:
            print(f"ERROR: Ошибка отправки админу: {e}")
        
        # Ответ пользователю
        await query.edit_message_text(
            "✅ Спасибо! Мы получили ваше уведомление.\n"
            "⏳ Админ проверяет оплату, это займет 1-15 минут.\n\n"
            "📞 По вопросам: @ir1sum"
        )
    
    # Админ подтверждает оплату
    elif data.startswith("confirm_"):
        if user.id != ADMIN_ID:
            await query.edit_message_text("⛔ Вы не администратор")
            return
        
        order_id = int(data.replace("confirm_", ""))
        
        # Уведомляем пользователя
        try:
            await query.bot.send_message(
                chat_id=user.id,
                text=f"✅ Ваш заказ #{order_id} подтвержден! Товар будет отправлен в ближайшее время."
            )
        except:
            pass
        
        await query.edit_message_text(f"✅ Заказ #{order_id} подтвержден")
    
    # Админ отклоняет
    elif data.startswith("reject_"):
        if user.id != ADMIN_ID:
            await query.edit_message_text("⛔ Вы не администратор")
            return
        
        order_id = int(data.replace("reject_", ""))
        
        # Уведомляем пользователя
        try:
            await query.bot.send_message(
                chat_id=user.id,
                text=f"❌ По заказу #{order_id} оплата не найдена. Свяжитесь с поддержкой: @ir1sum"
            )
        except:
            pass
        
        await query.edit_message_text(f"❌ Заказ #{order_id} отклонен")
    
    # Мои заказы
    elif data == "my_orders":
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT id, amount, total, status, created_at FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT 5', (user.id,))
        orders = cursor.fetchall()
        conn.close()
        
        if orders:
            text = "📦 Ваши заказы:\n\n"
            for order in orders:
                order_id, amount, total, status, created_at = order
                status_icon = "✅" if status == "подтвержден" else "⏳" if status == "ожидает" else "❌"
                text += f"{status_icon} Заказ #{order_id}\n"
                text += f"   ⭐ {amount} звезд\n"
                text += f"   💰 {total}₽\n"
                text += f"   📅 {created_at[:16]}\n\n"
        else:
            text = "📦 У вас пока нет заказов"
        
        await query.edit_message_text(text, reply_markup=main_menu())

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик сообщений"""
    user = update.effective_user
    text = update.message.text.strip()
    
    print(f"DEBUG: Сообщение от {user.id}: {text}")
    
    # Если пользователь вводит количество звезд
    if context.user_data.get('waiting_amount') and text.isdigit():
        amount = int(text)
        
        if MIN_STARS <= amount <= MAX_STARS:
            total = amount * STAR_PRICE
            
            # Создаем заказ в базе
            order_id = add_order(
                user_id=user.id,
                username=user.username,
                first_name=user.first_name,
                amount=amount,
                total=total
            )
            
            # Показываем реквизиты
            payment_text = (
                f"✅ Заказ #{order_id} создан!\n\n"
                f"⭐ {amount} звезд\n"
                f"💰 {total:.2f}₽\n\n"
                f"💳 Реквизиты для оплаты:\n"
                f"{get_payment_details()}\n\n"
                f"📌 После оплаты нажмите кнопку ниже ⬇️"
            )
            
            # ⚡ УВЕДОМЛЕНИЕ АДМИНУ О НОВОМ ЗАКАЗЕ
            try:
                new_order_text = (
                    f"🆕 НОВЫЙ ЗАКАЗ #{order_id}\n\n"
                    f"👤 Пользователь: {user.first_name or 'Без имени'}\n"
                    f"📛 @{user.username or 'нет юзернейма'}\n"
                    f"🆔 ID: {user.id}\n"
                    f"⭐ {amount} звезд\n"
                    f"💰 {total:.2f}₽\n"
                    f"⏰ {datetime.now().strftime('%H:%M:%S')}"
                )
                
                await update.message.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=new_order_text
                )
                print(f"DEBUG: Уведомление о новом заказе отправлено админу")
                
            except Exception as e:
                print(f"ERROR: Ошибка отправки нового заказа админу: {e}")
            
            await update.message.reply_text(
                payment_text,
                reply_markup=payment_keyboard(order_id)
            )
        else:
            await update.message.reply_text(
                f"❌ Введите число от {MIN_STARS} до {MAX_STARS}"
            )
        
        context.user_data.pop('waiting_amount', None)
        return
    
    # Админские команды
    if user.id == ADMIN_ID:
        if text.startswith("/sendall "):
            message = text.replace("/sendall ", "", 1)
            await update.message.reply_text(f"📢 Рассылка: {message}")
            return
    
    # Любое другое сообщение
    await update.message.reply_text(
        "Выберите действие:",
        reply_markup=main_menu()
    )

# ==================== ЗАПУСК ====================
def main():
    """Запуск бота"""
    print("=" * 60)
    print("🤖 ЗАПУСК ПРОСТОГО БОТА")
    print(f"🔑 Токен: {BOT_TOKEN[:12]}...")
    print(f"👑 Админ ID: {ADMIN_ID}")
    print("=" * 60)
    print("\n🔔 ВАЖНО:")
    print("1. Бот будет отправлять уведомления на ваш ID")
    print("2. Проверьте, что ваш ID правильный:", ADMIN_ID)
    print("3. Когда пользователь нажмет 'Я ОПЛАТИЛ', вы получите уведомление")
    print("=" * 60)
    
    # Инициализация базы
    init_db()
    
    # Создание приложения
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("\n🔄 Бот запускается...")
    print("📱 Напишите боту /start в Telegram")
    print("=" * 60)
    
    try:
        app.run_polling(
            poll_interval=1.0,
            timeout=30,
            drop_pending_updates=True
        )
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    main()
