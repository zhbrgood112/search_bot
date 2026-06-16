# blacklist_manager.py
import json
import os
from datetime import datetime

class BlacklistManager:
    def __init__(self, filename):
        self.filename = filename
        self.blacklist = self.load()
    
    def load(self):
        """Загружает черный список из файла"""
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {
            "users": [],      # Заблокированные пользователи (ID или username)
            "chats": [],      # Заблокированные чаты (ID или название)
            "blocked_messages": []  # История блокировок
        }
    
    def save(self):
        """Сохраняет черный список в файл"""
        with open(self.filename, 'w', encoding='utf-8') as f:
            json.dump(self.blacklist, f, ensure_ascii=False, indent=2)
    
    def block_user(self, user_id, username=None, name=None, reason=None):
        """Блокирует пользователя"""
        user_info = {
            "id": user_id,
            "username": username,
            "name": name,
            "reason": reason,
            "blocked_at": datetime.now().strftime('%d.%m.%Y %H:%M:%S')
        }
        
        # Проверяем, не заблокирован ли уже
        for user in self.blacklist["users"]:
            if user["id"] == user_id:
                return False, "Пользователь уже в черном списке"
        
        self.blacklist["users"].append(user_info)
        self.blacklist["blocked_messages"].append({
            "type": "user",
            "action": "block",
            "target": user_info,
            "time": datetime.now().strftime('%d.%m.%Y %H:%M:%S')
        })
        self.save()
        return True, f"Пользователь {username or name or user_id} заблокирован"
    
    def unblock_user(self, user_id):
        """Разблокирует пользователя"""
        for i, user in enumerate(self.blacklist["users"]):
            if user["id"] == user_id:
                removed = self.blacklist["users"].pop(i)
                self.blacklist["blocked_messages"].append({
                    "type": "user",
                    "action": "unblock",
                    "target": removed,
                    "time": datetime.now().strftime('%d.%m.%Y %H:%M:%S')
                })
                self.save()
                return True, f"Пользователь {removed.get('username') or removed.get('name') or user_id} разблокирован"
        return False, "Пользователь не найден в черном списке"
    
    def block_chat(self, chat_id, chat_name=None, reason=None):
        """Блокирует чат"""
        chat_info = {
            "id": chat_id,
            "name": chat_name,
            "reason": reason,
            "blocked_at": datetime.now().strftime('%d.%m.%Y %H:%M:%S')
        }
        
        for chat in self.blacklist["chats"]:
            if chat["id"] == chat_id:
                return False, "Чат уже в черном списке"
        
        self.blacklist["chats"].append(chat_info)
        self.blacklist["blocked_messages"].append({
            "type": "chat",
            "action": "block",
            "target": chat_info,
            "time": datetime.now().strftime('%d.%m.%Y %H:%M:%S')
        })
        self.save()
        return True, f"Чат {chat_name or chat_id} заблокирован"
    
    def unblock_chat(self, chat_id):
        """Разблокирует чат"""
        for i, chat in enumerate(self.blacklist["chats"]):
            if chat["id"] == chat_id:
                removed = self.blacklist["chats"].pop(i)
                self.blacklist["blocked_messages"].append({
                    "type": "chat",
                    "action": "unblock",
                    "target": removed,
                    "time": datetime.now().strftime('%d.%m.%Y %H:%M:%S')
                })
                self.save()
                return True, f"Чат {removed.get('name') or chat_id} разблокирован"
        return False, "Чат не найден в черном списке"
    
    def is_user_blocked(self, user_id):
        """Проверяет, заблокирован ли пользователь"""
        for user in self.blacklist["users"]:
            if user["id"] == user_id:
                return True
        return False
    
    def is_chat_blocked(self, chat_id):
        """Проверяет, заблокирован ли чат"""
        for chat in self.blacklist["chats"]:
            if chat["id"] == chat_id:
                return True
        return False
    
    def get_blocked_users(self):
        """Возвращает список заблокированных пользователей"""
        return self.blacklist["users"]
    
    def get_blocked_chats(self):
        """Возвращает список заблокированных чатов"""
        return self.blacklist["chats"]
    
    def get_blacklist_summary(self):
        """Возвращает краткую сводку черного списка"""
        users = self.get_blocked_users()
        chats = self.get_blocked_chats()
        
        summary = f"""
{'═' * 35}
🚫 ЧЕРНЫЙ СПИСОК
{'═' * 35}

👤 Заблокировано пользователей: {len(users)}
📝 Заблокировано чатов: {len(chats)}
"""
        if users:
            summary += "\n👤 Пользователи:\n"
            for user in users[:10]:
                name = user.get('username') or user.get('name') or user['id']
                summary += f"  • {name}\n"
            if len(users) > 10:
                summary += f"  ... и еще {len(users)-10}\n"
        
        if chats:
            summary += "\n📝 Чаты:\n"
            for chat in chats[:10]:
                name = chat.get('name') or chat['id']
                summary += f"  • {name}\n"
            if len(chats) > 10:
                summary += f"  ... и еще {len(chats)-10}\n"
        
        summary += f"{'═' * 35}"
        return summary