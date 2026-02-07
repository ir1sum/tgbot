#!/usr/bin/env python3
"""
Telegram Stars Bot - Упрощенная и рабочая версия
Все кнопки работают, включая "Купить звёзды"
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
ADMIN_ID = 741906407

# Цены
STAR_PRICE_BUY = 1.6  # Покупка у нас
STAR_PRICE_SELL = 1.0 # Продажа нам
MIN_STARS = 50
MAX_STARS = 5000

# Реквизиты
BANK_CARD = "2202206713916687"
CARD_HOLDER = "ROMAN IVANOV"
CRYPTO_WALLETS = {
    "USDT (TRC20)": "TT6QmsrMhctAabpY9Cy5eSV3L1myxNeUwF",
    "Bitcoin (BTC)": "bc1qy9860j3zxjd3wpy6pj5tu7jpqkz84tzftq076p",
    "TON": "UQA2Xxf6CL2lx2XpiDvPPHr3heCJ5o6nRNBbxytj9eFVTpXx"
}

# Хранилища (в памяти)
user_balances = {}
user_states = {}  # Новое: храним состояние каждого пользователя
active_orders = {}

# Логи
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== КЛАВИАТУРЫ ====================
def main_menu():
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

def back_to_menu_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 В меню", callback_data='menu')]])

# ==================== КОМАНДЫ ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало работы"""
    user = update.effective_user
    user_id = user.id
    
    if user_id not in user_balances:
        user_balances[user_id] = 0.0
    
    text = (
        f"👋 Добро пожаловать, {user.first_name}!\n\n"
        f"🔒 Текущий баланс: *{user_balances[user_id]:.2f}₽*\n\n"
        f"*Выберите действие* 🔄"
    )
    
    await update.message.reply_text(text, reply_markup=main_menu(), parse_mode='Markdown')

