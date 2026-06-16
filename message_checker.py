# message_checker.py
import re

class MessageChecker:
    def __init__(self, words_manager):
        self.words_manager = words_manager
    
    def check_message(self, text):
        if not text:
            return False, None, None, []
        
        column_1 = self.words_manager.get_column_1()
        column_2 = self.words_manager.get_column_2()
        
        text_lower = text.lower()
        words = re.findall(r'\b[а-яa-z0-9]+\b', text_lower)
        
        found_column_1 = []
        for word in column_1:
            if word.lower() in words or word.lower() in text_lower:
                found_column_1.append(word)
        
        found_column_2 = []
        for word in column_2:
            if word.lower() in words or word.lower() in text_lower:
                found_column_2.append(word)
        
        if found_column_1 and found_column_2:
            return True, found_column_1[0], found_column_2[0], {
                "column_1": found_column_1,
                "column_2": found_column_2
            }
        
        return False, None, None, []
    
    def highlight_matches(self, text, matches):
        if not matches:
            return text
        
        result = text
        for word in matches.get("column_1", []):
            result = re.sub(f'({re.escape(word)})', r'**\1**', result, flags=re.IGNORECASE)
        for word in matches.get("column_2", []):
            result = re.sub(f'({re.escape(word)})', r'**\1**', result, flags=re.IGNORECASE)
        
        return result