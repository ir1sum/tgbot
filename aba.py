#!/usr/bin/env python3
import asyncio
from telegram import Bot

TOKEN = "8196751032:AAGwizPBRuq_uh0zd9GQ6C2BFiseAfnp_xo"
ADMIN_ID = 741906407

async def main():
    bot = Bot(token=TOKEN)
    
    # 1. Проверка подключения
    me = await bot.get_me()
    print(f"✅ Бот: @{me.username}")
    
    # 2. Отправка тестового сообщения тебе
    await bot.send_message(
        ADMIN_ID,
        "🤖 Бот работает!\n"
        "Отправь /start в бота для проверки"
    )
    print("✅ Тестовое сообщение отправлено")
    
    # 3. Ожидание сообщений
    print("🔄 Ожидаю сообщения...")
    offset = 0
    
    while True:
        try:
            updates = await bot.get_updates(offset=offset, timeout=30)
            
            for update in updates:
                offset = update.update_id + 1
                
                if update.message:
                    user = update.message.from_user
                    text = update.message.text
                    
                    print(f"📩 От {user.first_name}: {text}")
                    
                    if text == "/start":
                        await update.message.reply_text(f"Привет, {user.first_name}!")
                    
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            await asyncio.sleep(5)

asyncio.run(main())