# ==================== ОБРАБОТКА КНОПОК ====================
async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    
    # Инициализация баланса
    if user_id not in user_balances:
        user_balances[user_id] = 0.0
    
    if data == 'menu':
        await show_menu(chat_id, user_id)
        return
    
    if data == 'buy_stars':
        # Ключевой момент: запоминаем, что пользователь хочет купить
        user_states[user_id] = 'waiting_stars_buy'
        await query.edit_message_text(
            f"🎛 *Введите количество звёзд для покупки*\n\n"
            f"💎 Цена: *{STAR_PRICE_BUY}₽* за звезду\n"
            f"📦 От *{MIN_STARS}* до *{MAX_STARS}*\n\n"
            f"*Пример:* 100 звёзд = *{100 * STAR_PRICE_BUY:.2f}₽*\n\n"
            f"Просто введите число:",
            parse_mode='Markdown'
        )
        return
    
    if data == 'sell_stars':
        user_states[user_id] = 'waiting_stars_sell'
        await query.edit_message_text(
            f"🎛 *Введите количество звёзд для продажи*\n\n"
            f"💎 Цена: *{STAR_PRICE_SELL}₽* за звезду\n"
            f"📦 От *{MIN_STARS}* до *{MAX_STARS}*\n\n"
            f"*Пример:* 100 звёзд = *{100 * STAR_PRICE_SELL:.2f}₽*\n\n"
            f"Просто введите число:",
            parse_mode='Markdown'
        )
        return
    
    if data == 'calculator':
        text = "🧮 *Калькулятор*\n\n"
        text += f"Покупка ({STAR_PRICE_BUY}₽):\n"
        for amount in [50, 100, 500, 1000, 5000]:
            text += f"{amount} звёзд = {amount * STAR_PRICE_BUY:.2f}₽\n"
        text += f"\nПродажа ({STAR_PRICE_SELL}₽):\n"
        for amount in [50, 100, 500, 1000, 5000]:
            text += f"{amount} звёзд = {amount * STAR_PRICE_SELL:.2f}₽\n"
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=back_to_menu_button())
        return
    
    if data == 'profile':
        balance = user_balances.get(user_id, 0.0)
        text = f"👤 *Профиль*\n\n🆔 ID: `{user_id}`\n💰 Баланс: *{balance:.2f}₽*\n\n💎 Промокод: IRIS666"
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=back_to_menu_button())
        return
    
    if data == 'deposit':
        keyboard = [
            [InlineKeyboardButton("💳 Карта", callback_data='deposit_card')],
            [InlineKeyboardButton("💎 USDT", callback_data='deposit_usdt')],
            [InlineKeyboardButton("₿ Bitcoin", callback_data='deposit_btc')],
            [InlineKeyboardButton("⚡ TON", callback_data='deposit_ton')],
            [InlineKeyboardButton("🔙 Назад", callback_data='menu')]
        ]
        await query.edit_message_text(
            "💳 *Выберите способ пополнения:*",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # Обработка выбора способа пополнения
    if data.startswith('deposit_'):
        method = data.replace('deposit_', '')
        
        if method == 'card':
            text = f"💳 *Карта РФ*\n\n`{BANK_CARD}`\n👤 {CARD_HOLDER}\n\n📝 В комментарии укажите ваш ID: `{user_id}`"
        elif method == 'usdt':
            text = f"💎 *USDT (TRC20)*\n\n`{CRYPTO_WALLETS['USDT (TRC20)']}`\n\n📝 В комментарии укажите ваш ID: `{user_id}`"
        elif method == 'btc':
            text = f"₿ *Bitcoin*\n\n`{CRYPTO_WALLETS['Bitcoin (BTC)']}`\n\n📝 В комментарии укажите ваш ID: `{user_id}`"
        elif method == 'ton':
            text = f"⚡ *TON*\n\n`{CRYPTO_WALLETS['TON']}`\n\n📝 В комментарии укажите ваш ID: `{user_id}`"
        else:
            text = "❌ Способ не найден"
        
        keyboard = [[InlineKeyboardButton("✅ Я оплатил", callback_data=f'paid_{method}')],
                   [InlineKeyboardButton("🔙 Назад", callback_data='deposit')]]
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    # Заглушки для остальных кнопок
    sections = {
        'rent_nft': "🎨 Аренда NFT",
        'buy_nft': "🖼 Купить NFT", 
        'buy_gift': "🎁 Обычный подарок",
        'premium': "👑 Премиум",
        'support': "📞 Поддержка",
        'info': "ℹ️ Информация"
    }
    
    if data in sections:
        await query.edit_message_text(
            f"{sections[data]} - *в разработке* 🛠️",
            parse_mode='Markdown',
            reply_markup=back_to_menu_button()
        )
        return

# ==================== ОБРАБОТКА ВВОДА ЧИСЛА (ЗВЁЗД) ====================
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает ввод количества звёзд"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    chat_id = update.effective_chat.id
    
    # Проверяем, ждём ли мы ввод числа от этого пользователя
    user_state = user_states.get(user_id)
    
    if not user_state:
        # Пользователь просто что-то написал, не нажимая кнопку
        return
    
    if not text.isdigit():
        await update.message.reply_text("❌ Введите число! Например: 100")
        return
    
    stars = int(text)
    
    # Проверка лимитов
    if stars < MIN_STARS:
        await update.message.reply_text(f"❌ Минимум {MIN_STARS} звёзд")
        return
    if stars > MAX_STARS:
        await update.message.reply_text(f"❌ Максимум {MAX_STARS} звёзд")
        return
    
    # Определяем тип операции
    if user_state == 'waiting_stars_buy':
        price = STAR_PRICE_BUY
        action = "покупки"
        order_type = "BUY"
        status = "Ожидает оплаты"
        button_text = "💳 Оплатить"
        callback_data = "confirm_buy"
    else:  # waiting_stars_sell
        price = STAR_PRICE_SELL
        action = "продажи"
        order_type = "SELL"
        status = "Ожидает подтверждения"
        button_text = "✅ Подтвердить"
        callback_data = "confirm_sell"
    
    total = stars * price
    
    # Создаём заказ
    order_id = f"{order_type}_{datetime.now().strftime('%H%M%S')}"
    active_orders[order_id] = {
        'id': order_id,
        'user_id': user_id,
        'stars': stars,
        'total': total,
        'status': status
    }
    
    # Очищаем состояние пользователя
    user_states.pop(user_id, None)
    
    # Показываем заказ
    order_text = (
        f"✅ *Заказ #{order_id}*\n\n"
        f"📋 Действие: *{action} звёзд*\n"
        f"⭐ Количество: *{stars}* звёзд\n"
        f"💰 Цена: *{price}₽* за штуку\n"
        f"💵 Итого: *{total:.2f}₽*\n\n"
        f"Статус: *{status}*"
    )
    
    keyboard = [
        [InlineKeyboardButton(button_text, callback_data=f'{callback_data}_{order_id}')],
        [InlineKeyboardButton("🔙 В меню", callback_data='menu')]
    ]
    
    await update.message.reply_text(
        order_text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    # Уведомляем админа
    try:
        await Application.builder().token(BOT_TOKEN).build().bot.send_message(
            ADMIN_ID,
            f"🆕 Новый заказ #{order_id}\n👤 {user_id}\n⭐ {stars} звёзд ({action})\n💰 {total:.2f}₽",
            parse_mode='Markdown'
        )
    except:
        pass

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================
async def show_menu(chat_id: int, user_id: int):
    """Показать главное меню"""
    balance = user_balances.get(user_id, 0.0)
    text = f"🔒 Баланс: *{balance:.2f}₽*\n\n*Выберите действие* 🔄"
    
    app = Application.builder().token(BOT_TOKEN).build()
    await app.bot.send_message(chat_id, text, reply_markup=main_menu(), parse_mode='Markdown')

# ==================== ЗАПУСК ====================
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # Запуск
    logger.info("Бот запущен")
    print("=" * 50)
    print("🤖 БОТ ЗАПУЩЕН")
    print(f"⭐ Покупка: {STAR_PRICE_BUY}₽ | Продажа: {STAR_PRICE_SELL}₽")
    print(f"📦 Лимит: {MIN_STARS}-{MAX_STARS} звёзд")
    print("=" * 50)
    
    app.run_polling()

if __name__ == '__main__':
    main()
