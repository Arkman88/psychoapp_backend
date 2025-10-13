"""
Парсер упражнений с изображениями и оригинальными названиями
Использование: python scripts/parse_exercises_with_images.py
"""

import json
import os
import requests
from typing import Dict, List, Optional
import time


class ExerciseParserWithImages:
    """Парсер с сохранением изображений"""
    
    GITHUB_API = "https://api.github.com/repos/wrkout/exercises.json/contents/exercises"
    RAW_BASE_URL = "https://raw.githubusercontent.com/wrkout/exercises.json/master/exercises"
    
    # Маппинг категорий для gym упражнений
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
    
    # Перевод групп мышц для описания
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
        'middle back': 'средняя часть спины',
        'lats': 'широчайшие',
        'neck': 'шея',
    }
    
    EQUIPMENT_TRANSLATION = {
        'barbell': 'Штанга',
        'dumbbell': 'Гантели',
        'body only': 'Собственный вес',
        'machine': 'Тренажёр',
        'cable': 'Блочный тренажёр',
        'kettlebells': 'Гири',
        'bands': 'Резиновые ленты',
        'medicine ball': 'Медбол',
        'exercise ball': 'Фитбол',
        'foam roll': 'Массажный ролик',
        'e-z curl bar': 'EZ-гриф',
    }
    
    def __init__(self):
        self.exercises = []
    
    def fetch_exercise_list(self) -> List[str]:
        """Получить список упражнений"""
        print("📥 Загрузка списка упражнений из GitHub...")
        
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
            return None
    
    def get_image_urls(self, folder_name: str) -> tuple:
        """Получить URL изображений упражнения"""
        # В репозитории изображения обычно называются 0.jpg и 1.jpg
        image_0 = f"{self.RAW_BASE_URL}/{folder_name}/images/0.jpg"
        image_1 = f"{self.RAW_BASE_URL}/{folder_name}/images/1.jpg"
        
        # Проверяем доступность изображений
        try:
            response = requests.head(image_0, timeout=5)
            main_image = image_0 if response.status_code == 200 else None
        except:
            main_image = None
        
        try:
            response = requests.head(image_1, timeout=5)
            secondary_image = image_1 if response.status_code == 200 else None
        except:
            secondary_image = None
        
        return main_image, secondary_image
    
    def adapt_exercise(self, raw_data: Dict, folder_name: str) -> Dict:
        """Адаптация под нашу структуру с оригинальными названиями"""
        
        # Оригинальное название (БЕЗ перевода)
        name = raw_data.get('name', 'Unknown Exercise')
        
        # Категория
        category = self.CATEGORY_MAPPING.get(
            raw_data.get('category', 'strength').lower(),
            'physical'
        )
        
        # Сложность
        difficulty = self.LEVEL_MAPPING.get(
            raw_data.get('level', 'beginner').lower(),
            'beginner'
        )
        
        # Инструкции (на английском)
        instructions = raw_data.get('instructions', [])
        instructions_text = '\n'.join([f"{i+1}. {instr}" for i, instr in enumerate(instructions)])
        
        # Описание с информацией о мышцах (на русском для удобства)
        primary_muscles = raw_data.get('primaryMuscles', [])
        secondary_muscles = raw_data.get('secondaryMuscles', [])
        equipment = raw_data.get('equipment', '')
        force = raw_data.get('force', '')
        mechanic = raw_data.get('mechanic', '')
        
        description_parts = []
        
        if primary_muscles:
            muscles_ru = [self.MUSCLE_TRANSLATION.get(m, m) for m in primary_muscles]
            description_parts.append(f"Primary muscles: {', '.join(muscles_ru)}")
        
        if secondary_muscles:
            muscles_ru = [self.MUSCLE_TRANSLATION.get(m, m) for m in secondary_muscles]
            description_parts.append(f"Secondary muscles: {', '.join(muscles_ru)}")
        
        if equipment:
            equipment_ru = self.EQUIPMENT_TRANSLATION.get(equipment.lower(), equipment)
            description_parts.append(f"Equipment: {equipment_ru}")
        
        if force:
            description_parts.append(f"Force: {force}")
        
        if mechanic:
            description_parts.append(f"Mechanic: {mechanic}")
        
        description = raw_data.get('description', '')
        if description:
            description_parts.insert(0, description)
        
        full_description = '\n'.join(description_parts)
        
        # Получаем URL изображений
        image_main, image_secondary = self.get_image_urls(folder_name)
        
        # Формируем алиасы (оригинальные aliases + варианты)
        aliases = raw_data.get('aliases', [])
        
        # Добавляем вариант с оборудованием
        if equipment and equipment.lower() not in name.lower():
            aliases.append(f"{name} ({equipment})")
        
        return {
            'model': 'authentication.exercise',
            'pk': None,
            'fields': {
                'name': name,  # ОРИГИНАЛЬНОЕ название
                'name_ru': '',  # Будет заполнено позже через скрипт перевода
                'description': full_description[:1000] if full_description else '',
                'category': category,
                'difficulty': difficulty,
                'duration_min': None,
                'duration_max': None,
                'repetitions': None,
                'instructions': instructions_text,
                'audio_url': None,
                'video_url': None,
                'image_url_main': image_main,
                'image_url_secondary': image_secondary,
                'is_active': True,
                'usage_count': 0,
                'created_at': '2025-10-13T12:00:00Z',
                'updated_at': '2025-10-13T12:00:00Z',
            },
            'aliases': list(set(aliases))[:20],  # Уникальные
            'raw_data': {
                'primaryMuscles': primary_muscles,
                'secondaryMuscles': secondary_muscles,
                'equipment': equipment,
                'force': force,
                'mechanic': mechanic,
            }
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
                exercise = self.adapt_exercise(raw_data, folder)
                self.exercises.append(exercise)
                
                # Показываем прогресс
                has_images = "🖼️" if exercise['fields']['image_url_main'] else "📄"
                print(f"✓ {has_images} {exercise['fields']['name']}")
            else:
                print("✗")
            
            # Задержка
            time.sleep(0.2)
        
        print(f"\n✓ Обработано: {len(self.exercises)}")
        
        # Статистика по изображениям
        with_images = sum(1 for ex in self.exercises if ex['fields']['image_url_main'])
        print(f"📊 С изображениями: {with_images}/{len(self.exercises)}")
        
        return self.exercises
    
    def save_to_fixture(self, filename: str = 'gym_exercises.json'):
        """Сохранение"""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_path = os.path.join(base_dir, 'authentication/fixtures', filename)
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        fixture_data = []
        aliases_data = {}
        metadata = {}
        
        for exercise in self.exercises:
            # Извлекаем алиасы и метаданные
            aliases = exercise.pop('aliases', [])
            raw_data = exercise.pop('raw_data', {})
            
            fixture_data.append(exercise)
            
            exercise_name = exercise['fields']['name']
            aliases_data[exercise_name] = aliases
            metadata[exercise_name] = raw_data
        
        # Сохраняем упражнения
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(fixture_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 Упражнения: {output_path}")
        
        # Алиасы
        aliases_path = output_path.replace('.json', '_aliases.json')
        with open(aliases_path, 'w', encoding='utf-8') as f:
            json.dump(aliases_data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Алиасы: {aliases_path}")
        
        # Метаданные (для будущего использования)
        metadata_path = output_path.replace('.json', '_metadata.json')
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Метаданные: {metadata_path}")
        
        # Статистика
        print(f"\n📊 Статистика:")
        print(f"   Всего упражнений: {len(fixture_data)}")
        print(f"   Всего алиасов: {sum(len(a) for a in aliases_data.values())}")
        with_images = sum(1 for ex in fixture_data if ex['fields']['image_url_main'])
        print(f"   С изображениями: {with_images}")
        
        return output_path, aliases_path


def main():
    print("=" * 70)
    print("🏋️  ПАРСЕР УПРАЖНЕНИЙ С ИЗОБРАЖЕНИЯМИ")
    print("=" * 70)
    print("\n⚠️  Примечание: Сохраняются ОРИГИНАЛЬНЫЕ названия на английском")
    print("   Перевод можно будет добавить позже через отдельную команду\n")
    
    parser = ExerciseParserWithImages()
    
    print("Выберите режим:")
    print("  1) Все упражнения (~800+, займёт ~10-15 минут)")
    print("  2) Тестовый режим (50 упражнений, ~2 минуты)")
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
        print("  1. python3 manage.py makemigrations")
        print("  2. python3 manage.py migrate")
        print("  3. python3 manage.py loaddata authentication/fixtures/gym_exercises.json")
        print("  4. python3 manage.py load_gym_aliases")
        print("\n💡 Перевод названий можно добавить позже через админку или API")
        print()


if __name__ == '__main__':
    main()
