# message_checker.py
import re
from config import COLUMN_1, COLUMN_2

def check_message(text):
    """
    Проверяет сообщение на наличие слов из двух столбцов.
    Возвращает (найдено, слово_из_1, слово_из_2, какие_слова_найдены)
    """
    if not text:
        return False, None, None, []
    
    # Приводим к нижнему регистру
    text_lower = text.lower()
    
    # Разбиваем на отдельные слова и фразы
    words = re.findall(r'\b[а-яa-z0-9]+\b', text_lower)
    
    # Ищем слова из первого столбца
    found_column_1 = []
    for word in COLUMN_1:
        # Ищем как отдельное слово
        if word.lower() in words:
            found_column_1.append(word)
        # Ищем в тексте (для случаев типа "куплюмтс")
        elif word.lower() in text_lower:
            found_column_1.append(word)
    
    # Ищем слова из второго столбца
    found_column_2 = []
    for word in COLUMN_2:
        if word.lower() in words:
            found_column_2.append(word)
        elif word.lower() in text_lower:
            found_column_2.append(word)
    
    # Если есть хотя бы одно из каждого столбца
    if found_column_1 and found_column_2:
        return True, found_column_1[0], found_column_2[0], {
            "column_1": found_column_1,
            "column_2": found_column_2
        }
    
    return False, None, None, []


def highlight_matches(text, matches):
    """Подсвечивает найденные слова в тексте"""
    if not matches:
        return text
    
    result = text
    for word in matches.get("column_1", []):
        result = re.sub(f'({re.escape(word)})', r'**\1**', result, flags=re.IGNORECASE)
    for word in matches.get("column_2", []):
        result = re.sub(f'({re.escape(word)})', r'**\1**', result, flags=re.IGNORECASE)
    
    return result