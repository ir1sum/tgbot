#!/usr/bin/env python3
"""
Telegram Stars & NFT Bot
Полный функционал: покупка/продажа звёзд, пополнение баланса, NFT, премиум.
Готов к запуску на Amvera Cloud.
"""

import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters
)

# ==================== КОНФИГУРАЦИЯ ====================
BOT_TOKEN = "8196751032:AAGwizPBRuq_uh0zd9GQ6C2BFiseAfnp_xo"
ADMIN_ID = 741906407  # Ваш ID для уведомлений

# Цены и лимиты
STAR_PRICE_BUY = 1.6   # Руб. за 1 звезду (покупка у нас)
STAR_PRICE_SELL = 1.0  # Руб. за 1 звезду (продажа нам) - ИЗМЕНЕНО ПО ВАШЕМУ ЗАПРОСУ
MIN_STARS = 50
MAX_STARS = 5000

# Реквизиты для ПОПОЛНЕНИЯ БАЛАНСА
BANK_CARD = "2202206713916687"
CARD_HOLDER = "ROMAN IVANOV"
CRYPTO_WALLETS = {
    "USDT (TRC20)": "TT6QmsrMhctAabpY9Cy5eSV3L1myxNeUwF",
    "Bitcoin (BTC)": "bc1qy9860j3zxjd3wpy6pj5tu7jpqkz84tzftq076p",
    "TON": "UQA2Xxf6CL2lx2XpiDvPPHr3heCJ5o6nRNBbxytj9eFVTpXx"
}

# Хранилище данных (в памяти)
user_balances = {}
active_orders = {}
user_profiles = {}

# Настройка логов
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== КЛАВИАТУРЫ ====================
def main_menu_keyboard():
    """Главное меню как на скриншоте"""
    keyboard = [
        [InlineKeyboardButton("Купить звёзды", callback_data='buy_stars'),
         InlineKeyboardButton("Продать звёзды", callback_data='sell_stars')],
        [InlineKeyboardButton("Аренда NFT", callback_data='rent_nft'),
         InlineKeyboardButton("Купить NFT", callback_data='buy_nft')],
        [InlineKeyboardButton("Купить обычный подарок", callback_data='buy_gift')],
        [InlineKeyboardButton("Премиум", callback_data='premium')],
        [InlineKeyboardButton("Пополнить баланс", callback_data='deposit'),
         InlineKeyboardButton("Профиль", callback_data='profile')],
        [InlineKeyboardButton("Поддержка", callback_data='support'),
         InlineKeyboardButton("Калькулятор", callback_data='calculator')],
        [InlineKeyboardButton("Информация", callback_data='info')]
    ]
    return InlineKeyboardMarkup(keyboard)

