#!/usr/bin/env python3
"""
Упрощенный бот для Amvera без psutil
"""

import json
import logging
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Конфигурация
TOKEN = os.getenv("TELEGRAM_TOKEN", "8196751032:AAGwizPBRuq_uh0zd9GQ6C2BFiseAfnp_xo")
ADMIN_ID = 741906407

# Упрощенная БД в памяти (для начала)
users_db = {}
orders_db = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    # Инициализация пользователя
    if user_id not in users_db:
        users_db[user_id] = {
            "balance": 0.0,
            "stars": 0,
            "name": user.first_name
        }
    
    user_data = users_db[user_id]
    
    # Клавиатура
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⭐ Купить звезды", callback_data="buy"),
         InlineKeyboardButton("💰 Продать звезды", callback_data="sell")],
        [InlineKeyboardButton("📊 Профиль", callback_data="profile"),
         InlineKeyboardButton("ℹ️ Помощь", callback_data="help")]
    ])
    
    text = (
        f"👋 Привет, {user.first_name}!\n\n"
        f"💰 Баланс: {user_data['balance']:.1f}₽\n"
        f"⭐ Звезд: {user_data['stars']}\n\n"
        f"Выберите действие:"
    )
    
    await update.message.reply_text(text, reply_markup=keyboard)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "profile":
        if user_id in users_db:
            user_data = users_db[user_id]
            text = f"📊 Профиль\n\nID: {user_id}\nБаланс: {user_data['balance']:.1f}₽\nЗвезд: {user_data['stars']}"
        else:
            text = "Профиль не найден"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Назад", callback_data="back")]
        ])
        await query.edit_message_text(text, reply_markup=keyboard)
    
    elif data == "buy":
        text = "🎛 Выберите количество звезд для покупки:"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("50 ⭐", callback_data="buy_50"),
             InlineKeyboardButton("100 ⭐", callback_data="buy_100")],
            [InlineKeyboardButton("500 ⭐", callback_data="buy_500"),
             InlineKeyboardButton("1000 ⭐", callback_data="buy_1000")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back")]
        ])
        await query.edit_message_text(text, reply_markup=keyboard)
    
    elif data.startswith("buy_"):
        amount = int(data.split("_")[1])
        price = amount * 1.6  # Цена покупки
        
        order_id = f"buy_{user_id}_{datetime.now().strftime('%H%M%S')}"
        orders_db[order_id] = {
            "user_id": user_id,
            "amount": amount,
            "price": price,
            "status": "pending"
        }
        
        text = (
            f"✅ Заказ #{order_id}\n\n"
            f"Количество: {amount} ⭐\n"
            f"Сумма: {price:.1f}₽\n\n"
            f"Для оплаты:\n"
            f"💳 Карта: 2202206713916687\n"
            f"Получатель: ROMAN IVANOV\n\n"
            f"В комментарии укажите: {order_id}"
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Я оплатил", callback_data=f"paid_{order_id}")],
            [InlineKeyboardButton("❌ Отмена", callback_data="back")]
        ])
        
        await query.edit_message_text(text, reply_markup=keyboard)
        
        # Уведомление админу
        try:
            await context.bot.send_message(
                ADMIN_ID,
                f"🆕 Новый заказ #{order_id}\n"
                f"👤 {user_id}\n"
                f"⭐ {amount} звезд\n"
                f"💰 {price:.1f}₽"
            )
        except:
            pass
    
    elif data == "back":
        await start_from_button(query)
    
    elif data == "help":
        await query.edit_message_text("📞 Техподдержка: @iris_support\n\nПромокод: IRIS666")

async def start_from_button(query):
    """Обновление сообщения на главное меню"""
    user_id = query.from_user.id
    
    if user_id in users_db:
        user_data = users_db[user_id]
        text = f"Главное меню\n\nБаланс: {user_data['balance']:.1f}₽\nЗвезд: {user_data['stars']}"
    else:
        text = "Главное меню"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⭐ Купить звезды", callback_data="buy"),
         InlineKeyboardButton("💰 Продать звезды", callback_data="sell")],
        [InlineKeyboardButton("📊 Профиль", callback_data="profile"),
         InlineKeyboardButton("ℹ️ Помощь", callback_data="help")]
    ])
    
    await query.edit_message_text(text, reply_markup=keyboard)

def main():
    """Запуск бота"""
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    
    # Создаем приложение
    application = Application.builder().token(TOKEN).build()
    
    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Запускаем бота
    print("=" * 50)
    print("🤖 БОТ ЗАПУСКАЕТСЯ")
    print(f"🔑 Токен: {TOKEN[:10]}...")
    print(f"👑 Админ: {ADMIN_ID}")
    print("=" * 50)
    
    application.run_polling()

if __name__ == "__main__":
    main()
