# message_formatter.py
from datetime import datetime
import config

def format_forward_message(chat_name, chat_id, sender_info, sender_id, text, chat_link, event_date, word1, word2):
    """
    Форматирует сообщение для пересылки (минимальная версия без подсказок)
    """
    time_str = event_date.strftime(config.TIME_FORMAT)
    
    if len(text) > config.MAX_MESSAGE_LENGTH:
        text = text[:config.MAX_MESSAGE_LENGTH] + "..."
    
    if not text:
        text = "[Медиафайл без текста]"
    
    message = f"""
📌 {chat_name}
👤 {sender_info} | {time_str}

{text}

🔗 {chat_link}
"""
    return message.strip()


def format_help_message():
    """Форматирует сообщение с помощью"""
    return f"""
🔍 ПОИСКОВИКБОТ - ПОМОЩЬ

🚫 БЛОКИРОВКИ (САМЫЙ УДОБНЫЙ СПОСОБ):
   
   1. Нажмите на сообщение от бота
   2. Выберите "Ответить"
   3. Напишите команду:
   
   /block_user    - заблокировать пользователя
   /unblock_user  - разблокировать пользователя
   /block_chat    - заблокировать чат
   /unblock_chat  - разблокировать чат

📌 ТАКЖЕ РАБОТАЕТ:
   /block_user 123456789    - блокировка по ID
   /block_chat -100123456789 - блокировка чата по ID
   /blacklist               - показать черный список

🔄 УПРАВЛЕНИЕ ДУБЛИКАТАМИ:
   Одинаковые сообщения от пользователя
   приходят не чаще 1 раза в 3 часа
   
   /clear_cache  - очистить кэш одинаковых сообщений
   /cache_stats  - показать статистику кэша

⚙️ ДРУГИЕ КОМАНДЫ:
/toggle    - вкл/выкл поиск
/media     - вкл/выкл медиа
/settings  - настройки
/stats     - статистика
/reset     - сбросить статистику
/menu      - главное меню
/help      - эта справка
"""


def format_menu_message(active):
    """Форматирует главное меню"""
    status = "🟢 АКТИВЕН" if active else "🔴 ОСТАНОВЛЕН"
    
    return f"""
🔍 ПОИСКОВИКБОТ - МЕНЮ

Статус: {status}

🚫 БЛОКИРОВКИ (ответом на сообщение):
   /block_user    - заблокировать пользователя
   /unblock_user  - разблокировать
   /block_chat    - заблокировать чат
   /unblock_chat  - разблокировать

🔄 ЗАЩИТА ОТ ДУБЛИКАТОВ:
   Одинаковые сообщения от пользователя
   приходят не чаще 1 раза в 3 часа
   
   /clear_cache  - очистить кэш
   /cache_stats  - статистика кэша

📌 ИЛИ ПО ID:
   /block_user <ID>
   /block_chat <ID>
   /blacklist - показать черный список

⚙️ Другие команды:
/toggle    - вкл/выкл
/media     - медиа вкл/выкл
/settings  - настройки
/stats     - статистика
/reset     - сброс
/help      - помощь
"""


def format_blacklist_message(blacklist_manager):
    """Форматирует сообщение с черным списком"""
    users = blacklist_manager.get_blocked_users()
    chats = blacklist_manager.get_blocked_chats()
    
    result = f"""
🚫 ЧЕРНЫЙ СПИСОК

👤 Заблокировано пользователей: {len(users)}
📝 Заблокировано чатов: {len(chats)}
"""
    
    if users:
        result += "\n👤 Пользователи:\n"
        for user in users[:15]:
            name = user.get('username') or user.get('name') or user['id']
            result += f"  • {name}\n"
        if len(users) > 15:
            result += f"  ... и еще {len(users)-15}\n"
    
    if chats:
        result += "\n📝 Чаты:\n"
        for chat in chats[:15]:
            name = chat.get('name') or chat['id']
            result += f"  • {name}\n"
        if len(chats) > 15:
            result += f"  ... и еще {len(chats)-15}\n"
    
    return result


def format_settings_message(active, forward_media, blacklist_manager):
    """Форматирует сообщение с настройками"""
    status = "🟢 Включен" if active else "🔴 Выключен"
    media_status = "📎 Включена" if forward_media else "⏸ Выключена"
    
    blocked_users = len(blacklist_manager.get_blocked_users())
    blocked_chats = len(blacklist_manager.get_blocked_chats())
    
    return f"""
⚙️ НАСТРОЙКИ

Статус: {status}
Медиа: {media_status}

🚫 Черный список:
   Пользователей: {blocked_users}
   Чатов: {blocked_chats}

🔍 Столбец 1: {len(config.COLUMN_1)} слов
👤 Столбец 2: {len(config.COLUMN_2)} слов

📌 Правило: слово из 1-го И слово из 2-го

🔄 Защита от дубликатов: 3 часа
"""


def format_stats_message(total, last_reset, top_pairs=None):
    """Форматирует сообщение со статистикой"""
    from datetime import datetime
    uptime = datetime.now() - last_reset
    hours = uptime.seconds // 3600
    minutes = (uptime.seconds % 3600) // 60
    
    result = f"""
📊 СТАТИСТИКА

Найдено совпадений: {total}
Время работы: {hours}ч {minutes}мин
"""
    
    if top_pairs:
        result += "\n🏆 Частые пары:\n"
        for pair, count in list(top_pairs.items())[:5]:
            result += f"  • {pair}: {count}\n"
    
    return result


def get_chat_name(chat):
    """Возвращает название чата"""
    if hasattr(chat, 'title') and chat.title:
        return chat.title
    elif hasattr(chat, 'first_name'):
        name = chat.first_name
        if hasattr(chat, 'last_name') and chat.last_name:
            name += f" {chat.last_name}"
        return name
    return f"Чат #{chat.id}"


def get_sender_info(sender):
    """Возвращает информацию об отправителе"""
    if not sender:
        return "Неизвестно"
    
    if hasattr(sender, 'username') and sender.username:
        return f"@{sender.username}"
    
    if hasattr(sender, 'first_name'):
        name = sender.first_name
        if hasattr(sender, 'last_name') and sender.last_name:
            name += f" {sender.last_name}"
        return name
    
    return f"ID:{sender.id}"


def get_chat_link(chat, message):
    """Генерирует ссылку на сообщение"""
    try:
        if hasattr(chat, 'username') and chat.username:
            return f"t.me/{chat.username}/{message.id}"
        else:
            chat_id = str(chat.id)
            if chat_id.startswith('-100'):
                chat_id = chat_id[4:]
            return f"t.me/c/{chat_id}/{message.id}"
    except:
        return "ссылка недоступна"