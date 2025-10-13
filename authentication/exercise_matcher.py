"""
Сервис для сопоставления распознанного текста с упражнениями из базы
Использует fuzzy matching и алгоритмы схожести строк
"""

from difflib import SequenceMatcher
from typing import List, Dict, Tuple, Optional
import re
from django.db.models import Q
from .models import Exercise, ExerciseAlias


class QuickExerciseMatcher:
    """Быстрое сопоставление упражнений для UI с 1-3 карточками"""
    
    # Пороги схожести
    EXACT_THRESHOLD = 0.9      # Точное совпадение
    GOOD_THRESHOLD = 0.75      # Хорошее совпадение
    SUGGEST_THRESHOLD = 0.5    # Минимальный порог для показа
    
    # Стоп-слова
    STOP_WORDS_RU = {'упражнение', 'на', 'для', 'с', 'и', 'в', 'по'}
    STOP_WORDS_EN = {'exercise', 'for', 'with', 'on', 'the', 'and', 'a'}
    
    @classmethod
    def normalize_text(cls, text: str, language: str = 'ru') -> str:
        """Нормализация текста"""
        text = text.lower().strip()
        text = re.sub(r'[^\w\s-]', '', text)
        
        # Убираем стоп-слова
        stop_words = cls.STOP_WORDS_RU if language == 'ru' else cls.STOP_WORDS_EN
        words = text.split()
        words = [w for w in words if w not in stop_words]
        
        return ' '.join(words)
    
    @classmethod
    def calculate_similarity(cls, text1: str, text2: str) -> float:
        """Вычисление схожести с бонусами"""
        base_sim = SequenceMatcher(None, text1, text2).ratio()
        bonus = 0.0
        
        # Точное вхождение
        if text1 in text2 or text2 in text1:
            bonus += 0.15
        
        # Совпадение начала
        min_len = min(len(text1), len(text2))
        if min_len >= 3:
            prefix_len = min(5, min_len)
            if text1[:prefix_len] == text2[:prefix_len]:
                bonus += 0.1
        
        # Совпадение слов
        words1 = set(text1.split())
        words2 = set(text2.split())
        if words1 and words2:
            word_overlap = len(words1 & words2) / len(words1 | words2)
            bonus += word_overlap * 0.1
        
        return min(1.0, base_sim + bonus)
    
    @classmethod
    def find_matches(
        cls,
        text: str,
        language: str = 'ru',
        max_results: int = 3
    ) -> List[Dict]:
        """Быстрый поиск упражнений"""
        normalized_input = cls.normalize_text(text, language)
        
        # Оптимизированный поиск в БД
        field = 'name_ru__icontains' if language == 'ru' else 'name__icontains'
        exercises = Exercise.objects.filter(
            **{field: text.lower()},
            is_active=True
        ).prefetch_related('aliases')[:20]
        
        # Расширенный поиск если не найдено
        if not exercises.exists():
            exercises = Exercise.objects.filter(
                Q(aliases__alias__icontains=text.lower()) |
                Q(name__icontains=text.lower()) |
                Q(name_ru__icontains=text.lower()),
                is_active=True
            ).distinct().prefetch_related('aliases')[:20]
        
        # Полный поиск если всё ещё пусто
        if not exercises.exists():
            exercises = Exercise.objects.filter(
                is_active=True
            ).prefetch_related('aliases')[:100]
        
        matches = []
        
        for exercise in exercises:
            variants = []
            
            # Добавляем варианты для сравнения
            if language == 'ru':
                if exercise.name_ru:
                    variants.append(cls.normalize_text(exercise.name_ru, 'ru'))
                variants.append(cls.normalize_text(exercise.name, 'en'))
            else:
                variants.append(cls.normalize_text(exercise.name, 'en'))
                if exercise.name_ru:
                    variants.append(cls.normalize_text(exercise.name_ru, 'ru'))
            
            # Алиасы
            for alias in exercise.aliases.all():
                variants.append(cls.normalize_text(alias.alias, language))
            
            # Максимальная схожесть
            max_similarity = 0.0
            best_variant = exercise.name
            
            for variant in variants:
                similarity = cls.calculate_similarity(normalized_input, variant)
                if similarity > max_similarity:
                    max_similarity = similarity
                    best_variant = variant
            
            if max_similarity >= cls.SUGGEST_THRESHOLD:
                matches.append({
                    'id': str(exercise.id),
                    'name': exercise.name,
                    'name_ru': exercise.name_ru or '',
                    'matched_variant': best_variant,
                    'similarity': round(max_similarity, 3),
                    'category': exercise.category,
                    'difficulty': exercise.difficulty,
                    'image_main': exercise.image_url_main or '',
                    'image_secondary': exercise.image_url_secondary or '',
                    'description_short': exercise.description[:150] + '...' if len(exercise.description) > 150 else exercise.description,
                })
        
        # Сортируем и ограничиваем
        matches.sort(key=lambda x: x['similarity'], reverse=True)
        return matches[:max_results]