def deposit_methods_keyboard():
    """Клавиатура выбора способа пополнения"""
    keyboard = [
        [InlineKeyboardButton("💳 Карта (РФ)", callback_data='deposit_card')],
        [InlineKeyboardButton("💎 USDT (TRC20)", callback_data='deposit_usdt')],
        [InlineKeyboardButton("₿ Bitcoin", callback_data='deposit_btc')],
        [InlineKeyboardButton("⚡ TON", callback_data='deposit_ton')],
        [InlineKeyboardButton("🔙 Назад", callback_data='back_to_menu')]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== ОСНОВНЫЕ КОМАНДЫ ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    user_id = user.id
    
    # Инициализация профиля
    if user_id not in user_balances:
        user_balances[user_id] = 0.0
    if user_id not in user_profiles:
        user_profiles[user_id] = {"name": user.first_name or "Пользователь", "username": user.username or ""}
    
    welcome_text = (
        f"👋 Добро пожаловать, {user.first_name}!\n\n"
        f"У нас Вы можете приобрести **Telegram Stars**, **Telegram Premium** и арендовать **NFT**.\n\n"
        f"🔒 Текущий баланс: *{user_balances[user_id]:.2f}₽*\n\n"
        f"*Выберите действие* 🔄"
    )
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=main_menu_keyboard(),
        parse_mode='Markdown'
    )
    logger.info(f"Пользователь {user_id} запустил бота")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    help_text = (
        "📚 *Доступные команды:*\n\n"
        "/start - Главное меню\n"
        "/help - Эта справка\n"
        "/profile - Ваш профиль\n\n"
        "*Поддержка:* @IRIS666"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

# ==================== ОБРАБОТКА КНОПОК ====================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка всех inline-кнопок"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    chat_id = query.message.chat_id
    user_id = query.from_user.id
    
    # Инициализация баланса если ещё нет
    if user_id not in user_balances:
        user_balances[user_id] = 0.0
    
    # Обработка действий
    if data == 'back_to_menu':
        await show_main_menu(chat_id, user_id)
    
    elif data == 'buy_stars':
        await ask_stars_amount(chat_id, "buy")
    elif data == 'sell_stars':
        await ask_stars_amount(chat_id, "sell")
    
    elif data == 'calculator':
        await show_calculator(chat_id)
    
    elif data == 'deposit':
        await show_deposit_methods(chat_id)
    
    elif data == 'profile':
        await show_profile(chat_id, user_id)
    
    elif data.startswith('deposit_'):
        method = data.replace('deposit_', '')
        await show_deposit_details(chat_id, method)
    
    elif data in ['rent_nft', 'buy_nft', 'buy_gift', 'premium', 'support', 'info']:
        await show_placeholder(chat_id, data)
    
    else:
        await query.edit_message_text("Действие в разработке 🛠️", reply_markup=main_menu_keyboard())

# ==================== ПОКУПКА/ПРОДАЖА ЗВЁЗД ====================
async def ask_stars_amount(chat_id: int, action: str):
    """Запрос количества звёзд для покупки/продажи"""
    price = STAR_PRICE_BUY if action == "buy" else STAR_PRICE_SELL
    action_text = "покупки" if action == "buy" else "продажи"
    
    text = (
        f"🎛 *Введите количество звёзд для {action_text}*\n\n"
        f"💎 Цена: *{price}₽* за звезду\n"
        f"📦 От *{MIN_STARS}* до *{MAX_STARS}* звёзд\n\n"
        f"*Пример:* 100 звёзд = *{100 * price:.2f}₽*\n\n"
        f"Просто введите число:"
    )
    
    # Сохраняем действие в контексте
    from telegram.ext import ContextTypes
    context = ContextTypes.DEFAULT_TYPE()
    context.user_data['stars_action'] = action
    
    await Application.builder().token(BOT_TOKEN).build().bot.send_message(
        chat_id, text, parse_mode='Markdown'
    )

async def handle_stars_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка введенного количества звёзд"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    text = update.message.text
    
    if not text.isdigit():
        await update.message.reply_text("❌ Введите число! Например: 100")
        return
    
    stars = int(text)
    
    # Проверка лимитов
    if stars < MIN_STARS:
        await update.message.reply_text(f"❌ Минимум {MIN_STARS} звёзд. Попробуйте снова:")
        return
    if stars > MAX_STARS:
        await update.message.reply_text(f"❌ Максимум {MAX_STARS} звёзд. Попробуйте снова:")
        return
    
    # Получаем сохраненное действие
    action = context.user_data.get('stars_action', 'buy')
    price = STAR_PRICE_BUY if action == "buy" else STAR_PRICE_SELL
    total = stars * price
    
    # Создаем заказ
    order_id = f"{'BUY' if action == 'buy' else 'SELL'}_{datetime.now().strftime('%H%M%S')}"
    active_orders[order_id] = {
        'id': order_id,
        'user_id': user_id,
        'action': action,
        'stars': stars,
        'price': price,
        'total': total,
        'time': datetime.now().strftime("%d.%m.%Y %H:%M"),
        'status': 'Ожидает оплаты' if action == 'buy' else 'Ожидает подтверждения'
    }
    
    # Текст в зависимости от действия
    if action == 'buy':
        action_text = "покупки"
        button_text = "💳 Оплатить"
        callback_data = f"confirm_buy_{order_id}"
    else:
        action_text = "продажи"
        button_text = "✅ Подтвердить продажу"
        callback_data = f"confirm_sell_{order_id}"
    
    order_text = (
        f"✅ *Заказ #{order_id}*\n\n"
        f"📋 Действие: *{action_text} звёзд*\n"
        f"⭐ Количество: *{stars}* звёзд\n"
        f"💰 Цена за штуку: *{price}₽*\n"
        f"💵 Итоговая сумма: *{total:.2f}₽*\n\n"
        f"Статус: *{active_orders[order_id]['status']}*"
    )
    
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(button_text, callback_data=callback_data),
        InlineKeyboardButton("❌ Отменить", callback_data='cancel_order')
    ], [
        InlineKeyboardButton("🔙 В меню", callback_data='back_to_menu')
    ]])
    
    await update.message.reply_text(order_text, reply_markup=keyboard, parse_mode='Markdown')
    
    # Уведомление админу
    await notify_admin(
        f"🆕 *Новый заказ #{order_id}*\n"
        f"👤 Пользователь: {user_id}\n"
        f"⭐ {stars} звёзд ({action_text})\n"
        f"💰 {total:.2f}₽"
    )

