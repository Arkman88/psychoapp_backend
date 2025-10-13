"""
Простой скрипт для парсинга упражнений БЕЗ автоматического перевода
Использует ручной словарь переводов для основных терминов

Использование:
    python scripts/parse_exercises_simple.py
"""

import json
import os
import requests
from typing import Dict, List, Optional
import time


class SimpleExerciseParser:
    """Упрощённый парсер без автоперевода"""
    
    GITHUB_API = "https://api.github.com/repos/wrkout/exercises.json/contents/exercises"
    RAW_BASE_URL = "https://raw.githubusercontent.com/wrkout/exercises.json/master/exercises"
    
    # Словарь переводов названий упражнений (популярные)
    EXERCISE_NAMES = {
        # Грудь
        'Bench Press': 'Жим лёжа',
        'Incline Bench Press': 'Жим на наклонной скамье',
        'Decline Bench Press': 'Жим на скамье с отрицательным наклоном',
        'Dumbbell Bench Press': 'Жим гантелей лёжа',
        'Push-Up': 'Отжимания',
        'Chest Fly': 'Разведение рук',
        'Cable Crossover': 'Сведение рук в кроссовере',
        
        # Спина
        'Deadlift': 'Становая тяга',
        'Pull-Up': 'Подтягивания',
        'Chin-Up': 'Подтягивания обратным хватом',
        'Lat Pulldown': 'Тяга верхнего блока',
        'Barbell Row': 'Тяга штанги в наклоне',
        'Dumbbell Row': 'Тяга гантели в наклоне',
        'Seated Cable Row': 'Тяга горизонтального блока',
        'T-Bar Row': 'Тяга Т-грифа',
        
        # Ноги
        'Squat': 'Приседания',
        'Front Squat': 'Фронтальные приседания',
        'Leg Press': 'Жим ногами',
        'Leg Extension': 'Разгибание ног',
        'Leg Curl': 'Сгибание ног',
        'Lunge': 'Выпады',
        'Romanian Deadlift': 'Румынская тяга',
        'Calf Raise': 'Подъём на носки',
        
        # Плечи
        'Shoulder Press': 'Жим плечами',
        'Military Press': 'Армейский жим',
        'Dumbbell Shoulder Press': 'Жим гантелей',
        'Lateral Raise': 'Махи в стороны',
        'Front Raise': 'Махи перед собой',
        'Rear Delt Fly': 'Разведение в наклоне',
        'Upright Row': 'Тяга к подбородку',
        'Shrug': 'Шраги',
        
        # Руки
        'Barbell Curl': 'Подъём штанги на бицепс',
        'Dumbbell Curl': 'Подъём гантелей на бицепс',
        'Hammer Curl': 'Молотковые сгибания',
        'Preacher Curl': 'Сгибания на скамье Скотта',
        'Tricep Dip': 'Отжимания на брусьях',
        'Tricep Extension': 'Разгибания на трицепс',
        'Skull Crusher': 'Французский жим',
        'Close-Grip Bench Press': 'Жим узким хватом',
        
        # Пресс
        'Crunch': 'Скручивания',
        'Sit-Up': 'Подъём корпуса',
        'Plank': 'Планка',
        'Russian Twist': 'Русские скручивания',
        'Leg Raise': 'Подъём ног',
        'Mountain Climber': 'Альпинист',
        'Ab Wheel': 'Ролик для пресса',
    }
    
    # Термины для замены в названиях
    TERMS_TRANSLATION = {
        'Barbell': 'Штанга',
        'Dumbbell': 'Гантели',
        'Cable': 'Блок',
        'Machine': 'Тренажёр',
        'Incline': 'Наклон',
        'Decline': 'Обратный наклон',
        'Flat': 'Горизонтальная',
        'Press': 'Жим',
        'Curl': 'Сгибание',
        'Extension': 'Разгибание',
        'Raise': 'Подъём',
        'Pull': 'Тяга',
        'Push': 'Жим',
        'Squat': 'Приседание',
        'Lunge': 'Выпад',
        'Row': 'Тяга',
        'Fly': 'Разведение',
        'Crunch': 'Скручивание',
    }
    
    CATEGORY_MAPPING = {
        'strength': 'physical',
        'stretching': 'physical',
        'plyometrics': 'physical',
        'strongman': 'physical',
        'powerlifting': 'physical',
        'cardio': 'physical',
        'olympic weightlifting': 'physical',
        'crossfit': 'physical',
        'weighted bodyweight': 'physical',
        'assisted bodyweight': 'physical',
    }
    
    LEVEL_MAPPING = {
        'beginner': 'beginner',
        'intermediate': 'intermediate',
        'expert': 'advanced',
    }
    
    EQUIPMENT_TRANSLATION = {
        'barbell': 'штанга',
        'dumbbell': 'гантели',
        'body only': 'собственный вес',
        'machine': 'тренажёр',
        'cable': 'блочный тренажёр',
        'kettlebells': 'гири',
        'bands': 'резиновые ленты',
        'medicine ball': 'медбол',
        'exercise ball': 'фитбол',
        'foam roll': 'массажный ролик',
        'e-z curl bar': 'EZ-гриф',
    }
    
    MUSCLE_TRANSLATION = {
        'abdominals': 'пресс',
        'hamstrings': 'бицепс бедра',
        'calves': 'икры',
        'shoulders': 'плечи',
        'adductors': 'приводящие',
        'glutes': 'ягодицы',
        'quadriceps': 'квадрицепс',
        'biceps': 'бицепс',
        'forearms': 'предплечья',
        'abductors': 'отводящие',
        'triceps': 'трицепс',
        'chest': 'грудь',
        'lower back': 'поясница',
        'traps': 'трапеции',
        'middle back': 'средняя спина',
        'lats': 'широчайшие',
        'neck': 'шея',
    }
    
    def __init__(self):
        self.exercises = []
    
    def simple_translate(self, name: str) -> str:
        """Простой перевод на основе словаря"""
        # Проверяем точное совпадение
        if name in self.EXERCISE_NAMES:
            return self.EXERCISE_NAMES[name]
        
        # Пробуем заменить известные термины
        translated = name
        for en, ru in self.TERMS_TRANSLATION.items():
            if en in translated:
                translated = translated.replace(en, ru)
        
        # Если перевод изменился, возвращаем его
        if translated != name:
            return translated
        
        # Иначе возвращаем оригинал (можно доработать позже)
        return name
    
    def fetch_exercise_list(self) -> List[str]:
        """Получить список упражнений"""
        print("📥 Загрузка списка упражнений...")
        
        try:
            response = requests.get(self.GITHUB_API, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            folders = [item['name'] for item in data if item['type'] == 'dir']
            print(f"✓ Найдено {len(folders)} упражнений")
            return folders
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return []
    
    def fetch_exercise_data(self, folder_name: str) -> Optional[Dict]:
        """Загрузить данные упражнения"""
        url = f"{self.RAW_BASE_URL}/{folder_name}/exercise.json"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"⚠️  Ошибка {folder_name}: {e}")
            return None
    
    def adapt_exercise(self, raw_data: Dict) -> Dict:
        """Адаптация под нашу структуру"""
        name = raw_data.get('name', 'Unknown')
        name_ru = self.simple_translate(name)
        
        category = self.CATEGORY_MAPPING.get(
            raw_data.get('category', 'strength').lower(),
            'physical'
        )
        
        difficulty = self.LEVEL_MAPPING.get(
            raw_data.get('level', 'beginner').lower(),
            'beginner'
        )
        
        instructions = raw_data.get('instructions', [])
        instructions_text = '\n'.join([f"{i+1}. {instr}" for i, instr in enumerate(instructions)])
        
        # Собираем информацию о мышцах
        primary_muscles = raw_data.get('primaryMuscles', [])
        secondary_muscles = raw_data.get('secondaryMuscles', [])
        equipment = raw_data.get('equipment', '')
        
        description_parts = []
        
        if primary_muscles:
            muscles_ru = [self.MUSCLE_TRANSLATION.get(m, m) for m in primary_muscles]
            description_parts.append(f"Основные мышцы: {', '.join(muscles_ru)}")
        
        if secondary_muscles:
            muscles_ru = [self.MUSCLE_TRANSLATION.get(m, m) for m in secondary_muscles]
            description_parts.append(f"Вспомогательные: {', '.join(muscles_ru)}")
        
        if equipment:
            equipment_ru = self.EQUIPMENT_TRANSLATION.get(equipment.lower(), equipment)
            description_parts.append(f"Оборудование: {equipment_ru}")
        
        description = '\n'.join(description_parts)
        
        # Формируем алиасы
        aliases = raw_data.get('aliases', [])
        
        # Добавляем английское название
        if name != name_ru:
            aliases.insert(0, name)
        
        # Добавляем вариант с оборудованием
        if equipment:
            equipment_ru = self.EQUIPMENT_TRANSLATION.get(equipment.lower(), equipment)
            aliases.append(f"{name_ru} ({equipment_ru})")
        
        return {
            'model': 'authentication.exercise',
            'pk': None,
            'fields': {
                'name': name_ru,
                'description': description,
                'category': category,
                'difficulty': difficulty,
                'duration_min': None,
                'duration_max': None,
                'repetitions': None,
                'instructions': instructions_text,
                'audio_url': None,
                'video_url': None,
                'is_active': True,
                'usage_count': 0,
            },
            'aliases': list(set(aliases))[:15]  # Уникальные, максимум 15
        }
    
    def parse_all(self, limit: Optional[int] = None) -> List[Dict]:
        """Парсинг всех упражнений"""
        folders = self.fetch_exercise_list()
        
        if limit:
            folders = folders[:limit]
            print(f"⚠️  Ограничение: {limit} упражнений")
        
        print(f"\n🔄 Обработка {len(folders)} упражнений...\n")
        
        for i, folder in enumerate(folders, 1):
            print(f"[{i}/{len(folders)}] {folder}...", end=' ')
            
            raw_data = self.fetch_exercise_data(folder)
            if raw_data:
                exercise = self.adapt_exercise(raw_data)
                self.exercises.append(exercise)
                print(f"✓ {exercise['fields']['name']}")
            else:
                print("✗")
            
            time.sleep(0.2)  # Задержка
        
        print(f"\n✓ Обработано: {len(self.exercises)}")
        return self.exercises
    
    def save_to_fixture(self, filename: str = 'gym_exercises.json'):
        """Сохранение"""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_path = os.path.join(base_dir, 'authentication/fixtures', filename)
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        fixture_data = []
        aliases_data = {}
        
        for exercise in self.exercises:
            aliases = exercise.pop('aliases', [])
            fixture_data.append(exercise)
            aliases_data[exercise['fields']['name']] = aliases
        
        # Сохраняем упражнения
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(fixture_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 Упражнения: {output_path}")
        
        # Алиасы
        aliases_path = output_path.replace('.json', '_aliases.json')
        with open(aliases_path, 'w', encoding='utf-8') as f:
            json.dump(aliases_data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Алиасы: {aliases_path}")
        
        # Статистика
        print(f"\n📊 Статистика:")
        print(f"   Всего упражнений: {len(fixture_data)}")
        print(f"   Всего алиасов: {sum(len(a) for a in aliases_data.values())}")
        
        return output_path, aliases_path


def main():
    print("=" * 70)
    print("🏋️  ПАРСЕР УПРАЖНЕНИЙ (упрощённая версия)")
    print("=" * 70)
    
    parser = SimpleExerciseParser()
    
    print("\nВыберите режим:")
    print("  1) Все упражнения (~800+)")
    print("  2) Тестовый режим (50 упражнений)")
    print("  3) Указать количество")
    
    choice = input("\nВыбор [1/2/3]: ").strip()
    
    limit = None
    if choice == '2':
        limit = 50
    elif choice == '3':
        try:
            limit = int(input("Количество: "))
        except:
            limit = 50
    
    exercises = parser.parse_all(limit=limit)
    
    if exercises:
        parser.save_to_fixture()
        
        print("\n" + "=" * 70)
        print("✅ ГОТОВО!")
        print("=" * 70)
        print("\n📋 Следующие шаги:")
        print("  1. python manage.py loaddata authentication/fixtures/gym_exercises.json")
        print("  2. python manage.py load_gym_aliases")
        print()


if __name__ == '__main__':
    main()
