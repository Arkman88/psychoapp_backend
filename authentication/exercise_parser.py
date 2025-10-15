"""
Парсер для распознавания упражнений из голосовых команд
Поддерживает сложные шаблоны типа:
- "жим лежа 5 подходов по 40кг на 10 раз каждый"
- "3 подхода: 2 из них 4 раза по 40кг и один 4 раза по 50кг"
- "приседания 4 подхода по 12 повторений с весом 60кг"
"""

import re
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class ExerciseParser:
    """
    Парсер голосовых команд для упражнений
    """
    
    # Паттерны для распознавания чисел
    NUMBER_WORDS = {
        'один': 1, 'одна': 1, 'одного': 1, 'одному': 1,
        'два': 2, 'две': 2, 'двух': 2,
        'три': 3, 'трёх': 3, 'трех': 3,
        'четыре': 4, 'четырёх': 4, 'четырех': 4,
        'пять': 5, 'пяти': 5,
        'шесть': 6, 'шести': 6,
        'семь': 7, 'семи': 7,
        'восемь': 8, 'восьми': 8,
        'девять': 9, 'девяти': 9,
        'десять': 10, 'десяти': 10,
        'одиннадцать': 11, 'одиннадцати': 11,
        'двенадцать': 12, 'двенадцати': 12,
        'пятнадцать': 15, 'пятнадцати': 15,
        'двадцать': 20, 'двадцати': 20,
    }
    
    # Ключевые слова для параметров
    SETS_KEYWORDS = ['подход', 'подхода', 'подходов', 'сет', 'сета', 'сетов']
    REPS_KEYWORDS = ['раз', 'раза', 'повтор', 'повтора', 'повторение', 'повторения', 'повторений']
    WEIGHT_KEYWORDS = ['кг', 'килограмм', 'килограмма', 'кило', 'грамм']
    
    @classmethod
    def parse(cls, text: str) -> Dict:
        """
        Основной метод парсинга текста
        
        Args:
            text: Распознанный текст от пользователя
            
        Returns:
            Dict с полями:
            {
                "exercise_name": str,  # Название упражнения
                "sets": List[Dict],     # Список подходов
                "raw_text": str,        # Исходный текст
                "is_structured": bool   # Есть ли структурированные данные
            }
        """
        text = text.lower().strip()
        logger.info(f"Parsing exercise text: {text}")
        
        result = {
            "exercise_name": "",
            "sets": [],
            "raw_text": text,
            "is_structured": False
        }
        
        # Пытаемся распарсить сложный шаблон с несколькими вариантами подходов
        # Пример: "3 подхода: 2 из них 4 раза по 40кг и один 4 раза по 50кг"
        complex_match = cls._parse_complex_pattern(text)
        if complex_match:
            result.update(complex_match)
            result["is_structured"] = True
            return result
        
        # Пытаемся распарсить простой шаблон
        # Пример: "жим лежа 5 подходов по 40кг на 10 раз каждый"
        simple_match = cls._parse_simple_pattern(text)
        if simple_match:
            result.update(simple_match)
            result["is_structured"] = True
            return result
        
        # Если не удалось распарсить - возвращаем весь текст как название
        result["exercise_name"] = text
        return result
    
    @classmethod
    def _parse_simple_pattern(cls, text: str) -> Optional[Dict]:
        """
        Парсит простой шаблон: "упражнение X подходов по Y кг на Z раз"
        
        Примеры:
        - "жим лежа 5 подходов по 40кг на 10 раз"
        - "приседания 4 подхода по 12 повторений с весом 60кг"
        - "становая тяга 3 сета по 5 раз 100 кило"
        """
        # Паттерн: (название) (число) (подход*) (по/с/на) (число) (вес*) (на/по) (число) (раз*)
        pattern = r'^(.+?)\s+(\d+|' + '|'.join(cls.NUMBER_WORDS.keys()) + r')\s+(?:' + '|'.join(cls.SETS_KEYWORDS) + r')'
        
        # Ищем количество подходов
        sets_match = re.search(
            r'(\d+|' + '|'.join(cls.NUMBER_WORDS.keys()) + r')\s+(?:' + '|'.join(cls.SETS_KEYWORDS) + r')',
            text
        )
        
        if not sets_match:
            return None
        
        sets_count = cls._extract_number(sets_match.group(1))
        
        # Извлекаем название упражнения (всё до количества подходов)
        exercise_name = text[:sets_match.start()].strip()
        
        if not exercise_name:
            return None
        
        # Ищем вес
        weight = cls._extract_weight(text)
        
        # Ищем количество повторений
        reps = cls._extract_reps(text)
        
        # Создаём одинаковые подходы
        sets = []
        for i in range(sets_count):
            set_data = {"set_number": i + 1}
            if reps:
                set_data["reps"] = reps
            if weight:
                set_data["weight_kg"] = weight
            sets.append(set_data)
        
        return {
            "exercise_name": exercise_name,
            "sets": sets
        }
    
    @classmethod
    def _parse_complex_pattern(cls, text: str) -> Optional[Dict]:
        """
        Парсит сложный шаблон с разными подходами
        
        Пример: "жим 3 подхода: 2 из них 4 раза по 40кг и один 4 раза по 50кг"
        """
        # Ищем общее количество подходов
        total_sets_match = re.search(
            r'(\d+|' + '|'.join(cls.NUMBER_WORDS.keys()) + r')\s+(?:' + '|'.join(cls.SETS_KEYWORDS) + r')\s*:',
            text
        )
        
        if not total_sets_match:
            return None
        
        total_sets = cls._extract_number(total_sets_match.group(1))
        exercise_name = text[:total_sets_match.start()].strip()
        
        # Текст после двоеточия с описанием подходов
        sets_description = text[total_sets_match.end():].strip()
        
        # Разбиваем по "и" для разных групп подходов
        groups = re.split(r'\s+и\s+', sets_description)
        
        sets = []
        set_counter = 1
        
        for group in groups:
            # Ищем паттерн "X из них Y раз по Z кг" или "один Y раз по Z кг"
            # Паттерн 1: "X из них Y раз по Z кг"
            group_match = re.search(
                r'(\d+|' + '|'.join(cls.NUMBER_WORDS.keys()) + r')\s+(?:из\s+них|подход|подхода|подходов)\s+'
                r'(\d+|' + '|'.join(cls.NUMBER_WORDS.keys()) + r')\s+(?:' + '|'.join(cls.REPS_KEYWORDS) + r')\s+'
                r'(?:по\s+)?(\d+(?:\.\d+)?)\s*(?:' + '|'.join(cls.WEIGHT_KEYWORDS) + r')',
                group
            )
            
            # Паттерн 2: "один/два/три Y раз по Z кг" (без "из них")
            if not group_match:
                group_match = re.search(
                    r'(\d+|' + '|'.join(cls.NUMBER_WORDS.keys()) + r')\s+'
                    r'(\d+|' + '|'.join(cls.NUMBER_WORDS.keys()) + r')\s+(?:' + '|'.join(cls.REPS_KEYWORDS) + r')\s+'
                    r'(?:по\s+)?(\d+(?:\.\d+)?)\s*(?:' + '|'.join(cls.WEIGHT_KEYWORDS) + r')',
                    group
                )
            
            if group_match:
                count = cls._extract_number(group_match.group(1))
                reps = cls._extract_number(group_match.group(2))
                weight = float(group_match.group(3))
                
                for _ in range(count):
                    sets.append({
                        "set_number": set_counter,
                        "reps": reps,
                        "weight_kg": weight
                    })
                    set_counter += 1
        
        if not sets:
            return None
        
        return {
            "exercise_name": exercise_name,
            "sets": sets
        }
    
    @classmethod
    def _extract_number(cls, text: str) -> int:
        """Извлекает число из текста (цифра или слово)"""
        text = text.lower().strip()
        
        # Сначала пробуем как число
        if text.isdigit():
            return int(text)
        
        # Затем ищем в словаре слов
        return cls.NUMBER_WORDS.get(text, 0)
    
    @classmethod
    def _extract_weight(cls, text: str) -> Optional[float]:
        """Извлекает вес из текста"""
        # Паттерн: число + (кг|килограмм|кило)
        weight_match = re.search(
            r'(\d+(?:\.\d+)?)\s*(?:' + '|'.join(cls.WEIGHT_KEYWORDS) + r')',
            text
        )
        
        if weight_match:
            return float(weight_match.group(1))
        
        return None
    
    @classmethod
    def _extract_reps(cls, text: str) -> Optional[int]:
        """Извлекает количество повторений из текста"""
        # Паттерн: число + (раз|повтор*)
        reps_match = re.search(
            r'(\d+|' + '|'.join(cls.NUMBER_WORDS.keys()) + r')\s+(?:' + '|'.join(cls.REPS_KEYWORDS) + r')',
            text
        )
        
        if reps_match:
            return cls._extract_number(reps_match.group(1))
        
        return None
    
    @classmethod
    def format_sets_summary(cls, sets: List[Dict]) -> str:
        """
        Форматирует список подходов в читаемый текст
        
        Args:
            sets: Список подходов из parse()
            
        Returns:
            Строка типа "5 подходов по 10 раз с весом 40кг"
        """
        if not sets:
            return ""
        
        # Проверяем однородность подходов
        first_set = sets[0]
        all_same = all(
            s.get('reps') == first_set.get('reps') and 
            s.get('weight_kg') == first_set.get('weight_kg') 
            for s in sets
        )
        
        if all_same:
            # Все подходы одинаковые
            parts = [f"{len(sets)} подходов"]
            if 'reps' in first_set:
                parts.append(f"по {first_set['reps']} раз")
            if 'weight_kg' in first_set:
                parts.append(f"с весом {first_set['weight_kg']}кг")
            return " ".join(parts)
        else:
            # Разные подходы - перечисляем
            set_descriptions = []
            for s in sets:
                desc_parts = [f"Подход {s['set_number']}"]
                if 'reps' in s:
                    desc_parts.append(f"{s['reps']} раз")
                if 'weight_kg' in s:
                    desc_parts.append(f"{s['weight_kg']}кг")
                set_descriptions.append(" - ".join(desc_parts))
            return "; ".join(set_descriptions)