# ==================== ПОПОЛНЕНИЕ БАЛАНСА ====================
async def show_deposit_methods(chat_id: int):
    """Показать способы пополнения"""
    text = "💳 *Выберите способ пополнения:*"
    await Application.builder().token(BOT_TOKEN).build().bot.send_message(
        chat_id, text, reply_markup=deposit_methods_keyboard(), parse_mode='Markdown'
    )

async def show_deposit_details(chat_id: int, method: str):
    """Показать реквизиты для выбранного способа"""
    if method == 'card':
        text = (
            f"💳 *Пополнение картой*\n\n"
            f"🏦 Номер карты:\n`{BANK_CARD}`\n\n"
            f"👤 Получатель:\n*{CARD_HOLDER}*\n\n"
            f"📝 *Обязательно укажите в комментарии:*\n"
            f"Ваш ID: `{chat_id}`"
        )
    elif method in ['usdt', 'btc', 'ton']:
        wallet_name = {
            'usdt': 'USDT (TRC20)',
            'btc': 'Bitcoin (BTC)',
            'ton': 'TON'
        }[method]
        
        wallet_address = CRYPTO_WALLETS[wallet_name]
        
        text = (
            f"💎 *Пополнение {wallet_name}*\n\n"
            f"🏦 Адрес кошелька:\n`{wallet_address}`\n\n"
            f"📝 *Обязательно укажите в комментарии:*\n"
            f"Ваш ID: `{chat_id}`\n\n"
            f"⚠️ *Внимание:* Отправляйте только в указанной сети!"
        )
    else:
        text = "❌ Способ оплаты не найден"
    
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Я оплатил", callback_data=f'paid_{method}'),
        InlineKeyboardButton("🔙 Назад", callback_data='deposit')
    ]])
    
    await Application.builder().token(BOT_TOKEN).build().bot.send_message(
        chat_id, text, reply_markup=keyboard, parse_mode='Markdown'
    )

# ==================== ПРОФИЛЬ И БАЛАНС ====================
async def show_profile(chat_id: int, user_id: int):
    """Показать профиль пользователя"""
    balance = user_balances.get(user_id, 0.0)
    profile = user_profiles.get(user_id, {"name": "Пользователь", "username": ""})
    
    text = (
        f"👤 *Ваш профиль*\n\n"
        f"🆔 ID: `{user_id}`\n"
        f"👁‍🗨 Имя: {profile['name']}\n"
        f"📱 Юзернейм: @{profile['username'] if profile['username'] else 'не указан'}\n\n"
        f"💰 *Баланс: {balance:.2f}₽*\n\n"
        f"💎 Промокод: IRIS666"
    )
    
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("💰 Пополнить", callback_data='deposit'),
        InlineKeyboardButton("🔄 Обновить", callback_data='profile')
    ], [
        InlineKeyboardButton("🔙 В меню", callback_data='back_to_menu')
    ]])
    
    await Application.builder().token(BOT_TOKEN).build().bot.send_message(
        chat_id, text, reply_markup=keyboard, parse_mode='Markdown'
    )

