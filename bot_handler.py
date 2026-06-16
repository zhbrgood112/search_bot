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
from message_checker import MessageChecker

class BotHandler:
    def __init__(self, client, settings, blacklist, admin_entity, stats):
        self.client = client
        self.settings = settings
        self.blacklist = blacklist
        self.admin_entity = admin_entity
        self.stats = stats
        
        self.last_send_time = 0
        self.min_interval = 10
        
        self.user_message_cache = defaultdict(dict)
        self.cache_ttl = timedelta(hours=3)
        
        self.chat_cache = {}
        self.last_chat_update = None
        
        self.accounts_manager = None
        self.words_manager = None
        
        self.setup_handlers()
    
    def get_message_hash(self, text, chat_id):
        normalized = ' '.join(text.lower().split())
        return f"{normalized}|{chat_id}"
    
    def should_forward_message(self, user_id, message_hash):
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
        self.user_message_cache.clear()
        print("🗑 Кэш сообщений очищен")
    
    async def update_chat_cache(self):
        try:
            print(f"🔄 Обновление списка чатов...")
            dialogs = await self.client.get_dialogs()
            
            self.chat_cache = {}
            
            for dialog in dialogs:
                chat = dialog.entity
                self.chat_cache[chat.id] = chat
            
            self.last_chat_update = datetime.now()
            
            groups = sum(1 for d in dialogs if d.is_group)
            channels = sum(1 for d in dialogs if d.is_channel)
            users = sum(1 for d in dialogs if d.is_user)
            
            print(f"✅ Обновлено! Всего чатов: {len(dialogs)}")
            return f"✅ Обновлено!\n📊 Всего чатов: {len(dialogs)}\n👥 Групп: {groups}\n📢 Каналов: {channels}\n👤 Личных: {users}"
            
        except Exception as e:
            print(f"❌ Ошибка обновления кэша: {e}")
            return f"❌ Ошибка: {e}"
    
    async def rate_limited_send(self, entity, message):
        now = datetime.now().timestamp()
        time_since_last = now - self.last_send_time
        
        if time_since_last < self.min_interval:
            wait_time = self.min_interval - time_since_last
            print(f"⏳ Ожидание {wait_time:.1f} сек...")
            await asyncio.sleep(wait_time)
        
        result = await self.client.send_message(entity, message)
        self.last_send_time = datetime.now().timestamp()
        return result
    
    async def rate_limited_send_file(self, entity, file, caption=""):
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
        
        @self.client.on(events.NewMessage(chats=self.admin_entity))
        async def admin_commands(event):
            if event.out:
                return
            
            text = event.raw_text.strip().lower()
            reply_msg = await event.get_reply_message() if event.is_reply else None
            
            # ===== БЛОКИРОВКА ОТВЕТОМ =====
            
            if text == "/block_user" and reply_msg:
                user_id = await self.extract_user_id_from_reply(reply_msg)
                if user_id:
                    result, msg = self.blacklist.block_user(user_id)
                    await event.reply(msg)
                    if user_id in self.user_message_cache:
                        del self.user_message_cache[user_id]
                else:
                    await event.reply("❌ Не удалось определить пользователя")
                return
            
            if text == "/unblock_user" and reply_msg:
                user_id = await self.extract_user_id_from_reply(reply_msg)
                if user_id:
                    result, msg = self.blacklist.unblock_user(user_id)
                    await event.reply(msg)
                else:
                    await event.reply("❌ Не удалось определить пользователя")
                return
            
            if text == "/block_chat" and reply_msg:
                chat_id = await self.extract_chat_id_from_reply(reply_msg)
                if chat_id:
                    result, msg = self.blacklist.block_chat(chat_id)
                    await event.reply(msg)
                else:
                    await event.reply("❌ Не удалось определить чат")
                return
            
            if text == "/unblock_chat" and reply_msg:
                chat_id = await self.extract_chat_id_from_reply(reply_msg)
                if chat_id:
                    result, msg = self.blacklist.unblock_chat(chat_id)
                    await event.reply(msg)
                else:
                    await event.reply("❌ Не удалось определить чат")
                return
            
            # ===== БЛОКИРОВКА ПО ID =====
            
            if text.startswith("/block_user "):
                await self.block_user_by_id(text, event)
                return
            
            if text.startswith("/unblock_user "):
                await self.unblock_user_by_id(text, event)
                return
            
            if text.startswith("/block_chat "):
                await self.block_chat_by_id(text, event)
                return
            
            if text.startswith("/unblock_chat "):
                await self.unblock_chat_by_id(text, event)
                return
            
            # ===== ОБНОВЛЕНИЕ ЧАТОВ =====
            
            if text == "/update_chats":
                await event.reply("🔄 Обновляю список чатов...")
                result = await self.update_chat_cache()
                await event.reply(result)
                return
            
            # ===== ОСТАЛЬНЫЕ КОМАНДЫ =====
            
            if text in ["/menu", "меню", "/start"]:
                await self.send_menu(event)
                return
            
            if text in ["/settings", "настройки"]:
                await self.send_settings(event)
                return
            
            if text in ["/blacklist", "blacklist", "/bl", "чс"]:
                await self.send_blacklist(event)
                return
            
            if text in ["/toggle", "/onoff"]:
                status = self.settings.toggle_active()
                await event.reply("✅ Поиск ВКЛЮЧЕН" if status else "⏸ Поиск ВЫКЛЮЧЕН")
                await self.send_settings(event)
                return
            
            if text == "/media":
                status = self.settings.toggle_media()
                await event.reply("✅ Медиа ВКЛЮЧЕНА" if status else "⏸ Медиа ВЫКЛЮЧЕНА")
                return
            
            if text in ["/stats", "статистика"]:
                await self.send_stats(event)
                return
            
            if text == "/reset":
                self.stats["total"] = 0
                self.stats["last_reset"] = datetime.now()
                self.stats["pairs"] = {}
                self.clean_all_cache()
                await event.reply("📊 Статистика и кэш сброшены")
                return
            
            if text in ["/help", "help"]:
                await self.send_help(event)
                return
            
            if text == "/clear_cache":
                self.clean_all_cache()
                await event.reply("🗑 Кэш одинаковых сообщений очищен")
                return
            
            if text == "/cache_stats":
                total_users = len(self.user_message_cache)
                total_messages = sum(len(msgs) for msgs in self.user_message_cache.values())
                await event.reply(f"📊 **Статистика кэша:**\n\n"
                                 f"👤 Пользователей в кэше: {total_users}\n"
                                 f"💬 Запомнено сообщений: {total_messages}\n"
                                 f"⏰ TTL: 3 часа")
                return
        
        # ===== ОСНОВНОЙ ОБРАБОТЧИК СООБЩЕНИЙ =====
        @self.client.on(events.NewMessage)
        async def search_handler(event):
            await asyncio.sleep(10)
            
            if event.out:
                return
            
            if not self.settings.settings["active"]:
                return
            
            if event.chat_id == self.admin_entity.id:
                return
            
            try:
                chat = await event.get_chat()
            except Exception as e:
                print(f"⚠️ Ошибка получения чата: {e}")
                return
            
            sender = await event.get_sender()
            message = event.message
            
            if self.blacklist.is_chat_blocked(event.chat_id):
                return
            
            if sender and self.blacklist.is_user_blocked(sender.id):
                return
            
            text = message.text or ""
            if not text and not message.media:
                return
            
            # ИСПОЛЬЗУЕМ КЛАСС MessageChecker
            if self.words_manager:
                checker = MessageChecker(self.words_manager)
                is_match, word1, word2, matches = checker.check_message(text)
            else:
                # Если words_manager нет - создаем временный
                from words_manager import WordsManager
                temp_words = WordsManager()
                checker = MessageChecker(temp_words)
                is_match, word1, word2, matches = checker.check_message(text)
            
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
                
                # Подсвечиваем найденные слова
                if self.words_manager:
                    highlighted_text = checker.highlight_matches(text, matches) if text else "[Медиафайл]"
                else:
                    highlighted_text = text if text else "[Медиафайл]"
                
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
    
    # ===== ФУНКЦИИ ДЛЯ ИЗВЛЕЧЕНИЯ ID =====
    
    async def extract_user_id_from_reply(self, reply_msg):
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
    
    async def extract_chat_id_from_reply(self, reply_msg):
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
    
    # ===== ФУНКЦИИ БЛОКИРОВКИ =====
    
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