#!/usr/bin/env python3
"""
Telegram Stars Bot v2.0
Полностью автономный бот для продажи Telegram Stars.
Просто вставьте свой токен и ID, затем загрузите в Amvera.
"""

import os
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# ========== НАСТРОЙКИ ==========
# ЗАМЕНИТЕ ЭТИ ДАННЫЕ НА СВОИ!
BOT_TOKEN = "8196751032:AAGwizPBRuq_uh0zd9GQ6C2BFiseAfnp_xo"  # Токен от @BotFather
ADMIN_ID = 123456789  # Ваш ID Telegram (узнать у @userinfobot)

# Цены и лимиты
STAR_PRICE = 1.6  # Рублей за звезду
MIN_STARS = 50
MAX_STARS = 5000

# Реквизиты для оплаты (замените на свои!)
BANK_CARD = "2200 1234 5678 9012"
BANK_HOLDER = "ИВАН ИВАНОВ"
USDT_WALLET = "TAbcdefgh1234567890"
TON_WALLET = "UQabcdefgh1234567890"

# Хранилище заказов в памяти (пока без базы данных)
active_orders = {}
user_data = {}

# Настройка логов
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== КЛАВИАТУРЫ ==========
def get_main_menu():
    """Главное меню бота"""
    keyboard = [
        [InlineKeyboardButton("⭐ Купить звёзды", callback_data='buy_stars')],
        [InlineKeyboardButton("💰 Калькулятор", callback_data='calculator')],
        [InlineKeyboardButton("💳 Способы оплаты", callback_data='payment_methods')],
        [InlineKeyboardButton("📞 Поддержка", callback_data='support')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_payment_methods(order_id):
    """Кнопки выбора способа оплаты"""
    keyboard = [
        [
            InlineKeyboardButton("💳 Карта РФ", callback_data=f'pay_card_{order_id}'),
            InlineKeyboardButton("💎 USDT", callback_data=f'pay_usdt_{order_id}')
        ],
        [
            InlineKeyboardButton("⚡ TON", callback_data=f'pay_ton_{order_id}'),
            InlineKeyboardButton("₿ Bitcoin", callback_data=f'pay_btc_{order_id}')
        ],
        [InlineKeyboardButton("🔙 Назад", callback_data='back_to_menu')]
    ]
    return InlineKeyboardMarkup(keyboard)

# ========== КОМАНДЫ ==========
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    welcome_text = (
        f"🌟 Добро пожаловать, {user.first_name}!\n\n"
        f"Я — бот для покупки Telegram Stars.\n\n"
        f"💎 <b>Цена:</b> {STAR_PRICE}₽ за звезду\n"
        f"📦 <b>Минимум:</b> {MIN_STARS} звезд\n"
        f"⚡ <b>Мгновенная доставка</b>\n\n"
        f"Нажмите 'Купить звёзды' для заказа!"
    )
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_menu(),
        parse_mode='HTML'
    )
    logger.info(f"Пользователь {user.id} ({user.username}) запустил бота")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    help_text = (
        "🤖 <b>Доступные команды:</b>\n\n"
        "/start - Главное меню\n"
        "/buy - Купить звёзды\n"
        "/orders - Мои заказы\n"
        "/help - Эта справка\n\n"
        "📞 <b>Поддержка:</b> @ваш_аккаунт"
    )
    await update.message.reply_text(help_text, parse_mode='HTML')

async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /buy"""
    await ask_for_stars(update.effective_chat.id)

async def orders_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать заказы пользователя"""
    user_id = update.effective_user.id
    user_orders = [o for o in active_orders.values() if o['user_id'] == user_id]
    
    if not user_orders:
        await update.message.reply_text("📭 У вас пока нет активных заказов.")
        return
    
    orders_text = "📋 <b>Ваши заказы:</b>\n\n"
    for order in user_orders[:5]:  # Показываем последние 5 заказов
        orders_text += (
            f"🎫 <b>Заказ #{order['id']}</b>\n"
            f"⭐ {order['stars']} звезд | {order['price']}₽\n"
            f"📊 Статус: {order['status']}\n"
            f"🕐 {order['time']}\n\n"
        )
    
    await update.message.reply_text(orders_text, parse_mode='HTML')

# ========== ОСНОВНАЯ ЛОГИКА ==========
async def ask_for_stars(chat_id: int):
    """Запросить количество звёзд"""
    text = (
        f"🎛 <b>Введите количество звезд</b>\n\n"
        f"💎 Цена: <b>{STAR_PRICE}₽</b> за штуку\n"
        f"📦 От <b>{MIN_STARS}</b> до <b>{MAX_STARS}</b>\n\n"
        f"<i>Пример: 100 звезд = {100 * STAR_PRICE}₽</i>\n\n"
        f"Просто введите любое число:"
    )
    await application.bot.send_message(chat_id, text, parse_mode='HTML')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений"""
    text = update.message.text
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Если сообщение - число, обрабатываем как заказ
    if text.isdigit():
        stars = int(text)
        await process_order(chat_id, user.id, stars, user.first_name)
    else:
        await update.message.reply_text(
            "Используйте команды из меню или введите количество звезд (например: 100)"
        )

async def process_order(chat_id: int, user_id: int, stars: int, user_name: str):
    """Обработка нового заказа"""
    # Проверка лимитов
    if stars < MIN_STARS:
        await application.bot.send_message(
            chat_id, 
            f"❌ Минимум {MIN_STARS} звезд. Попробуйте снова:"
        )
        return
    
    if stars > MAX_STARS:
        await application.bot.send_message(
            chat_id, 
            f"❌ Максимум {MAX_STARS} звезд. Попробуйте снова:"
        )
        return
    
    # Расчет стоимости
    price = stars * STAR_PRICE
    order_id = f"ORD{datetime.now().strftime('%H%M%S')}"
    
    # Сохранение заказа
    active_orders[order_id] = {
        'id': order_id,
        'user_id': user_id,
        'user_name': user_name,
        'stars': stars,
        'price': f"{price:.2f}",
        'status': 'Ожидает оплаты',
        'time': datetime.now().strftime("%d.%m.%Y %H:%M"),
        'payment_method': None
    }
    
    # Показ способов оплаты
    keyboard = get_payment_methods(order_id)
    text = (
        f"✅ <b>Заказ #{order_id}</b>\n\n"
        f"⭐ <b>Звёзд:</b> {stars}\n"
        f"💰 <b>Сумма:</b> {price:.2f}₽\n\n"
        f"Выберите способ оплаты:"
    )
    
    await application.bot.send_message(
        chat_id, 
        text, 
        reply_markup=keyboard,
        parse_mode='HTML'
    )
    
    logger.info(f"Создан заказ #{order_id} для пользователя {user_id}")

# ========== ОБРАБОТКА КНОПОК ==========
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий на inline-кнопки"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    chat_id = query.message.chat_id
    message_id = query.message.message_id
    
    # Главное меню
    if data == 'buy_stars':
        await ask_for_stars(chat_id)
        await query.delete_message()
    
    elif data == 'calculator':
        await show_calculator(chat_id)
    
    elif data == 'payment_methods':
        await show_all_payments(chat_id)
    
    elif data == 'support':
        await show_support(chat_id)
    
    elif data == 'back_to_menu':
        await query.edit_message_text(
            "Главное меню:",
            reply_markup=get_main_menu()
        )
    
    # Обработка выбора оплаты
    elif data.startswith('pay_'):
        parts = data.split('_')
        if len(parts) == 3:
            method = parts[1]  # card, usdt, ton, btc
            order_id = parts[2]
            await show_payment_details(chat_id, order_id, method)
    
    # Подтверждение оплаты
    elif data.startswith('confirm_'):
        order_id = data.replace('confirm_', '')
        await confirm_payment(chat_id, order_id)

async def show_payment_details(chat_id: int, order_id: str, method: str):
    """Показать реквизиты для оплаты"""
    if order_id not in active_orders:
        await application.bot.send_message(chat_id, "❌ Заказ не найден")
        return
    
    order = active_orders[order_id]
    
    if method == 'card':
        text = (
            f"💳 <b>Оплата картой</b>\n\n"
            f"🎫 Код заказа: <code>{order_id}</code>\n"
            f"⭐ Звёзд: {order['stars']}\n"
            f"💰 Сумма: {order['price']}₽\n\n"
            f"🏦 <b>Реквизиты:</b>\n"
            f"Карта: <code>{BANK_CARD}</code>\n"
            f"Получатель: {BANK_HOLDER}\n\n"
            f"📝 <b>ВАЖНО:</b> В комментарии укажите код заказа!"
        )
    
    elif method == 'usdt':
        text = (
            f"💎 <b>Оплата USDT (TRC20)</b>\n\n"
            f"🎫 Код заказа: <code>{order_id}</code>\n"
            f"⭐ Звёзд: {order['stars']}\n"
            f"💰 Сумма: {order['price']}₽\n\n"
            f"🏦 <b>Кошелёк:</b>\n"
            f"<code>{USDT_WALLET}</code>\n\n"
            f"📝 <b>ВАЖНО:</b> В комментарии укажите код заказа!"
        )
    
    elif method == 'ton':
        text = (
            f"⚡ <b>Оплата TON</b>\n\n"
            f"🎫 Код заказа: <code>{order_id}</code>\n"
            f"⭐ Звёзд: {order['stars']}\n"
            f"💰 Сумма: {order['price']}₽\n\n"
            f"🏦 <b>Кошелёк:</b>\n"
            f"<code>{TON_WALLET}</code>\n\n"
            f"📝 <b>ВАЖНО:</b> В комментарии укажите код заказа!"
        )
    
    else:
        text = "❌ Способ оплаты не поддерживается"
    
    # Кнопка подтверждения оплаты
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Я оплатил", callback_data=f'confirm_{order_id}'),
        InlineKeyboardButton("🔙 Назад", callback_data='back_to_menu')
    ]])
    
    await application.bot.send_message(
        chat_id, 
        text, 
        reply_markup=keyboard,
        parse_mode='HTML'
    )

async def confirm_payment(chat_id: int, order_id: str):
    """Подтверждение оплаты от пользователя"""
    if order_id not in active_orders:
        await application.bot.send_message(chat_id, "❌ Заказ не найден")
        return
    
    order = active_orders[order_id]
    order['status'] = 'Оплата проверяется'
    
    text = (
        f"🕐 <b>Оплата получена!</b>\n\n"
        f"Заказ #{order_id} передан на проверку.\n"
        f"Обычно проверка занимает 5-15 минут.\n"
        f"Как только платеж подтвердится, мы отправим вам звёзды.\n\n"
        f"📞 <b>Поддержка:</b> @ваш_аккаунт"
    )
    
    # Уведомление администратора
    admin_text = (
        f"📦 <b>Новый платеж!</b>\n\n"
        f"🎫 Заказ: #{order_id}\n"
        f"👤 Пользователь: {order['user_name']} (ID: {order['user_id']})\n"
        f"⭐ Звёзд: {order['stars']}\n"
        f"💰 Сумма: {order['price']}₽\n"
        f"🕐 Время: {order['time']}"
    )
    
    try:
        await application.bot.send_message(ADMIN_ID, admin_text, parse_mode='HTML')
    except Exception as e:
        logger.error(f"Не удалось уведомить администратора: {e}")
    
    await application.bot.send_message(chat_id, text, parse_mode='HTML')
    logger.info(f"Пользователь подтвердил оплату заказа #{order_id}")

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
async def show_calculator(chat_id: int):
    """Показать калькулятор стоимости"""
    examples = [50, 100, 500, 1000, 5000]
    text = "🧮 <b>Калькулятор стоимости</b>\n\n"
    
    for stars in examples:
        price = stars * STAR_PRICE
        text += f"{stars} звезд = {price:.2f}₽\n"
    
    text += f"\n💎 <i>Цена: {STAR_PRICE}₽ за звезду</i>"
    
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("⭐ Купить сейчас", callback_data='buy_stars')
    ]])
    
    await application.bot.send_message(
        chat_id, 
        text, 
        reply_markup=keyboard,
        parse_mode='HTML'
    )

async def show_all_payments(chat_id: int):
    """Показать все способы оплаты"""
    text = (
        "💳 <b>Доступные способы оплаты:</b>\n\n"
        "1. <b>Карта РФ</b> (Сбербанк, Тинькофф, и др.)\n"
        "2. <b>USDT (TRC20)</b> - быстрые переводы\n"
        "3. <b>TON</b> - моментальные переводы\n"
        "4. <b>Bitcoin (BTC)</b> - безопасно\n\n"
        "При создании заказа вы сможете выбрать любой способ."
    )
    
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("⭐ Купить звёзды", callback_data='buy_stars')
    ]])
    
    await application.bot.send_message(
        chat_id, 
        text, 
        reply_markup=keyboard,
        parse_mode='HTML'
    )

async def show_support(chat_id: int):
    """Показать контакты поддержки"""
    text = (
        "📞 <b>Служба поддержки</b>\n\n"
        "🕐 Работаем 24/7\n"
        "📨 Ответ в течение 5-15 минут\n\n"
        "<b>Контакты:</b>\n"
        "Telegram: @ваш_аккаунт\n"
        "Email: ваш@email.com\n\n"
        "<b>По всем вопросам:</b>\n"
        "• Проблемы с оплатой\n"
        "• Не пришли звёзды\n"
        "• Изменить заказ\n"
        "• Сотрудничество"
    )
    
    await application.bot.send_message(chat_id, text, parse_mode='HTML')

# ========== ЗАПУСК БОТА ==========
def main():
    """Основная функция запуска бота"""
    global application
    
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("buy", buy_command))
    application.add_handler(CommandHandler("orders", orders_command))
    
    # Обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Обработчик кнопок
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Запускаем бота
    logger.info("Бот запускается...")
    print(f"✅ Бот запущен! Токен: {BOT_TOKEN[:10]}...")
    print(f"👑 Админ ID: {ADMIN_ID}")
    print("🚀 Бот готов к работе!")
    
    application.run_polling()

if __name__ == '__main__':
    main()
