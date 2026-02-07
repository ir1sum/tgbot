#!/usr/bin/env python3
"""
Telegram Stars Bot - Оптимизированная версия для amvar
"""

import json
import logging
import os
import sys
import sqlite3
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Optional, List

# Минималистичный импорт для экономии памяти
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ==================== КОНФИГУРАЦИЯ ДЛЯ amvar ====================
TOKEN = "8196751032:AAGwizPBRuq_uh0zd9GQ6C2BFiseAfnp_xo"
ADMIN_ID = 741906407

# Компактные структуры данных
class MicroConfig:
    __slots__ = ('buy_price', 'sell_price', 'min_stars', 'max_stars')  # Экономия памяти
    
    def __init__(self):
        self.buy_price = 1.6
        self.sell_price = 1.0
        self.min_stars = 50
        self.max_stars = 5000

config = MicroConfig()

# ==================== УЛЬТРА-ЛЁГКАЯ БАЗА ДАННЫХ ====================
class AmvarDB:
    """База данных оптимизированная для amvar с минимальным использованием памяти"""
    
    def __init__(self, db_path: str = "amvar_bot.db"):
        self.db_path = db_path
        self.conn = None
        self._init_db()
    
    def _init_db(self):
        """Инициализация базы данных с минимальным набором таблиц"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode = WAL")  # Для лучшей производительности
        self.conn.execute("PRAGMA synchronous = NORMAL")
        self.conn.execute("PRAGMA cache_size = -2000")  # 2MB кэша
        
        # Основные таблицы
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                balance REAL DEFAULT 0.0,
                stars INTEGER DEFAULT 0,
                premium_until TEXT,
                created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                user_id INTEGER,
                order_type TEXT,
                amount INTEGER,
                total REAL,
                status TEXT DEFAULT 'pending',
                created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                key TEXT PRIMARY KEY,
                value TEXT,
                expires TIMESTAMP
            )
        """)
        
        self.conn.commit()
    
    def _clean_old_cache(self):
        """Очистка старого кэша для экономии места"""
        self.conn.execute("DELETE FROM cache WHERE expires < datetime('now')")
        self.conn.commit()
    
    def get_user(self, user_id: int) -> Dict:
        """Получение пользователя с кэшированием"""
        cursor = self.conn.execute(
            "SELECT user_id, balance, stars, premium_until FROM users WHERE user_id = ?",
            (user_id,)
        )
        row = cursor.fetchone()
        
        if row:
            return {
                "user_id": row[0],
                "balance": row[1],
                "stars": row[2],
                "premium_until": row[3]
            }
        else:
            # Создание нового пользователя
            self.conn.execute(
                "INSERT INTO users (user_id, balance, stars) VALUES (?, 0.0, 0)",
                (user_id,)
            )
            self.conn.commit()
            return {
                "user_id": user_id,
                "balance": 0.0,
                "stars": 0,
                "premium_until": None
            }
    
    def update_balance(self, user_id: int, delta: float) -> bool:
        """Атомарное обновление баланса"""
        try:
            self.conn.execute(
                "UPDATE users SET balance = balance + ?, last_active = datetime('now') WHERE user_id = ?",
                (delta, user_id)
            )
            self.conn.commit()
            return True
        except:
            return False
    
    def update_stars(self, user_id: int, delta: int) -> bool:
        """Атомарное обновление количества звезд"""
        try:
            self.conn.execute(
                "UPDATE users SET stars = stars + ?, last_active = datetime('now') WHERE user_id = ?",
                (delta, user_id)
            )
            self.conn.commit()
            return True
        except:
            return False
    
    def create_order(self, order_id: str, user_id: int, order_type: str, amount: int, total: float) -> bool:
        """Создание заказа"""
        try:
            self.conn.execute(
                """INSERT INTO orders (order_id, user_id, order_type, amount, total, status) 
                   VALUES (?, ?, ?, ?, ?, 'pending')""",
                (order_id, user_id, order_type, amount, total)
            )
            self.conn.commit()
            return True
        except:
            return False
    
    def close(self):
        """Корректное закрытие соединения"""
        if self.conn:
            self.conn.close()

# Глобальный экземпляр БД
db = AmvarDB()