class ExerciseMatcher:
    """Класс для поиска и сопоставления упражнений"""
    
    # Минимальный порог схожести для автоматического выбора
    AUTO_MATCH_THRESHOLD = 0.85
    
    # Порог для предложения вариантов
    SUGGEST_THRESHOLD = 0.5
    
    # Максимальное количество предложений
    MAX_SUGGESTIONS = 5
    
    @classmethod
    def normalize_text(cls, text: str) -> str:
        """
        Нормализация текста для сравнения
        - приведение к нижнему регистру
        - удаление лишних пробелов
        - удаление знаков препинания
        """
        if not text:
            return ""
        
        # Нижний регистр
        text = text.lower().strip()
        
        # Удаление знаков препинания (кроме пробелов и дефисов)
        text = re.sub(r'[^\w\s\-]', '', text)
        
        # Замена множественных пробелов на один
        text = re.sub(r'\s+', ' ', text)
        
        return text
    
    @classmethod
    def calculate_similarity(cls, text1: str, text2: str) -> float:
        """
        Вычисление коэффициента схожести между двумя строками
        Использует SequenceMatcher (алгоритм похожий на Levenshtein)
        
        Returns:
            float: значение от 0 до 1, где 1 = полное совпадение
        """
        norm_text1 = cls.normalize_text(text1)
        norm_text2 = cls.normalize_text(text2)
        
        if not norm_text1 or not norm_text2:
            return 0.0
        
        # Базовая схожесть через SequenceMatcher
        base_similarity = SequenceMatcher(None, norm_text1, norm_text2).ratio()
        
        # Бонус за точное вхождение подстроки
        substring_bonus = 0.0
        if norm_text1 in norm_text2 or norm_text2 in norm_text1:
            substring_bonus = 0.1
        
        # Бонус за совпадение начала строки
        start_bonus = 0.0
        if norm_text1.startswith(norm_text2[:min(5, len(norm_text2))]) or \
           norm_text2.startswith(norm_text1[:min(5, len(norm_text1))]):
            start_bonus = 0.05
        
        return min(1.0, base_similarity + substring_bonus + start_bonus)
    
    @classmethod
    def extract_parameters(cls, text: str) -> Dict[str, Optional[int]]:
        """
        Извлечение параметров из текста (повторения, длительность)
        
        Примеры:
        - "10 приседаний" → {'repetitions': 10}
        - "дыхание 5 минут" → {'duration': 300}
        - "отжимания 20 раз по 3 подхода" → {'repetitions': 20, 'sets': 3}
        """
        params = {
            'repetitions': None,
            'duration': None,
            'sets': None,
        }
        
        text_lower = text.lower()
        
        # Поиск повторений
        reps_patterns = [
            r'(\d+)\s*(?:раз|повтор|повторен)',
            r'(\d+)\s*(?:приседан|отжиман|наклон)',
        ]
        for pattern in reps_patterns:
            match = re.search(pattern, text_lower)
            if match:
                params['repetitions'] = int(match.group(1))
                break
        
        # Поиск длительности
        duration_patterns = [
            (r'(\d+)\s*минут', 60),
            (r'(\d+)\s*секунд', 1),
            (r'(\d+)\s*час', 3600),
        ]
        for pattern, multiplier in duration_patterns:
            match = re.search(pattern, text_lower)
            if match:
                params['duration'] = int(match.group(1)) * multiplier
                break
        
        # Поиск подходов/сетов
        sets_pattern = r'(\d+)\s*(?:подход|сет|серии)'
        match = re.search(sets_pattern, text_lower)
        if match:
            params['sets'] = int(match.group(1))
        
        return params
    
    @classmethod
    def find_matches(
        cls, 
        recognized_text: str, 
        category: Optional[str] = None,
        min_confidence: float = 0.0
    ) -> List[Dict]:
        """
        Поиск подходящих упражнений по распознанному тексту
        
        Args:
            recognized_text: Распознанный текст от пользователя
            category: Опциональная категория для фильтрации
            min_confidence: Минимальный уровень confidence от ASR
            
        Returns:
            List[Dict]: Список найденных упражнений с оценками схожести
        """
        if not recognized_text:
            return []
        
        normalized_input = cls.normalize_text(recognized_text)
        
        # Извлекаем параметры из текста
        extracted_params = cls.extract_parameters(recognized_text)
        
        # Получаем все активные упражнения
        exercises_query = Exercise.objects.filter(is_active=True)
        if category:
            exercises_query = exercises_query.filter(category=category)
        
        exercises = exercises_query.prefetch_related('aliases')
        
        matches = []
        
        for exercise in exercises:
            # Список вариантов для сравнения: название + все алиасы
            variants = [exercise.name] + [alias.alias for alias in exercise.aliases.all()]
            
            # Находим максимальную схожесть среди всех вариантов
            max_similarity = 0.0
            best_match_variant = exercise.name
            
            for variant in variants:
                similarity = cls.calculate_similarity(normalized_input, variant)
                if similarity > max_similarity:
                    max_similarity = similarity
                    best_match_variant = variant
            
            # Фильтруем по порогу
            if max_similarity >= cls.SUGGEST_THRESHOLD:
                matches.append({
                    'exercise_id': str(exercise.id),
                    'name': exercise.name,
                    'name_ru': exercise.name_ru or '',
                    'matched_variant': best_match_variant,
                    'category': exercise.category,
                    'category_display': exercise.get_category_display(),
                    'difficulty': exercise.difficulty,
                    'difficulty_display': exercise.get_difficulty_display(),
                    'description': exercise.description,
                    'similarity_score': round(max_similarity, 3),
                    'instructions': exercise.instructions,
                    'duration_min': exercise.duration_min,
                    'duration_max': exercise.duration_max,
                    'repetitions': exercise.repetitions,
                    'audio_url': exercise.audio_url,
                    'video_url': exercise.video_url,
                    'image_url_main': exercise.image_url_main,
                    'image_url_secondary': exercise.image_url_secondary,
                    'usage_count': exercise.usage_count,
                    'extracted_params': extracted_params,
                })
        
        # Сортируем по убыванию схожести
        matches.sort(key=lambda x: x['similarity_score'], reverse=True)
        
        # Ограничиваем количество результатов
        return matches[:cls.MAX_SUGGESTIONS]
    
    @classmethod
    def get_best_match(
        cls, 
        recognized_text: str,
        category: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Получение наилучшего совпадения
        Возвращает None если уверенность ниже порога автоматического выбора
        """
        matches = cls.find_matches(recognized_text, category)
        
        if not matches:
            return None
        
        best_match = matches[0]
        
        # Проверяем порог для автоматического выбора
        if best_match['similarity_score'] >= cls.AUTO_MATCH_THRESHOLD:
            return best_match
        
        return None
    
    @classmethod
    def search_exercises(
        cls,
        query: str,
        category: Optional[str] = None,
        difficulty: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict]:
        """
        Поиск упражнений по текстовому запросу (для browse/search функционала)
        """
        exercises_query = Exercise.objects.filter(is_active=True)
        
        if category:
            exercises_query = exercises_query.filter(category=category)
        
        if difficulty:
            exercises_query = exercises_query.filter(difficulty=difficulty)
        
        if query:
            normalized_query = cls.normalize_text(query)
            
            # Поиск по названию, описанию и алиасам
            exercises_query = exercises_query.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query) |
                Q(aliases__alias__icontains=query)
            ).distinct()
        
        exercises = exercises_query[:limit]
        
        results = []
        for exercise in exercises:
            results.append({
                'exercise_id': str(exercise.id),
                'name': exercise.name,
                'category': exercise.category,
                'category_display': exercise.get_category_display(),
                'difficulty': exercise.difficulty,
                'difficulty_display': exercise.get_difficulty_display(),
                'description': exercise.description,
                'instructions': exercise.instructions,
                'duration_min': exercise.duration_min,
                'duration_max': exercise.duration_max,
                'repetitions': exercise.repetitions,
                'audio_url': exercise.audio_url,
                'video_url': exercise.video_url,
                'usage_count': exercise.usage_count,
            })
        
        return results
