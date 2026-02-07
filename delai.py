#!/usr/bin/env python3
"""
Telegram Stars Bot - Упрощенная версия
Без требования комментария к платежу
"""

import os
import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Optional
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
        "details": "2202206713916687\nПолучатель: ROMAN IVANOV",
        "instruction": "Просто переведите указанную сумму"  # УПРОЩЕННАЯ ИНСТРУКЦИЯ
    },
    "usdt": {
        "name": "💎 USDT (TRC20)", 
        "details": "TT6QmsrMhctAabpY9Cy5eSV3L1myxNeUwF",
        "instruction": "Отправьте USDT на указанный адрес"
    },
    "btc": {
        "name": "₿ Bitcoin", 
        "details": "bc1qy9860j3zxjd3wpy6pj5tu7jpqkz84tzftq076p",
        "instruction": "Отправьте BTC на указанный адрес"
    },
    "ton": {
        "name": "⚡ TON", 
        "details": "UQA2Xxf6CL2lx2XpiDvPPHr3heCJ5o6nRNBbxytj9eFVTpXx",
        "instruction": "Отправьте TON на указанный адрес"
    }
}

# ==================== ПЕРСИСТЕНТНАЯ БАЗА ДАННЫХ ====================
class PersistentDatabase:
    def __init__(self):
        # Создаем папку /data если ее нет
        self.data_dir = "/data"
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir, exist_ok=True)
            print(f"📁 Создана папка для данных: {self.data_dir}")
        
        # Путь к базе данных в /data
        self.db_path = os.path.join(self.data_dir, "telegram_bot.db")
        print(f"📊 База данных: {self.db_path}")
        
        self.conn = None
        self.cursor = None
        self._init_db()
    
    def _init_db(self):
        """Инициализация базы данных"""
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.cursor = self.conn.cursor()
            
            # Пользователи
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    stars INTEGER DEFAULT 0,
                    created TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Заказы
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    username TEXT,
                    type TEXT,
                    amount INTEGER,
                    total REAL,
                    status TEXT DEFAULT 'pending',
                    payment_method TEXT,
                    created TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            self.conn.commit()
            print("✅ База данных инициализирована")
            
        except Exception as e:
            print(f"❌ Ошибка инициализации БД: {e}")
            self.db_path = "telegram_bot.db"
            print(f"⚠️  Использую локальную БД: {self.db_path}")
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.cursor = self.conn.cursor()
            self._create_tables()
    
    def _create_tables(self):
        """Создание таблиц"""
        try:
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
                    payment_method TEXT,
                    created TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            self.conn.commit()
        except Exception as e:
            print(f"❌ Ошибка создания таблиц: {e}")
    
    def _execute_query(self, query: str, params: tuple = ()):
        """Безопасное выполнение запроса"""
        try:
            if not self.conn:
                self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
                self.cursor = self.conn.cursor()
            
            result = self.cursor.execute(query, params)
            self.conn.commit()
            return result
        except sqlite3.OperationalError as e:
            print(f"⚠️  Ошибка БД: {e}")
            return None
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        try:
            self._execute_query('SELECT * FROM users WHERE user_id = ?', (user_id,))
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
        except Exception as e:
            print(f"❌ Ошибка получения пользователя: {e}")
            return None
    
    def create_user(self, user_id: int, username: str, first_name: str) -> Dict:
        try:
            self._execute_query(
                'INSERT INTO users (user_id, username, first_name) VALUES (?, ?, ?)',
                (user_id, username, first_name)
            )
            
            return {
                'user_id': user_id,
                'username': username,
                'first_name': first_name,
                'stars': 0,
                'created': datetime.now().isoformat()
            }
        except Exception as e:
            print(f"❌ Ошибка создания пользователя: {e}")
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
            return user
        return self.create_user(user_id, username, first_name)
    
    def update_stars(self, user_id: int, amount: int) -> bool:
        try:
            self._execute_query(
                'UPDATE users SET stars = stars + ? WHERE user_id = ?',
                (amount, user_id)
            )
            return True
        except Exception as e:
            print(f"❌ Ошибка обновления звезд: {e}")
            return False
    
    def create_order(self, user_id: int, username: str, order_type: str, 
                    amount: int, total: float, payment_method: str = "") -> int:
        try:
            self._execute_query(
                '''INSERT INTO orders (user_id, username, type, amount, total, payment_method) 
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (user_id, username, order_type, amount, total, payment_method)
            )
            return self.cursor.lastrowid
        except Exception as e:
            print(f"❌ Ошибка создания заказа: {e}")
            return int(datetime.now().timestamp()) % 1000000
    
    def get_order(self, order_id: int) -> Optional[Dict]:
        try:
            self._execute_query('SELECT * FROM orders WHERE id = ?', (order_id,))
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
                    'payment_method': row[7],
                    'created': row[8]
                }
            return None
        except Exception as e:
            print(f"❌ Ошибка получения заказа: {e}")
            return None
    
    def update_order_status(self, order_id: int, status: str) -> bool:
        try:
            self._execute_query(
                'UPDATE orders SET status = ? WHERE id = ?',
                (status, order_id)
            )
            return True
        except Exception as e:
            print(f"❌ Ошибка обновления статуса заказа: {e}")
            return False
    
    def get_all_users(self) -> List[Dict]:
        try:
            self._execute_query('SELECT user_id, username, first_name, stars FROM users')
            rows = self.cursor.fetchall()
            return [{'user_id': r[0], 'username': r[1], 'first_name': r[2], 'stars': r[3]} for r in rows]
        except Exception as e:
            print(f"❌ Ошибка получения пользователей: {e}")
            return []
    
    def get_user_count(self) -> int:
        try:
            self._execute_query('SELECT COUNT(*) FROM users')
            return self.cursor.fetchone()[0] or 0
        except Exception as e:
            print(f"❌ Ошибка подсчета пользователей: {e}")
            return 0
    
    def close(self):
        """Корректное закрытие соединения с БД"""
        try:
            if self.conn:
                self.conn.close()
        except:
            pass

# Глобальная база данных
db = PersistentDatabase()

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
            reply_mup=back_to_main(),
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
            # Создаем заказ без сохранения способа оплаты (пока)
            order_id = db.create_order(
                user_id=user.id,
                username=user.username or f"id{user.id}",
                order_type="premium",
                amount=plan["days"],
                total=plan["price"],
                payment_method=""
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
    
    # Оплата
    elif data.startswith("pay_"):
        parts = data.split("_")
        if len(parts) >= 4:
            order_type = parts[1]
            method_id = parts[2]
            order_id = int(parts[3])
            method = PAYMENT_METHODS.get(method_id)
            
            if method:
                await show_payment_details(query, order_type, order_id, method, user.id, method_id)
    
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
            
            # Создаем заказ без сохранения способа оплаты (пока)
            order_id = db.create_order(
                user_id=user.id,
                username=user.username or f"id{user.id}",
                order_type="stars",
                amount=amount,
                total=total,
                payment_method=""
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

# ==================== ОПЛАТА (УПРОЩЕННАЯ) ====================
async def show_payment_details(query, order_type: str, order_id: int, method: Dict, user_id: int, method_id: str):
    """Показать реквизиты для оплаты"""
    # Получаем детали заказа
    order = db.get_order(order_id)
    
    if not order:
        await query.answer("❌ Заказ не найден", show_alert=True)
        return
    
    if order['user_id'] != user_id:
        await query.answer("❌ Это не ваш заказ", show_alert=True)
        return
    
    # Обновляем запись о способе оплаты
    db._execute_query(
        'UPDATE orders SET payment_method = ? WHERE id = ?',
        (method_id, order_id)
    )
    
    if order_type == "stars":
        details = f"Покупка {order['amount']} звезд за {order['total']:.1f}₽"
    else:
        days = order['amount']
        price = order['total']
        details = f"Telegram Premium на {days} дней за {price}₽"
    
    # УПРОЩЕННЫЙ ТЕКСТ БЕЗ ТРЕБОВАНИЯ КОММЕНТАРИЯ
    text = (
        f"💳 *ОПЛАТА*\n\n"
        f"🏦 Способ: {method['name']}\n"
        f"📋 Заказ: #{order_id}\n"
        f"📝 Детали: {details}\n\n"
        f"📄 *Реквизиты:*\n"
        f"```\n{method['details']}\n```\n\n"
        f"📢 *Инструкция:*\n"
        f"{method.get('instruction', 'Просто переведите указанную сумму')}\n\n"
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
    
    # Определяем способ оплаты для уведомления
    payment_method = PAYMENT_METHODS.get(order.get('payment_method', ''), {}).get('name', 'Неизвестный способ')
    
    # Отправляем уведомление админу
    admin_message = (
        f"💰 *НОВАЯ ОПЛАТА*\n\n"
        f"🆔 *Заказ:* #{order_id}\n"
        f"👤 *Пользователь:*\n"
        f"   • ID: `{user.id}`\n"
        f"   • Имя: {user.first_name or 'Не указано'}\n"
        f"   • Юзернейм: @{user.username if user.username else 'отсутствует'}\n"
        f"💳 *Способ оплаты:* {payment_method}\n"
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
        print(f"❌ Ошибка отправки админу: {e}")
    
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
    
    elif text == "/admin orders":
        # Показываем последние заказы
        try:
            db._execute_query('SELECT id, user_id, username, type, amount, total, status, payment_method FROM orders ORDER BY id DESC LIMIT 10')
            rows = db.cursor.fetchall()
            
            if rows:
                text_response = "📦 *Последние заказы:*\n\n"
                for row in rows:
                    order_id, user_id, username, order_type, amount, total, status, payment_method = row
                    status_icon = "✅" if status == "paid" else "⏳" if status == "pending" else "❌"
                    payment = PAYMENT_METHODS.get(payment_method, {}).get('name', 'Неизвестно')
                    username_display = f"@{username}" if username.startswith('@') or username.startswith('id') else f"id{user_id}"
                    
                    text_response += f"{status_icon} #{order_id} | {username_display} | {order_type} | {amount} | {total}₽ | {payment}\n"
                
                await update.message.reply_text(text_response, parse_mode="Markdown")
            else:
                await update.message.reply_text("📭 Заказов пока нет")
        except Exception as e:
            print(f"❌ Ошибка получения заказов: {e}")
            await update.message.reply_text("❌ Ошибка получения заказов")

# ==================== ЗАПУСК БОТА ====================
def main():
    if not TELEGRAM_AVAILABLE:
        print("Установите python-telegram-bot==20.7")
        return
    
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 50)
    print("🤖 БОТ ЗАПУЩЕН (УПРОЩЕННАЯ ВЕРСИЯ)")
    print(f"📁 Папка данных: {db.data_dir}")
    print(f"📊 База данных: {db.db_path}")
    print(f"⭐ Цена звезд: {STAR_PRICE}₽")
    print(f"👑 Premium тарифов: {len(TELEGRAM_PREMIUM)}")
    print(f"👑 Админ ID: {ADMIN_ID}")
    print(f"📞 Поддержка: {SUPPORT_USERNAME}")
    print("=" * 50)
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Обработка завершения
    import signal
    
    def shutdown(signum, frame):
        print("\n🛑 Получен сигнал завершения...")
        db.close()
        print("✅ База данных закрыта")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    
    try:
        app.run_polling()
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен пользователем")
    finally:
        db.close()

if __name__ == "__main__":
    main()