# ==================== ОПТИМИЗИРОВАННЫЕ КЛАВИАТУРЫ ====================
class CompactKeyboard:
    """Генератор компактных клавиатур для экономии памяти"""
    
    @staticmethod
    def main_menu() -> InlineKeyboardMarkup:
        """Главное меню (2x3 для компактности)"""
        keyboard = [
            [InlineKeyboardButton("⭐ Купить", callback_data="buy"),
             InlineKeyboardButton("💰 Продать", callback_data="sell")],
            [InlineKeyboardButton("👑 Премиум", callback_data="premium"),
             InlineKeyboardButton("💎 Баланс", callback_data="balance")],
            [InlineKeyboardButton("📊 Профиль", callback_data="profile"),
             InlineKeyboardButton("🆘 Поддержка", callback_data="support")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def amounts_menu(action: str) -> InlineKeyboardMarkup:
        """Меню выбора количества"""
        amounts = [50, 100, 250, 500]
        rows = []
        
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
                rows.append(row)
        
        rows.append([InlineKeyboardButton("✏️ Свое", callback_data=f"custom_{action}")])
        rows.append([InlineKeyboardButton("🔙 Назад", callback_data="main")])
        
        return InlineKeyboardMarkup(rows)

# ==================== МИНИМАЛИСТИЧНЫЙ КЭШ СОСТОЯНИЙ ====================
class StateCache:
    """Кэш состояний пользователя в памяти (ограниченный размер)"""
    
    def __init__(self, max_size: int = 1000):
        self.cache = {}
        self.max_size = max_size
        self.access_order = []  # Для реализации LRU
    
    def get(self, user_id: int, default=None):
        """Получение состояния с обновлением порядка доступа"""
        if user_id in self.cache:
            self.access_order.remove(user_id)
            self.access_order.append(user_id)
            return self.cache[user_id]
        return default
    
    def set(self, user_id: int, value):
        """Установка состояния с проверкой лимита"""
        if user_id in self.cache:
            self.access_order.remove(user_id)
        elif len(self.cache) >= self.max_size:
            # Удаляем самый старый элемент
            oldest = self.access_order.pop(0)
            del self.cache[oldest]
        
        self.cache[user_id] = value
        self.access_order.append(user_id)
    
    def delete(self, user_id: int):
        """Удаление состояния"""
        if user_id in self.cache:
            del self.cache[user_id]
            self.access_order.remove(user_id)

state_cache = StateCache(max_size=500)  # Ограничение для amvar

# ==================== ОПТИМИЗИРОВАННЫЕ ОБРАБОТЧИКИ ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Минималистичная команда старта"""
    user = update.effective_user
    
    # Получаем пользователя из БД
    user_data = db.get_user(user.id)
    
    # Компактный текст
    text = (
        f"👤 {user.first_name}\n"
        f"💰 {user_data['balance']:.1f}₽ | ⭐ {user_data['stars']}\n"
        f"Купить: {config.buy_price}₽ | Продать: {config.sell_price}₽\n\n"
        f"Выберите:"
    )
    
    await update.message.reply_text(
        text,
        reply_markup=CompactKeyboard.main_menu(),
        parse_mode="Markdown"
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Упрощенный обработчик callback'ов"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    # Главное меню
    if data == "main":
        user_data = db.get_user(user_id)
        text = f"Баланс: {user_data['balance']:.1f}₽ | Звезд: {user_data['stars']}"
        await query.edit_message_text(text, reply_markup=CompactKeyboard.main_menu())
        return
    
    # Покупка/продажа
    if data in ["buy", "sell"]:
        action_text = "КУПИТЬ" if data == "buy" else "ПРОДАТЬ"
        price = config.buy_price if data == "buy" else config.sell_price
        
        text = f"{action_text} ⭐\nЦена: {price}₽/шт\nВыберите количество:"
        await query.edit_message_text(
            text,
            reply_markup=CompactKeyboard.amounts_menu(data)
        )
        state_cache.set(user_id, f"waiting_{data}")
        return
    
    # Быстрый выбор количества
    if data.startswith("amt_"):
        _, action, amount_str = data.split("_")
        amount = int(amount_str)
        
        await process_order(user_id, query.message.chat_id, action, amount)
        return
    
    # Ручной ввод
    if data.startswith("custom_"):
        action = data.replace("custom_", "")
        state_cache.set(user_id, f"waiting_{action}")
        
        await query.edit_message_text(
            f"Введите количество ⭐ для {'покупки' if action == 'buy' else 'продажи'}:\n"
            f"От {config.min_stars} до {config.max_stars}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Назад", callback_data=action)]
            ])
        )
        return
    
    # Профиль
    if data == "profile":
        user_data = db.get_user(user_id)
        
        premium_info = ""
        if user_data['premium_until']:
            until = datetime.fromisoformat(user_data['premium_until'])
            if until > datetime.now():
                days = (until - datetime.now()).days
                premium_info = f"👑 Premium: {days}д\n"
        
        text = (
            f"🆔 ID: {user_id}\n"
            f"{premium_info}"
            f"💰 Баланс: {user_data['balance']:.1f}₽\n"
            f"⭐ Звезд: {user_data['stars']}\n"
            f"🎁 Промо: IRIS666"
        )
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Назад", callback_data="main")]
            ])
        )
        return
    
    # Остальные кнопки (заглушки)
    await query.edit_message_text(
        "Функция в разработке 🔧",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Назад", callback_data="main")]
        ])
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    # Проверяем состояние пользователя
    state = state_cache.get(user_id)
    if not state or not state.startswith("waiting_"):
        return
    
    # Удаляем состояние сразу
    state_cache.delete(user_id)
    
    # Проверка на число
    if not text.isdigit():
        await update.message.reply_text("Введите число!")
        return
    
    amount = int(text)
    
    # Проверка лимитов
    if amount < config.min_stars or amount > config.max_stars:
        await update.message.reply_text(
            f"Лимит: {config.min_stars}-{config.max_stars} ⭐"
        )
        return
    
    # Определяем действие
    action = "buy" if "buy" in state else "sell"
    
    # Обрабатываем заказ
    await process_order(user_id, update.message.chat_id, action, amount)

