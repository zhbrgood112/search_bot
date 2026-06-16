# bot_handler.py
import re
import asyncio
from datetime import datetime, timedelta
from collections import defaultdict
from telethon import events
from message_formatter import (
    format_forward_message, format_settings_message, 
    format_stats_message, format_help_message, format_menu_message,
    format_blacklist_message,
    get_chat_name, get_sender_info, get_chat_link
)
from message_checker import check_message, highlight_matches

class BotHandler:
    def __init__(self, client, settings, blacklist, admin_entity, stats):
        self.client = client
        self.settings = settings
        self.blacklist = blacklist
        self.admin_entity = admin_entity
        self.stats = stats
        
        # Для контроля частоты отправки
        self.last_send_time = 0
        self.min_interval = 10  # Минимум 10 секунд между отправками
        
        # Кэш для одинаковых сообщений от пользователей
        self.user_message_cache = defaultdict(dict)
        self.cache_ttl = timedelta(hours=3)  # 3 часа жизни кэша
        
        # Кэш чатов
        self.chat_cache = {}
        self.last_chat_update = None
        
        # Регистрируем обработчики
        self.setup_handlers()
    
    def get_message_hash(self, text, chat_id):
        """Создает хэш сообщения для сравнения (текст + чат)"""
        normalized = ' '.join(text.lower().split())
        return f"{normalized}|{chat_id}"
    
    def should_forward_message(self, user_id, message_hash):
        """Проверяет, нужно ли пересылать сообщение"""
        user_cache = self.user_message_cache.get(user_id, {})
        
        if message_hash in user_cache:
            last_sent = user_cache[message_hash]
            time_passed = datetime.now() - last_sent
            
            if time_passed < self.cache_ttl:
                hours_left = (self.cache_ttl - time_passed).seconds / 3600
                print(f"⏸ Пропущено дубликат от {user_id}: следующее через {hours_left:.1f}ч")
                return False
        
        if user_id not in self.user_message_cache:
            self.user_message_cache[user_id] = {}
        self.user_message_cache[user_id][message_hash] = datetime.now()
        
        self.clean_old_cache(user_id)
        return True
    
    def clean_old_cache(self, user_id):
        """Очищает старые записи пользователя"""
        if user_id in self.user_message_cache:
            now = datetime.now()
            to_delete = []
            for msg_hash, sent_time in self.user_message_cache[user_id].items():
                if now - sent_time >= self.cache_ttl:
                    to_delete.append(msg_hash)
            
            for msg_hash in to_delete:
                del self.user_message_cache[user_id][msg_hash]
            
            if not self.user_message_cache[user_id]:
                del self.user_message_cache[user_id]
    
    def clean_all_cache(self):
        """Очищает весь кэш"""
        self.user_message_cache.clear()
        print("🗑 Кэш сообщений очищен")
    
    async def update_chat_cache(self):
        """Обновляет кэш чатов (ручной вызов)"""
        try:
            print(f"🔄 Обновление списка чатов...")
            
            dialogs = await self.client.get_dialogs()
            
            old_count = len(self.chat_cache)
            added_chats = []
            
            for dialog in dialogs:
                chat = dialog.entity
                chat_id = chat.id
                
                if chat_id not in self.chat_cache:
                    self.chat_cache[chat_id] = chat
                    chat_name = get_chat_name(chat)
                    added_chats.append(chat_name)
            
            self.last_chat_update = datetime.now()
            
            if added_chats:
                print(f"✅ Добавлено новых чатов: {len(added_chats)}")
                for name in added_chats[:5]:
                    print(f"   • {name}")
                if len(added_chats) > 5:
                    print(f"   ... и еще {len(added_chats)-5}")
                return f"✅ Обновлено! Добавлено {len(added_chats)} новых чатов. Всего: {len(self.chat_cache)}"
            else:
                print(f"✅ Чаты обновлены. Всего: {len(self.chat_cache)} чатов (новых нет)")
                return f"✅ Обновлено! Всего чатов: {len(self.chat_cache)} (новых не найдено)"
            
        except Exception as e:
            print(f"❌ Ошибка обновления кэша чатов: {e}")
            return f"❌ Ошибка: {e}"
    
    async def get_chat_entity(self, chat_id):
        """Получает сущность чата из кэша"""
        if chat_id in self.chat_cache:
            return self.chat_cache[chat_id]
        return None
    
    async def rate_limited_send(self, entity, message):
        """Отправка с ограничением частоты"""
        now = datetime.now().timestamp()
        time_since_last = now - self.last_send_time
        
        if time_since_last < self.min_interval:
            wait_time = self.min_interval - time_since_last
            print(f"⏳ Ожидание {wait_time:.1f} сек перед следующей отправкой...")
            await asyncio.sleep(wait_time)
        
        result = await self.client.send_message(entity, message)
        self.last_send_time = datetime.now().timestamp()
        return result
    
    async def rate_limited_send_file(self, entity, file, caption=""):
        """Отправка файла с ограничением частоты"""
        now = datetime.now().timestamp()
        time_since_last = now - self.last_send_time
        
        if time_since_last < self.min_interval:
            wait_time = self.min_interval - time_since_last
            print(f"⏳ Ожидание {wait_time:.1f} сек перед отправкой медиа...")
            await asyncio.sleep(wait_time)
        
        result = await self.client.send_file(entity, file, caption=caption)
        self.last_send_time = datetime.now().timestamp()
        return result
    
    def setup_handlers(self):
        """Настраивает обработчики событий"""
        
        @self.client.on(events.NewMessage(chats=self.admin_entity))
        async def admin_commands(event):
            if event.out:
                return
            
            text = event.raw_text.strip().lower()
            reply_msg = await event.get_reply_message() if event.is_reply else None
            
            # ===== БЛОКИРОВКА ОТВЕТОМ НА СООБЩЕНИЕ =====
            
            if text == "/block_user" and reply_msg:
                user_id = await self.extract_user_id_from_reply(reply_msg)
                if user_id:
                    result, msg = self.blacklist.block_user(user_id)
                    await event.reply(msg)
                    if user_id in self.user_message_cache:
                        del self.user_message_cache[user_id]
                else:
                    await event.reply("❌ Не удалось определить пользователя. Используйте: /block_user ID")
                return
            
            elif text == "/unblock_user" and reply_msg:
                user_id = await self.extract_user_id_from_reply(reply_msg)
                if user_id:
                    result, msg = self.blacklist.unblock_user(user_id)
                    await event.reply(msg)
                else:
                    await event.reply("❌ Не удалось определить пользователя. Используйте: /unblock_user ID")
                return
            
            elif text == "/block_chat" and reply_msg:
                chat_id = await self.extract_chat_id_from_reply(reply_msg, event)
                if chat_id:
                    result, msg = self.blacklist.block_chat(chat_id)
                    await event.reply(msg)
                else:
                    await event.reply("❌ Не удалось определить чат. Используйте: /block_chat ID")
                return
            
            elif text == "/unblock_chat" and reply_msg:
                chat_id = await self.extract_chat_id_from_reply(reply_msg, event)
                if chat_id:
                    result, msg = self.blacklist.unblock_chat(chat_id)
                    await event.reply(msg)
                else:
                    await event.reply("❌ Не удалось определить чат. Используйте: /unblock_chat ID")
                return
            
            # ===== БЛОКИРОВКА С УКАЗАНИЕМ ID =====
            
            elif text.startswith("/block_user "):
                await self.block_user_by_id(text, event)
                return
            
            elif text.startswith("/unblock_user "):
                await self.unblock_user_by_id(text, event)
                return
            
            elif text.startswith("/block_chat "):
                await self.block_chat_by_id(text, event)
                return
            
            elif text.startswith("/unblock_chat "):
                await self.unblock_chat_by_id(text, event)
                return
            
            # ===== УПРАВЛЕНИЕ ЧАТАМИ =====
            
            # Принудительно обновить чаты
            elif text == "/update_chats":
                msg = await self.update_chat_cache()
                await event.reply(msg)
                return
            
            # Показать список чатов
            elif text == "/list_chats":
                await self.send_chat_list(event)
                return
            
            # ===== УПРАВЛЕНИЕ КЭШЕМ =====
            
            elif text == "/clear_cache":
                self.clean_all_cache()
                await event.reply("🗑 Кэш одинаковых сообщений очищен")
                return
            
            elif text == "/cache_stats":
                total_users = len(self.user_message_cache)
                total_messages = sum(len(msgs) for msgs in self.user_message_cache.values())
                await event.reply(f"📊 **Статистика кэша:**\n\n"
                                 f"👤 Пользователей в кэше: {total_users}\n"
                                 f"💬 Запомнено сообщений: {total_messages}\n"
                                 f"⏰ TTL: 3 часа")
                return
            
            # ===== ОСТАЛЬНЫЕ КОМАНДЫ =====
            
            elif text in ["/menu", "меню", "/start"]:
                await self.send_menu(event)
            
            elif text in ["/settings", "настройки"]:
                await self.send_settings(event)
            
            elif text in ["/blacklist", "blacklist", "/bl", "чс"]:
                await self.send_blacklist(event)
            
            elif text in ["/toggle", "/onoff"]:
                status = self.settings.toggle_active()
                await event.reply("✅ Поиск ВКЛЮЧЕН" if status else "⏸ Поиск ВЫКЛЮЧЕН")
                await self.send_settings(event)
            
            elif text == "/media":
                status = self.settings.toggle_media()
                await event.reply("✅ Медиа ВКЛЮЧЕНА" if status else "⏸ Медиа ВЫКЛЮЧЕНА")
            
            elif text in ["/stats", "статистика"]:
                await self.send_stats(event)
            
            elif text == "/reset":
                self.stats["total"] = 0
                self.stats["last_reset"] = datetime.now()
                self.stats["pairs"] = {}
                self.clean_all_cache()
                await event.reply("📊 Статистика и кэш сброшены")
            
            elif text in ["/help", "help"]:
                await self.send_help(event)
        
        # ОСНОВНОЙ ОБРАБОТЧИК СООБЩЕНИЙ
        @self.client.on(events.NewMessage)
        async def search_handler(event):
            await asyncio.sleep(10)
            
            if event.out:
                return
            
            if not self.settings.settings["active"]:
                return
            
            if event.chat_id == self.admin_entity.id:
                return
            
            # Проверяем, есть ли чат в кэше
            chat = await self.get_chat_entity(event.chat_id)
            if chat is None:
                # Если чата нет в кэше, пропускаем (пользователь должен обновить вручную)
                print(f"⚠️ Чат {event.chat_id} не найден в кэше. Используйте /update_chats")
                return
            
            sender = await event.get_sender()
            message = event.message
            
            # Проверка блокировок
            if self.blacklist.is_chat_blocked(event.chat_id):
                return
            
            if sender and self.blacklist.is_user_blocked(sender.id):
                return
            
            text = message.text or ""
            if not text and not message.media:
                return
            
            is_match, word1, word2, matches = check_message(text)
            
            if is_match:
                user_id = sender.id if sender else 0
                message_hash = self.get_message_hash(text, event.chat_id)
                
                if not self.should_forward_message(user_id, message_hash):
                    return
                
                self.stats["total"] += 1
                
                pair_key = f"{word1}+{word2}"
                if "pairs" not in self.stats:
                    self.stats["pairs"] = {}
                self.stats["pairs"][pair_key] = self.stats["pairs"].get(pair_key, 0) + 1
                
                chat_name = get_chat_name(chat)
                chat_id = event.chat_id
                sender_info = get_sender_info(sender)
                sender_id = sender.id if sender else 0
                chat_link = get_chat_link(chat, message)
                
                highlighted_text = highlight_matches(text, matches) if text else "[Медиафайл]"
                
                forward_text = format_forward_message(
                    chat_name=chat_name,
                    chat_id=chat_id,
                    sender_info=sender_info,
                    sender_id=sender_id,
                    text=highlighted_text,
                    chat_link=chat_link,
                    event_date=event.date,
                    word1=word1,
                    word2=word2
                )
                
                try:
                    await self.rate_limited_send(self.admin_entity, forward_text)
                    
                    if message.media and self.settings.settings["forward_media"]:
                        try:
                            await self.rate_limited_send_file(self.admin_entity, message.media,
                                                              caption=f"📎 {chat_name}")
                        except:
                            pass
                    
                    user_cache_count = len(self.user_message_cache.get(user_id, {}))
                    print(f"✅ [{self.stats['total']}] {chat_name[:30]} → {word1}+{word2} (кэш пользователя: {user_cache_count} сообщений)")
                    
                except Exception as e:
                    print(f"❌ Ошибка: {e}")
    
    # ===== СПИСОК ЧАТОВ =====
    
    async def send_chat_list(self, event):
        """Отправляет список чатов"""
        if not self.chat_cache:
            await event.reply("🔄 Кэш чатов пуст. Используйте /update_chats")
            return
        
        chats = list(self.chat_cache.values())
        
        if not chats:
            await event.reply("❌ Чаты не найдены")
            return
        
        groups = []
        channels = []
        users = []
        
        for chat in chats:
            chat_name = get_chat_name(chat)
            chat_id = chat.id
            
            if hasattr(chat, 'megagroup') and chat.megagroup:
                groups.append(f"  • {chat_name} (ID: {chat_id})")
            elif hasattr(chat, 'group') and chat.group:
                groups.append(f"  • {chat_name} (ID: {chat_id})")
            elif hasattr(chat, 'channel') and chat.channel:
                channels.append(f"  • {chat_name} (ID: {chat_id})")
            else:
                users.append(f"  • {chat_name} (ID: {chat_id})")
        
        result = f"""
📋 **СПИСОК ЧАТОВ** ({len(chats)} всего)

👥 **Группы ({len(groups)}):**
{chr(10).join(groups[:20]) if groups else '  • нет'}
{f'  ... и еще {len(groups)-20}' if len(groups) > 20 else ''}

📢 **Каналы ({len(channels)}):**
{chr(10).join(channels[:20]) if channels else '  • нет'}
{f'  ... и еще {len(channels)-20}' if len(channels) > 20 else ''}

👤 **Личные чаты ({len(users)}):**
{chr(10).join(users[:10]) if users else '  • нет'}
{f'  ... и еще {len(users)-10}' if len(users) > 10 else ''}

💡 /update_chats - обновить список чатов
"""
        await event.reply(result[:4000])
    
    # ===== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ =====
    
    async def extract_user_id_from_reply(self, reply_msg):
        """Извлекает ID пользователя из ответного сообщения"""
        try:
            username_match = re.search(r'@(\w+)', reply_msg.raw_text)
            if username_match:
                username = username_match.group(1)
                try:
                    entity = await self.client.get_entity(f"@{username}")
                    return entity.id
                except:
                    pass
            
            id_match = re.search(r'Sender ID:\s*(\d+)|ID:\s*(\d+)', reply_msg.raw_text)
            if id_match:
                user_id = id_match.group(1) or id_match.group(2)
                if user_id:
                    return int(user_id)
            
            if reply_msg.sender_id:
                return reply_msg.sender_id
            
            return None
        except Exception as e:
            print(f"Ошибка извлечения ID пользователя: {e}")
            return None
    
    async def extract_chat_id_from_reply(self, reply_msg, event):
        """Извлекает ID чата из ответного сообщения"""
        try:
            id_match = re.search(r'Chat ID:\s*([-\d]+)', reply_msg.raw_text)
            if id_match:
                return int(id_match.group(1))
            
            if reply_msg.chat_id:
                return reply_msg.chat_id
            
            return None
        except Exception as e:
            print(f"Ошибка извлечения ID чата: {e}")
            return None
    
    async def block_user_by_id(self, text, event):
        try:
            parts = text.split()
            if len(parts) < 2:
                await event.reply("❌ Использование: /block_user 123456789")
                return
            user_id = int(parts[1])
            result, msg = self.blacklist.block_user(user_id)
            await event.reply(msg)
            if user_id in self.user_message_cache:
                del self.user_message_cache[user_id]
        except ValueError:
            await event.reply("❌ ID должен быть числом. Пример: /block_user 123456789")
        except Exception as e:
            await event.reply(f"❌ Ошибка: {e}")
    
    async def unblock_user_by_id(self, text, event):
        try:
            parts = text.split()
            if len(parts) < 2:
                await event.reply("❌ Использование: /unblock_user 123456789")
                return
            user_id = int(parts[1])
            result, msg = self.blacklist.unblock_user(user_id)
            await event.reply(msg)
        except ValueError:
            await event.reply("❌ ID должен быть числом. Пример: /unblock_user 123456789")
        except Exception as e:
            await event.reply(f"❌ Ошибка: {e}")
    
    async def block_chat_by_id(self, text, event):
        try:
            parts = text.split()
            if len(parts) < 2:
                await event.reply("❌ Использование: /block_chat -100123456789")
                return
            chat_id = int(parts[1])
            result, msg = self.blacklist.block_chat(chat_id)
            await event.reply(msg)
        except ValueError:
            await event.reply("❌ ID чата должен быть числом. Пример: /block_chat -100123456789")
        except Exception as e:
            await event.reply(f"❌ Ошибка: {e}")
    
    async def unblock_chat_by_id(self, text, event):
        try:
            parts = text.split()
            if len(parts) < 2:
                await event.reply("❌ Использование: /unblock_chat -100123456789")
                return
            chat_id = int(parts[1])
            result, msg = self.blacklist.unblock_chat(chat_id)
            await event.reply(msg)
        except ValueError:
            await event.reply("❌ ID чата должен быть числом. Пример: /unblock_chat -100123456789")
        except Exception as e:
            await event.reply(f"❌ Ошибка: {e}")
    
    # ===== ОТПРАВКА СООБЩЕНИЙ =====
    
    async def send_menu(self, event):
        menu = format_menu_message(self.settings.settings["active"])
        await event.reply(menu)
    
    async def send_settings(self, event):
        settings_text = format_settings_message(
            self.settings.settings["active"],
            self.settings.settings["forward_media"],
            self.blacklist
        )
        await event.reply(settings_text)
    
    async def send_blacklist(self, event):
        blacklist_text = format_blacklist_message(self.blacklist)
        await event.reply(blacklist_text)
    
    async def send_stats(self, event):
        top_pairs = None
        if "pairs" in self.stats and self.stats["pairs"]:
            top_pairs = dict(sorted(self.stats["pairs"].items(), 
                                    key=lambda x: x[1], reverse=True)[:5])
        
        stats_text = format_stats_message(
            self.stats["total"],
            self.stats["last_reset"],
            top_pairs
        )
        await event.reply(stats_text)
    
    async def send_help(self, event):
        help_text = format_help_message()
        await event.reply(help_text)