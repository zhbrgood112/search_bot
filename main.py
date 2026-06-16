# main.py
import asyncio
from datetime import datetime
from telethon import TelegramClient

import config
from settings_manager import SettingsManager
from blacklist_manager import BlacklistManager
from bot_handler import BotHandler
from message_formatter import get_chat_name, format_menu_message, format_help_message

async def main():
    print("=" * 60)
    print("🔍 ПОИСКОВИКБОТ")
    print("=" * 60)
    
    client = TelegramClient(config.SESSION_FILE, config.API_ID, config.API_HASH)
    settings = SettingsManager(config.SETTINGS_FILE)
    blacklist = BlacklistManager(config.BLACKLIST_FILE)
    
    phone = input("📱 Введите номер телефона (+79991234567): ").strip()
    await client.start(phone=phone)
    
    print("\n✅ Авторизация успешна!")
    me = await client.get_me()
    print(f"👤 Аккаунт: {me.first_name} (@{me.username})")
    
    try:
        admin_entity = await client.get_entity(config.ADMIN_CHAT)
        admin_chat_name = get_chat_name(admin_entity)
        print(f"📨 Чат управления: {admin_chat_name}")
        
        # ОТПРАВЛЯЕМ ТОЛЬКО СПИСОК КОМАНД
        await client.send_message(admin_entity, "🤖 ПоисковикБот запущен!")
        
        # Отправляем список всех команд
        commands = """
📋 **ДОСТУПНЫЕ КОМАНДЫ:**

🚫 **Блокировки:**
   /block_user <ID>     - заблокировать пользователя
   /unblock_user <ID>   - разблокировать пользователя
   /block_chat <ID>     - заблокировать чат
   /unblock_chat <ID>   - разблокировать чат
   (можно использовать ответом на сообщение)

🔄 **Чаты:**
   /update_chats        - обновить список чатов
   /list_chats          - показать все чаты

🔄 **Кэш дубликатов:**
   /clear_cache         - очистить кэш
   /cache_stats         - статистика кэша

⚙️ **Управление:**
   /toggle              - вкл/выкл поиск
   /media               - вкл/выкл пересылку медиа
   /settings            - показать настройки
   /stats               - статистика
   /reset               - сбросить статистику
   /blacklist           - показать черный список

ℹ️ **Информация:**
   /menu                - главное меню
   /help                - подробная справка

📌 **Важно:**
   • Одинаковые сообщения от пользователя приходят не чаще 1 раза в 3 часа
   • Задержка между отправками: 10 секунд
   • Поиск работает во всех чатах
"""
        await client.send_message(admin_entity, commands)
        
        print("\n📋 Команды отправлены в чат управления")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        await client.disconnect()
        return
    
    stats = {
        "total": 0,
        "last_reset": datetime.now(),
        "pairs": {}
    }
    
    handler = BotHandler(client, settings, blacklist, admin_entity, stats)
    
    print("\n" + "=" * 60)
    print("🔍 ПОИСКОВИКБОТ ЗАПУЩЕН")
    print(f"📨 Управление через: {admin_chat_name}")
    print("\n📋 ОСНОВНЫЕ КОМАНДЫ:")
    print("   /update_chats - обновить список чатов")
    print("   /list_chats   - список чатов")
    print("   /menu         - меню")
    print("   /settings     - настройки")
    print("=" * 60 + "\n")
    
    await client.run_until_disconnected()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 ПоисковикБот остановлен")
    except Exception as e:
        print(f"❌ Ошибка: {e}")