async def process_order(user_id: int, chat_id: int, action: str, amount: int):
    """Минималистичная обработка заказа"""
    price = config.buy_price if action == "buy" else config.sell_price
    total = amount * price
    
    # Генерация ID заказа
    order_id = f"{action[:1]}{user_id % 10000}{int(datetime.now().timestamp()) % 10000}"
    
    # Создаем заказ в БД
    order_created = db.create_order(order_id, user_id, action, amount, total)
    
    if not order_created:
        await Application.builder().token(TOKEN).build().bot.send_message(
            chat_id,
            "❌ Ошибка создания заказа"
        )
        return
    
    # Текст заказа
    action_text = "покупки" if action == "buy" else "продажи"
    text = (
        f"✅ Заказ #{order_id}\n"
        f"Действие: {action_text}\n"
        f"Количество: {amount} ⭐\n"
        f"Сумма: {total:.1f}₽\n\n"
        f"Для оплаты:\n"
        f"1. Карта: 2202206713916687\n"
        f"   Получатель: ROMAN IVANOV\n"
        f"2. В комментарии укажите: {order_id}"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Я оплатил", callback_data=f"paid_{order_id}")],
        [InlineKeyboardButton("❌ Отмена", callback_data="main")]
    ])
    
    app = Application.builder().token(TOKEN).build()
    await app.bot.send_message(chat_id, text, reply_markup=keyboard)
    
    # Уведомление админу (если есть доступ)
    try:
        await app.bot.send_message(
            ADMIN_ID,
            f"🆕 #{order_id}\n"
            f"👤 {user_id}\n"
            f"⭐ {amount} ({action_text})\n"
            f"💰 {total:.1f}₽"
        )
    except:
        pass

# ==================== МОНИТОРИНГ ПАМЯТИ ДЛЯ amvar ====================
import psutil
import threading

class MemoryMonitor:
    """Мониторинг использования памяти для amvar"""
    
    def __init__(self, warning_threshold_mb: int = 50):
        self.warning_threshold = warning_threshold_mb * 1024 * 1024  # в байтах
        self.monitoring = False
    
    def get_memory_usage(self) -> float:
        """Получение текущего использования памяти процессом в MB"""
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024
    
    def cleanup_if_needed(self):
        """Очистка кэша если память на пределе"""
        memory_mb = self.get_memory_usage()
        
        if memory_mb > (self.warning_threshold / 1024 / 1024):
            # Очищаем кэш состояний
            global state_cache
            state_cache = StateCache(max_size=100)  # Уменьшаем кэш
            
            # Принудительный сбор мусора
            import gc
            gc.collect()
            
            return True
        return False
    
    def start_monitoring(self, interval_seconds: int = 60):
        """Запуск фонового мониторинга"""
        def monitor():
            self.monitoring = True
            while self.monitoring:
                if self.cleanup_if_needed():
                    logging.warning(f"Memory cleanup performed. Current: {self.get_memory_usage():.1f}MB")
                threading.Event().wait(interval_seconds)
        
        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()

# ==================== КОМПАКТНЫЙ ЗАПУСК ====================
def main():
    """Минималистичный запуск для amvar"""
    
    # Настройка компактного логгирования
    logging.basicConfig(
        level=logging.WARNING,  # Только ошибки для экономии
        format='%(levelname)s: %(message)s',
        handlers=[logging.StreamHandler()]
    )
    
    # Создание приложения
    app = Application.builder().token(TOKEN).build()
    
    # Минимальный набор обработчиков
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # Мониторинг памяти
    monitor = MemoryMonitor(warning_threshold_mb=50)
    monitor.start_monitoring()
    
    print("=" * 40)
    print(f"🤖 Бот запущен на amvar")
    print(f"📦 Память: {monitor.get_memory_usage():.1f}MB")
    print(f"💾 БД: {os.path.getsize('amvar_bot.db')/1024:.1f}KB")
    print("=" * 40)
    
    try:
        app.run_polling(
            poll_interval=1.0,  # Меньший интервал для отзывчивости
            timeout=20,
            drop_pending_updates=True  # Чистим старые апдейты
        )
    finally:
        # Корректное завершение
        db.close()
        print("Бот остановлен")

if __name__ == "__main__":
    # Проверка доступности памяти
    try:
        import psutil
        memory_info = psutil.virtual_memory()
        if memory_info.available < 100 * 1024 * 1024:  # Меньше 100MB
            print("Внимание: мало памяти на amvar!")
    except:
        pass
    
    main()