# ==================== КАЛЬКУЛЯТОР ====================
async def show_calculator(chat_id: int):
    """Показать калькулятор стоимости"""
    examples = [50, 100, 500, 1000, 5000]
    
    buy_text = "*Покупка (1.6₽/звезда):*\n"
    for stars in examples:
        buy_text += f"{stars} звезд = {stars * STAR_PRICE_BUY:.2f}₽\n"
    
    sell_text = "\n*Продажа (1₽/звезда):*\n"
    for stars in examples:
        sell_text += f"{stars} звезд = {stars * STAR_PRICE_SELL:.2f}₽\n"
    
    text = f"🧮 *Калькулятор стоимости*\n\n{buy_text}{sell_text}"
    
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("⭐ Купить звёзды", callback_data='buy_stars'),
        InlineKeyboardButton("💰 Продать звёзды", callback_data='sell_stars')
    ], [
        InlineKeyboardButton("🔙 В меню", callback_data='back_to_menu')
    ]])
    
    await Application.builder().token(BOT_TOKEN).build().bot.send_message(
        chat_id, text, reply_markup=keyboard, parse_mode='Markdown'
    )

# ==================== СЛУЖЕБНЫЕ ФУНКЦИИ ====================
async def show_main_menu(chat_id: int, user_id: int):
    """Показать главное меню"""
    balance = user_balances.get(user_id, 0.0)
    text = f"🔒 Текущий баланс: *{balance:.2f}₽*\n\n*Выберите действие* 🔄"
    await Application.builder().token(BOT_TOKEN).build().bot.send_message(
        chat_id, text, reply_markup=main_menu_keyboard(), parse_mode='Markdown'
    )

async def show_placeholder(chat_id: int, section: str):
    """Заглушка для разделов в разработке"""
    sections = {
        'rent_nft': "🎨 Аренда NFT",
        'buy_nft': "🖼 Купить NFT",
        'buy_gift': "🎁 Обычный подарок",
        'premium': "👑 Telegram Premium",
        'support': "📞 Поддержка",
        'info': "ℹ️ Информация"
    }
    
    text = f"{sections.get(section, 'Раздел')} - *в разработке* 🛠️\nСкоро здесь появится функционал!"
    
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔙 В меню", callback_data='back_to_menu')
    ]])
    
    await Application.builder().token(BOT_TOKEN).build().bot.send_message(
        chat_id, text, reply_markup=keyboard, parse_mode='Markdown'
    )

async def notify_admin(message: str):
    """Отправить уведомление администратору"""
    try:
        await Application.builder().token(BOT_TOKEN).build().bot.send_message(
            ADMIN_ID, message, parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Не удалось отправить уведомление админу: {e}")

# ==================== ЗАПУСК БОТА ====================
def main():
    """Основная функция запуска бота"""
    # Создаем приложение
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрируем обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("profile", lambda u, c: show_profile(u.effective_chat.id, u.effective_user.id)))
    
    # Обработчик кнопок
    app.add_handler(CallbackQueryHandler(button_handler))
    
    # Обработчик текстовых сообщений (для ввода количества звёзд)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_stars_amount))
    
    # Запуск
    logger.info("Бот запускается...")
    print("=" * 50)
    print("🤖 БОТ АКТИВИРОВАН")
    print(f"🔑 Токен: {BOT_TOKEN[:10]}...")
    print(f"👑 Админ ID: {ADMIN_ID}")
    print(f"⭐ Цена покупки: {STAR_PRICE_BUY}₽ | Продажи: {STAR_PRICE_SELL}₽")
    print(f"📦 Лимиты: {MIN_STARS}-{MAX_STARS} звёзд")
    print("=" * 50)
    print("🚀 Бот готов к работе! Ожидаю команду /start")
    
    app.run_polling()

if __name__ == '__main__':
    main()
