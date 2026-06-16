# words_manager.py
import json
import os

DEFAULT_COLUMN_1 = [
    "куплю", "дайте", "роспишите", "роспись", "автограф", 
    "подпись", "активируйте", "активация", "активацию", 
    "косключ", "gk", "заберу", "приму", "принимаю",
    "подписать", "скупаю",
    # НОВЫЕ СЛОВА:
    "приобрету",
    "скуплю",
    "выкуплю",
    "забираю",
    "выкупаю",
    "приобритаю"
]

DEFAULT_COLUMN_2 = [
    "мтс", "mts", "красного", "красный", "мтса", "красных", "mt$",
    "мегафон", "мегу", "мега", "meg", "зеленого", "мегафона", "зелень", "мегафонов",
    "t2", "т2", "теле2", "tele2", "черного", "черный", "черных",
    "билайн", "пчелу", "пчела", "желтого", "желтый", "бил", "билку", "билайна", "билки", "билайнов",
    "йоты", "йота", "йоту", "yota", "синего", "синий", "голубой", "голубова", "йот", "голубых", "синих",
    "миранда", "миранды", "миранду", "миранд", "miranda",
    "волна", "волну", "волны", "волн",
    "сбер", "сбермобаил", "сбера", "сберов", "сбермобайлов",
    "добро", "добросвязь",
    "нн", "оператор",
    "озон", "озоны", "ozon", "расширенный", "озонов"
]

class WordsManager:
    def __init__(self, filename="words.json"):
        self.filename = filename
        self.words = self.load()
    
    def load(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if "column_1" not in data:
                        data["column_1"] = DEFAULT_COLUMN_1.copy()
                    if "column_2" not in data:
                        data["column_2"] = DEFAULT_COLUMN_2.copy()
                    return data
            except:
                pass
        
        data = {
            "column_1": DEFAULT_COLUMN_1.copy(),
            "column_2": DEFAULT_COLUMN_2.copy()
        }
        self.save(data)
        return data
    
    def save(self, data=None):
        if data is None:
            data = self.words
        with open(self.filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def get_column_1(self):
        return self.words.get("column_1", [])
    
    def get_column_2(self):
        return self.words.get("column_2", [])
    
    def add_word_column_1(self, word):
        word = word.lower().strip()
        if word not in self.words["column_1"]:
            self.words["column_1"].append(word)
            self.save()
            return True, f"✅ Слово '{word}' добавлено в столбец 1"
        return False, f"⚠️ Слово '{word}' уже есть"
    
    def remove_word_column_1(self, word):
        word = word.lower().strip()
        if word in self.words["column_1"]:
            self.words["column_1"].remove(word)
            self.save()
            return True, f"❌ Слово '{word}' удалено из столбца 1"
        return False, f"⚠️ Слово '{word}' не найдено"
    
    def add_word_column_2(self, word):
        word = word.lower().strip()
        if word not in self.words["column_2"]:
            self.words["column_2"].append(word)
            self.save()
            return True, f"✅ Слово '{word}' добавлено в столбец 2"
        return False, f"⚠️ Слово '{word}' уже есть"
    
    def remove_word_column_2(self, word):
        word = word.lower().strip()
        if word in self.words["column_2"]:
            self.words["column_2"].remove(word)
            self.save()
            return True, f"❌ Слово '{word}' удалено из столбца 2"
        return False, f"⚠️ Слово '{word}' не найдено"
    
    def reset_to_default(self):
        self.words["column_1"] = DEFAULT_COLUMN_1.copy()
        self.words["column_2"] = DEFAULT_COLUMN_2.copy()
        self.save()
        return "🔄 Слова сброшены к значениям по умолчанию"
    
    def get_words_list_text(self):
        col1 = self.get_column_1()
        col2 = self.get_column_2()
        
        text = f"📋 **СЛОВА ДЛЯ ПОИСКА**\n\n"
        text += f"🔍 **Столбец 1 (действия) - {len(col1)} слов:**\n"
        for i, word in enumerate(col1, 1):
            text += f"  {i}. {word}\n"
        
        text += f"\n👤 **Столбец 2 (операторы) - {len(col2)} слов:**\n"
        for i, word in enumerate(col2, 1):
            text += f"  {i}. {word}\n"
        
        return text