#!/usr/bin/env python3
"""
Telegram Stars Bot - Ультра-простая рабочая версия
"""

import os
import logging
from datetime import datetime

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

# ==================== ПРОСТЫЕ КЛАВИАТУРЫ ====================
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⭐ Купить звезды", callback_data="buy")],
        [InlineKeyboardButton("👑 Premium", callback_data="premium")],
        [InlineKeyboardButton("📊 Профиль", callback_data="profile")]
    ])

def back_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="main")]])

# ==================== ОСНОВНЫЕ ФУНКЦИИ ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start - ПРОСТАЯ ВЕРСИЯ"""
    try:
        user = update.effective_user
        logger.info(f"Пользователь {user.id} запустил бота")
        
        text = f"👋 Привет, {user.first_name or 'друг'}!\n\nВыберите действие:"
        
        await update.message.reply_text(text, reply_markup=main_menu())
        logger.info("Команда /start выполнена успешно")
        
    except Exception as e:
        logger.error(f"Ошибка в /start: {e}")
        await update.message.reply_text("Ошибка. Попробуйте позже.")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик callback-запросов - ПРОСТАЯ ВЕРСИЯ"""
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
            await query.edit_message_text(text, reply_markup=back_button())
        
        elif data == "profile":
            text = f"📊 Профиль\n\n🆔 ID: {user.id}\n👤 Имя: {user.first_name or 'Не указано'}\n📛 Юзернейм: @{user.username or 'отсутствует'}"
            await query.edit_message_text(text, reply_markup=back_button())
            
    except Exception as e:
        logger.error(f"Ошибка в callback: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений - ПРОСТАЯ ВЕРСИЯ"""
    try:
        user = update.effective_user
        text = update.message.text.strip()
        
        logger.info(f"Сообщение от {user.id}: {text}")
        
        # Если пользователь вводит количество звезд
        if context.user_data.get('waiting_amount') and text.isdigit():
            amount = int(text)
            
            if MIN_STARS <= amount <= MAX_STARS:
                total = amount * STAR_PRICE
                
                # Уведомление админу
                try:
                    await context.bot.send_message(
                        ADMIN_ID,
                        f"💰 НОВЫЙ ЗАКАЗ\n\n"
                        f"👤 Пользователь: {user.first_name or 'Без имени'}\n"
                        f"📛 Юзернейм: @{user.username or 'отсутствует'}\n"
                        f"🆔 ID: {user.id}\n"
                        f"⭐ Количество: {amount} звезд\n"
                        f"💰 Сумма: {total:.1f}₽",
                        parse_mode="Markdown"
                    )
                except Exception as e:
                    logger.error(f"Ошибка уведомления админу: {e}")
                
                # Сообщение пользователю
                payment_info = (
                    f"✅ Заказ создан!\n\n"
                    f"⭐ Количество: {amount} звезд\n"
                    f"💰 Сумма: {total:.1f}₽\n\n"
                    f"💳 *Реквизиты для оплаты:*\n"
                    f"Карта: 2202206713916687\n"
                    f"Получатель: ROMAN IVANOV\n\n"
                    f"📞 После оплаты напишите: {SUPPORT_USERNAME}"
                )
                
                await update.message.reply_text(payment_info, parse_mode="Markdown")
                
            else:
                await update.message.reply_text(f"❌ Введите число от {MIN_STARS} до {MAX_STARS}")
            
            context.user_data.pop('waiting_amount', None)
            return
        
        # Админская команда для рассылки
        if user.id == ADMIN_ID and text.startswith("/sendall "):
            message = text.replace("/sendall ", "", 1)
            await update.message.reply_text(f"✅ Рассылка: {message}")
            return
        
        # Любое другое сообщение
        await update.message.reply_text(
            f"Используйте команду /start",
            reply_markup=main_menu()
        )
        
    except Exception as e:
        logger.error(f"Ошибка обработки сообщения: {e}")

# ==================== ЗАПУСК БОТА ====================
def main():
    """Запуск бота - ПРОСТАЯ ВЕРСИЯ"""
    print("=" * 50)
    print("🤖 ЗАПУСК ПРОСТОГО БОТА")
    print(f"🔑 Токен: {BOT_TOKEN[:10]}...")
    print(f"👑 Админ: {ADMIN_ID}")
    print("=" * 50)
    
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
        print("🔄 Запускаю polling...")
        app.run_polling(
            poll_interval=1.0,
            timeout=30,
            drop_pending_updates=True
        )
        
    except Exception as e:
        logger.error(f"КРИТИЧЕСКАЯ ОШИБКА: {e}")
        print(f"❌ Ошибка запуска: {e}")
        
        # Детальная диагностика
        print("\n🔍 ДИАГНОСТИКА:")
        print(f"1. Токен: {'УСТАНОВЛЕН' if BOT_TOKEN else 'ОТСУТСТВУЕТ'}")
        print(f"2. Токен начинается с: {BOT_TOKEN[:10]}")
        
        # Проверяем подключение к Telegram API
        import requests
        try:
            response = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getMe", timeout=10)
            print(f"3. Проверка API: {response.status_code}")
            if response.status_code == 200:
                print("   ✅ Подключение к Telegram API успешно")
            else:
                print(f"   ❌ Ошибка API: {response.text}")
        except Exception as api_error:
            print(f"3. Проверка API: ❌ Нет подключения - {api_error}")

if __name__ == "__main__":
    main()
