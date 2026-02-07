#!/usr/bin/env python3
"""
Telegram Stars Bot - Унифицированная версия
Все функции из обоих кодов + простая архитектура
"""

import json
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ==================== КОНФИГУРАЦИЯ ====================
TOKEN = "8196751032:AAGwizPBRuq_uh0zd9GQ6C2BFiseAfnp_xo"
ADMIN_ID = 741906407

# Цены
STAR_PRICE_BUY = 1.6
STAR_PRICE_SELL = 1.0
MIN_STARS = 50
MAX_STARS = 5000

# Премиум тарифы
PREMIUM_PLANS = {
    "month": {"name": "1 Месяц", "price": 299, "days": 30},
    "three": {"name": "3 Месяца", "price": 799, "days": 90},
    "six": {"name": "6 Месяцев", "price": 1499, "days": 180},
    "year": {"name": "1 Год", "price": 2599, "days": 365}
}

# Реквизиты
PAYMENT_METHODS = {
    "card": {"type": "💳 Карта РФ", "details": "2202206713916687\nПолучатель: ROMAN IVANOV"},
    "usdt": {"type": "💎 USDT (TRC20)", "details": "TT6QmsrMhctAabpY9Cy5eSV3L1myxNeUwF"},
    "btc": {"type": "₿ Bitcoin", "details": "bc1qy9860j3zxjd3wpy6pj5tu7jpqkz84tzftq076p"},
    "ton": {"type": "⚡ TON", "details": "UQA2Xxf6CL2lx2XpiDvPPHr3heCJ5o6nRNBbxytj9eFVTpXx"}
}

# ==================== БАЗА ДАННЫХ (УПРОЩЁННАЯ) ====================
class SimpleDB:
    """Упрощённая база данных из кода 2 + простота кода 1"""
    def __init__(self):
        self.users = {}
        self.orders = {}
        self.load()
    
    def load(self):
        """Загрузить данные из файла"""
        try:
            with open("data.json", "r") as f:
                data = json.load(f)
                self.users = data.get("users", {})
                self.orders = data.get("orders", {})
        except:
            self.users = {}
            self.orders = {}
    
    def save(self):
        """Сохранить данные в файл"""
        try:
            with open("data.json", "w") as f:
                json.dump({"users": self.users, "orders": self.orders}, f, indent=2)
        except:
            pass
    
    def get_user(self, user_id):
        """Получить или создать пользователя"""
        if str(user_id) not in self.users:
            self.users[str(user_id)] = {
                "balance": 0.0,
                "stars": 0,
                "premium_until": None,
                "created": datetime.now().isoformat()
            }
            self.save()
        return self.users[str(user_id)]
    
    def update_balance(self, user_id, amount):
        """Изменить баланс пользователя"""
        user = self.get_user(user_id)
        user["balance"] = user.get("balance", 0.0) + amount
        self.save()
        return user["balance"]

db = SimpleDB()

