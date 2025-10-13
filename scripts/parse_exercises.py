"""
Скрипт для парсинга упражнений из репозитория wrkout/exercises.json
и адаптации под структуру Django модели Exercise

Использование:
    python scripts/parse_exercises.py

Требования:
    pip install requests googletrans==4.0.0rc1
"""

import json
import os
import sys
import requests
from typing import Dict, List, Optional
import time

# Добавляем путь к Django проекту
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Для перевода
try:
    from googletrans import Translator
    TRANSLATOR_AVAILABLE = True
except ImportError:
    print("⚠️  googletrans не установлен. Запустите: pip install googletrans==4.0.0rc1")
    TRANSLATOR_AVAILABLE = False


class ExerciseParser:
    """Парсер упражнений из wrkout/exercises.json"""
    
    # API для получения списка упражнений
    GITHUB_API = "https://api.github.com/repos/wrkout/exercises.json/contents/exercises"
    RAW_BASE_URL = "https://raw.githubusercontent.com/wrkout/exercises.json/master/exercises"
    
    # Маппинг категорий
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
    
    # Маппинг уровней сложности
    LEVEL_MAPPING = {
        'beginner': 'beginner',
        'intermediate': 'intermediate',
        'expert': 'advanced',
    }
    
    # Перевод категорий оборудования
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
    
    # Перевод групп мышц
    MUSCLE_TRANSLATION = {
        'abdominals': 'пресс',
        'hamstrings': 'бицепс бедра',
        'calves': 'икры',
        'shoulders': 'плечи',
        'adductors': 'приводящие мышцы',
        'glutes': 'ягодицы',
        'quadriceps': 'квадрицепс',
        'biceps': 'бицепс',
        'forearms': 'предплечья',
        'abductors': 'отводящие мышцы',
        'triceps': 'трицепс',
        'chest': 'грудь',
        'lower back': 'нижняя часть спины',
        'traps': 'трапеции',
        'middle back': 'средняя часть спины',
        'lats': 'широчайшие',
        'neck': 'шея',
    }
    
    def __init__(self):
        self.translator = Translator() if TRANSLATOR_AVAILABLE else None
        self.exercises = []
        self.translation_cache = {}
    
    def translate_text(self, text: str, max_retries=3) -> str:
        """Перевод текста с использованием Google Translate"""
        if not self.translator or not text:
            return text
        
        # Проверяем кэш
        if text in self.translation_cache:
            return self.translation_cache[text]
        
        for attempt in range(max_retries):
            try:
                result = self.translator.translate(text, src='en', dest='ru')
                translated = result.text
                self.translation_cache[text] = translated
                time.sleep(0.5)  # Задержка для избежания rate limit
                return translated
            except Exception as e:
                print(f"⚠️  Ошибка перевода '{text}': {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                return text
        
        return text
    
    def fetch_exercise_list(self) -> List[str]:
        """Получить список папок с упражнениями из GitHub API"""
        print("📥 Загрузка списка упражнений из GitHub...")
        
        try:
            response = requests.get(self.GITHUB_API)
            response.raise_for_status()
            data = response.json()
            
            # Фильтруем только папки (упражнения)
            folders = [item['name'] for item in data if item['type'] == 'dir']
            print(f"✓ Найдено {len(folders)} упражнений")
            return folders
        except Exception as e:
            print(f"❌ Ошибка загрузки списка: {e}")
            return []
    
    def fetch_exercise_data(self, folder_name: str) -> Optional[Dict]:
        """Загрузить данные конкретного упражнения"""
        url = f"{self.RAW_BASE_URL}/{folder_name}/exercise.json"
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"⚠️  Не удалось загрузить {folder_name}: {e}")
            return None
    
    def adapt_exercise(self, raw_data: Dict, index: int) -> Dict:
        """Адаптация упражнения под нашу структуру Django"""
        
        # Базовое название
        name = raw_data.get('name', 'Unknown Exercise')
        
        # Переводим название
        name_ru = self.translate_text(name) if self.translator else name
        
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
        
        # Инструкции
        instructions = raw_data.get('instructions', [])
        instructions_text = '\n'.join([f"{i+1}. {instr}" for i, instr in enumerate(instructions)])
        
        # Переводим инструкции
        if self.translator and instructions_text:
            instructions_ru = self.translate_text(instructions_text)
        else:
            instructions_ru = instructions_text
        
        # Описание
        description = raw_data.get('description', '')
        if self.translator and description:
            description_ru = self.translate_text(description)
        else:
            description_ru = description
        
        # Формируем полное описание с информацией о мышцах
        primary_muscles = raw_data.get('primaryMuscles', [])
        secondary_muscles = raw_data.get('secondaryMuscles', [])
        equipment = raw_data.get('equipment', '')
        
        muscles_info = []
        if primary_muscles:
            muscles_ru = [self.MUSCLE_TRANSLATION.get(m, m) for m in primary_muscles]
            muscles_info.append(f"Основные мышцы: {', '.join(muscles_ru)}")
        
        if secondary_muscles:
            muscles_ru = [self.MUSCLE_TRANSLATION.get(m, m) for m in secondary_muscles]
            muscles_info.append(f"Вспомогательные мышцы: {', '.join(muscles_ru)}")
        
        if equipment:
            equipment_ru = self.EQUIPMENT_TRANSLATION.get(equipment.lower(), equipment)
            muscles_info.append(f"Оборудование: {equipment_ru}")
        
        full_description = description_ru
        if muscles_info:
            full_description += '\n\n' + '\n'.join(muscles_info) if full_description else '\n'.join(muscles_info)
        
        # Формируем алиасы
        aliases = raw_data.get('aliases', [])
        
        # Добавляем оригинальное английское название как алиас
        if name.lower() != name_ru.lower():
            aliases.insert(0, name)
        
        # Добавляем вариант с оборудованием
        if equipment:
            equipment_ru = self.EQUIPMENT_TRANSLATION.get(equipment.lower(), equipment)
            # Удаляем оборудование из названия если оно там есть
            name_without_equipment = name_ru
            for eq in ['(Штанга)', '(Гантели)', '(Тренажёр)', '(Блок)']:
                name_without_equipment = name_without_equipment.replace(eq, '').strip()
            
            if equipment_ru not in name_ru.lower():
                aliases.append(f"{name_without_equipment} {equipment_ru}")
                aliases.append(f"{name_without_equipment} на {equipment_ru}")
        
        return {
            'model': 'authentication.exercise',
            'pk': None,  # Django автоматически создаст UUID
            'fields': {
                'name': name_ru,
                'description': full_description[:500] if full_description else '',  # Ограничиваем длину
                'category': category,
                'difficulty': difficulty,
                'duration_min': None,
                'duration_max': None,
                'repetitions': None,  # Можно добавить логику извлечения из instructions
                'instructions': instructions_ru,
                'audio_url': None,
                'video_url': None,
                'is_active': True,
                'usage_count': 0,
            },
            'aliases': aliases[:10]  # Ограничиваем количество алиасов
        }
    
    def parse_all(self, limit: Optional[int] = None) -> List[Dict]:
        """Парсинг всех упражнений"""
        folders = self.fetch_exercise_list()
        
        if limit:
            folders = folders[:limit]
            print(f"⚠️  Ограничение: обработка только {limit} упражнений")
        
        print(f"\n🔄 Начинаем парсинг {len(folders)} упражнений...")
        
        for i, folder in enumerate(folders, 1):
            print(f"[{i}/{len(folders)}] Обработка: {folder}...", end=' ')
            
            raw_data = self.fetch_exercise_data(folder)
            if raw_data:
                exercise = self.adapt_exercise(raw_data, i)
                self.exercises.append(exercise)
                print("✓")
            else:
                print("✗")
            
            # Небольшая задержка для избежания rate limiting
            time.sleep(0.3)
        
        print(f"\n✓ Обработано {len(self.exercises)} упражнений")
        return self.exercises
    
    def save_to_fixture(self, filename: str = 'gym_exercises.json'):
        """Сохранение в Django fixture формат"""
        output_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'authentication/fixtures',
            filename
        )
        
        # Создаём директорию если её нет
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Формируем финальные данные (без алиасов, они будут в отдельном файле)
        fixture_data = []
        aliases_data = {}
        
        for exercise in self.exercises:
            aliases = exercise.pop('aliases', [])
            fixture_data.append(exercise)
            
            # Сохраняем алиасы отдельно для последующего добавления
            exercise_name = exercise['fields']['name']
            aliases_data[exercise_name] = aliases
        
        # Сохраняем упражнения
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(fixture_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 Упражнения сохранены в: {output_path}")
        
        # Сохраняем алиасы в отдельный файл
        aliases_path = output_path.replace('.json', '_aliases.json')
        with open(aliases_path, 'w', encoding='utf-8') as f:
            json.dump(aliases_data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Алиасы сохранены в: {aliases_path}")
        
        return output_path, aliases_path
    
    def generate_alias_command(self, aliases_file: str):
        """Генерация команды для добавления алиасов"""
        command_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'authentication/management/commands/load_gym_aliases.py'
        )
        
        command_code = f'''"""
Management команда для загрузки алиасов упражнений из файла
Запустить: python manage.py load_gym_aliases
"""

from django.core.management.base import BaseCommand
from authentication.models import Exercise, ExerciseAlias
import json
import os


class Command(BaseCommand):
    help = 'Загружает алиасы для упражнений из JSON файла'
    
    def handle(self, *args, **options):
        aliases_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'fixtures/gym_exercises_aliases.json'
        )
        
        if not os.path.exists(aliases_file):
            self.stdout.write(self.style.ERROR(f'Файл не найден: {{aliases_file}}'))
            return
        
        with open(aliases_file, 'r', encoding='utf-8') as f:
            aliases_data = json.load(f)
        
        self.stdout.write('Загрузка алиасов для упражнений...')
        
        added_count = 0
        skipped_count = 0
        
        for exercise_name, aliases in aliases_data.items():
            try:
                exercise = Exercise.objects.get(name=exercise_name, is_active=True)
                
                for alias in aliases:
                    if not alias or not alias.strip():
                        continue
                    
                    alias = alias.strip()
                    
                    # Проверяем, не существует ли уже такой алиас
                    if not ExerciseAlias.objects.filter(exercise=exercise, alias__iexact=alias).exists():
                        ExerciseAlias.objects.create(
                            exercise=exercise,
                            alias=alias,
                            match_count=0
                        )
                        added_count += 1
                        self.stdout.write(f'  ✓ Добавлен алиас "{{alias}}" для "{{exercise_name}}"')
                    else:
                        skipped_count += 1
                        
            except Exercise.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f'  ⚠ Упражнение "{{exercise_name}}" не найдено')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'\\nГотово! Добавлено: {{added_count}}, Пропущено: {{skipped_count}}')
        )
'''
        
        with open(command_path, 'w', encoding='utf-8') as f:
            f.write(command_code)
        
        print(f"💾 Команда загрузки алиасов: {command_path}")


def main():
    print("=" * 60)
    print("🏋️  Парсер упражнений из wrkout/exercises.json")
    print("=" * 60)
    
    parser = ExerciseParser()
    
    # Спрашиваем пользователя о лимите
    print("\nСколько упражнений обработать?")
    print("  1) Все упражнения (может занять время)")
    print("  2) Ограниченное количество (для теста)")
    
    choice = input("\nВыбор [1/2]: ").strip()
    
    limit = None
    if choice == '2':
        limit_str = input("Введите количество упражнений (например, 50): ").strip()
        try:
            limit = int(limit_str)
        except ValueError:
            print("Неверный ввод, используем 50 по умолчанию")
            limit = 50
    
    # Парсим
    exercises = parser.parse_all(limit=limit)
    
    if not exercises:
        print("\n❌ Не удалось получить упражнения")
        return
    
    # Сохраняем
    fixture_path, aliases_path = parser.save_to_fixture()
    
    # Генерируем команду для загрузки алиасов
    parser.generate_alias_command(aliases_path)
    
    print("\n" + "=" * 60)
    print("✅ Парсинг завершён!")
    print("=" * 60)
    print("\n📋 Следующие шаги:")
    print("  1. python manage.py loaddata authentication/fixtures/gym_exercises.json")
    print("  2. python manage.py load_gym_aliases")
    print("\n")


if __name__ == '__main__':
    main()