# ==================== КЛАВИАТУРЫ (ЕДИНЫЙ СТИЛЬ) ====================
def main_menu():
    """Главное меню как в коде 1, но с премиумом из кода 2"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⭐ Купить звёзды", callback_data="action_buy"),
         InlineKeyboardButton("💰 Продать звёзды", callback_data="action_sell")],
        [InlineKeyboardButton("👑 Премиум", callback_data="menu_premium"),
         InlineKeyboardButton("💳 Пополнить", callback_data="menu_deposit")],
        [InlineKeyboardButton("📊 Профиль", callback_data="menu_profile"),
         InlineKeyboardButton("🧮 Калькулятор", callback_data="menu_calc")],
        [InlineKeyboardButton("📞 Поддержка", callback_data="menu_support"),
         InlineKeyboardButton("ℹ️ Инфо", callback_data="menu_info")]
    ])

def back_button():
    """Кнопка назад как в коде 1"""
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="menu_main")]])

def quick_stars_buttons(action):
    """Быстрые кнопки выбора количества как в коде 1"""
    buttons = []
    amounts = [50, 100, 250, 500, 1000, 5000]
    
    # Первые 4 кнопки в два ряда
    for i in range(0, 4, 2):
        row = []
        row.append(InlineKeyboardButton(str(amounts[i]), callback_data=f"stars_{action}_{amounts[i]}"))
        row.append(InlineKeyboardButton(str(amounts[i+1]), callback_data=f"stars_{action}_{amounts[i+1]}"))
        buttons.append(row)
    
    # Последние 2 кнопки
    buttons.append([InlineKeyboardButton(str(amounts[4]), callback_data=f"stars_{action}_{amounts[4]}")])
    buttons.append([InlineKeyboardButton(str(amounts[5]), callback_data=f"stars_{action}_{amounts[5]}")])
    buttons.append([InlineKeyboardButton("✏️ Своё число", callback_data=f"custom_{action}")])
    buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="menu_main")])
    
    return InlineKeyboardMarkup(buttons)

# ==================== ОБРАБОТЧИКИ (ПРОСТАЯ ЛОГИКА КОДА 1) ====================
user_states = {}  # Простое хранилище состояний из кода 1

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Упрощённый старт как в коде 1"""
    user = update.effective_user
    user_data = db.get_user(user.id)
    
    text = (
        f"👋 Привет, {user.first_name}!\n\n"
        f"⭐ Купить: {STAR_PRICE_BUY}₽/шт | Продать: {STAR_PRICE_SELL}₽/шт\n"
        f"💰 Баланс: {user_data['balance']:.2f}₽\n"
        f"✨ Звёзд: {user_data['stars']}\n\n"
        f"Выберите действие:"
    )
    
    await update.message.reply_text(text, reply_markup=main_menu(), parse_mode="Markdown")

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Унифицированный обработчик кнопок"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    # Главное меню
    if data == "menu_main":
        user_data = db.get_user(user_id)
        text = f"💰 Баланс: {user_data['balance']:.2f}₽\nВыберите действие:"
        await query.edit_message_text(text, reply_markup=main_menu(), parse_mode="Markdown")
        return
    
    # Действия со звёздами (из кода 1)
    if data == "action_buy":
        user_states[user_id] = "waiting_buy"
        await query.edit_message_text(
            f"🎛 Введите количество звёзд для ПОКУПКИ:\n\n"
            f"Цена: {STAR_PRICE_BUY}₽/шт\n"
            f"Мин: {MIN_STARS} | Макс: {MAX_STARS}\n\n"
            f"Или выберите быстрый вариант:",
            reply_markup=quick_stars_buttons("buy")
        )
        return
    
    if data == "action_sell":
        user_states[user_id] = "waiting_sell"
        await query.edit_message_text(
            f"🎛 Введите количество звёзд для ПРОДАЖИ:\n\n"
            f"Цена: {STAR_PRICE_SELL}₽/шт\n"
            f"Мин: {MIN_STARS} | Макс: {MAX_STARS}\n\n"
            f"Или выберите быстрый вариант:",
            reply_markup=quick_stars_buttons("sell")
        )
        return
    
    # Быстрый выбор количества (код 1)
    if data.startswith("stars_"):
        _, action, amount = data.split("_")
        amount = int(amount)
        await process_stars_order(user_id, query.message.chat_id, action, amount)
        return
    
    # Ручной ввод (код 1)
    if data.startswith("custom_"):
        action = data.replace("custom_", "")
        user_states[user_id] = f"waiting_{action}"
        await query.edit_message_text(
            f"✏️ Введите количество звёзд для {'ПОКУПКИ' if action == 'buy' else 'ПРОДАЖИ'}:\n\n"
            f"От {MIN_STARS} до {MAX_STARS}\n"
            f"Просто отправьте число в чат:",
            reply_markup=back_button()
        )
        return
    
    # Профиль (объединённый)
    if data == "menu_profile":
        user_data = db.get_user(user_id)
        premium_text = ""
        if user_data.get("premium_until"):
            until = datetime.fromisoformat(user_data["premium_until"])
            if until > datetime.now():
                days = (until - datetime.now()).days
                premium_text = f"👑 Премиум: {days} дней\n"
        
        text = (
            f"📊 Профиль\n\n"
            f"🆔 ID: {user_id}\n"
            f"💰 Баланс: {user_data['balance']:.2f}₽\n"
            f"⭐ Звёзд: {user_data['stars']}\n"
            f"{premium_text}\n"
            f"💎 Промокод: IRIS666"
        )
        await query.edit_message_text(text, reply_markup=back_button(), parse_mode="Markdown")
        return
    
    # Премиум меню (из кода 2)
    if data == "menu_premium":
        text = "👑 Telegram Premium\n\nВыберите срок подписки:\n"
        for plan_id, plan in PREMIUM_PLANS.items():
            text += f"\n• {plan['name']} - {plan['price']}₽"
        
        buttons = []
        for plan_id in PREMIUM_PLANS.keys():
            buttons.append([InlineKeyboardButton(
                PREMIUM_PLANS[plan_id]["name"], 
                callback_data=f"premium_{plan_id}"
            )])
        buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="menu_main")])
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))
        return
    
    # Обработка выбора премиум тарифа
    if data.startswith("premium_"):
        plan_id = data.replace("premium_", "")
        if plan_id in PREMIUM_PLANS:
            plan = PREMIUM_PLANS[plan_id]
            
            # Создаём заказ
            order_id = f"premium_{datetime.now().strftime('%H%M%S')}"
            db.orders[order_id] = {
                "id": order_id,
                "user_id": user_id,
                "plan": plan_id,
                "price": plan["price"],
                "status": "pending"
            }
            db.save()
            
            text = (
                f"👑 {plan['name']} - {plan['price']}₽\n\n"
                f"Выберите способ оплаты:"
            )
            
            buttons = []
            for method_id, method in PAYMENT_METHODS.items():
                buttons.append([InlineKeyboardButton(
                    method["type"], 
                    callback_data=f"pay_{method_id}_{order_id}"
                )])
            buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="menu_premium")])
            
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))
        return
    
    # Пополнение (из кода 2)
    if data == "menu_deposit":
        text = "💳 Пополнение баланса\n\nВыберите способ:"
        buttons = []
        for method_id, method in PAYMENT_METHODS.items():
            buttons.append([InlineKeyboardButton(method["type"], callback_data=f"deposit_{method_id}")])
        buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="menu_main")])
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))
        return
    
    # Показ реквизитов для пополнения
    if data.startswith("deposit_"):
        method_id = data.replace("deposit_", "")
        method = PAYMENT_METHODS.get(method_id)
        
        if method:
            text = (
                f"{method['type']}\n\n"
                f"```\n{method['details']}\n```\n\n"
                f"📝 В комментарии укажите ваш ID:\n`{user_id}`"
            )
            
            await query.edit_message_text(
                text, 
                reply_markup=back_button(),
                parse_mode="Markdown"
            )
        return
    
    # Калькулятор (объединённый)
    if data == "menu_calc":
        text = "🧮 Калькулятор\n\n"
        
        text += "Покупка:\n"
        for amt in [50, 100, 500, 1000, 5000]:
            text += f"• {amt} звёзд = {amt * STAR_PRICE_BUY:.2f}₽\n"
        
        text += "\nПродажа:\n"
        for amt in [50, 100, 500, 1000, 5000]:
            text += f"• {amt} звёзд = {amt * STAR_PRICE_SELL:.2f}₽\n"
        
        await query.edit_message_text(text, reply_markup=back_button())
        return
    
    # Остальные меню (заглушки)
    if data in ["menu_support", "menu_info"]:
        name = "Поддержка" if data == "menu_support" else "Информация"
        await query.edit_message_text(f"{name} - в разработке 🛠️", reply_markup=back_button())
        return

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ручного ввода количества (из кода 1)"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    # Проверяем состояние пользователя
    state = user_states.get(user_id)
    if not state or not state.startswith("waiting_"):
        return
    
    if not text.isdigit():
        await update.message.reply_text("❌ Введите число!")
        return
    
    amount = int(text)
    
    # Проверка лимитов
    if amount < MIN_STARS:
        await update.message.reply_text(f"❌ Минимум {MIN_STARS} звёзд")
        return
    if amount > MAX_STARS:
        await update.message.reply_text(f"❌ Максимум {MAX_STARS} звёзд")
        return
    
    # Определяем действие
    if "buy" in state:
        action = "buy"
        price = STAR_PRICE_BUY
        action_text = "покупки"
    else:
        action = "sell"
        price = STAR_PRICE_SELL
        action_text = "продажи"
    
    # Очищаем состояние
    user_states.pop(user_id, None)
    
    # Создаём заказ
    await process_stars_order(user_id, update.message.chat_id, action, amount)

async def process_stars_order(user_id, chat_id, action, amount):
    """Обработка заказа звёзд (унифицированная)"""
    price = STAR_PRICE_BUY if action == "buy" else STAR_PRICE_SELL
    total = amount * price
    
    # Создаём заказ в базе
    order_id = f"{action}_{datetime.now().strftime('%H%M%S')}"
    db.orders[order_id] = {
        "id": order_id,
        "user_id": user_id,
        "type": action,
        "amount": amount,
        "total": total,
        "status": "pending",
        "created": datetime.now().isoformat()
    }
    db.save()
    
    # Текст заказа
    action_text = "покупки" if action == "buy" else "продажи"
    order_text = (
        f"✅ Заказ #{order_id}\n\n"
        f"Действие: {action_text} звёзд\n"
        f"Количество: {amount} шт\n"
        f"Цена: {price}₽/шт\n"
        f"Итого: {total:.2f}₽\n\n"
        f"Выберите способ оплаты:"
    )
    
    # Кнопки оплаты
    buttons = []
    for method_id, method in PAYMENT_METHODS.items():
        buttons.append([InlineKeyboardButton(
            method["type"],
            callback_data=f"pay_{method_id}_{order_id}"
        )])
    buttons.append([InlineKeyboardButton("🔙 Отмена", callback_data="menu_main")])
    
    app = Application.builder().token(TOKEN).build()
    await app.bot.send_message(
        chat_id,
        order_text,
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown"
    )
    
    # Уведомление админу
    try:
        await app.bot.send_message(
            ADMIN_ID,
            f"🆕 Новый заказ #{order_id}\n"
            f"👤 {user_id}\n"
            f"⭐ {amount} звёзд ({action_text})\n"
            f"💰 {total:.2f}₽",
            parse_mode="Markdown"
        )
    except:
        pass

# ==================== ЗАПУСК ====================
def main():
    logging.basicConfig(level=logging.INFO)
    
    app = Application.builder().token(TOKEN).build()
    
    # Обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # Запуск
    print("=" * 50)
    print("🤖 УНИФИЦИРОВАННЫЙ БОТ ЗАПУЩЕН")
    print(f"⭐ Покупка: {STAR_PRICE_BUY}₽ | Продажа: {STAR_PRICE_SELL}₽")
    print(f"📦 Лимит: {MIN_STARS}-{MAX_STARS} звёзд")
    print(f"👑 Премиум тарифов: {len(PREMIUM_PLANS)}")
    print(f"💳 Способов оплаты: {len(PAYMENT_METHODS)}")
    print("=" * 50)
    
    app.run_polling()

if __name__ == "__main__":
    main()
