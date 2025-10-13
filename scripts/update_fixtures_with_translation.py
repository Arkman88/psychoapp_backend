#!/usr/bin/env python3
"""
Обновление fixture файла:
1. Добавление UUID
2. Скачивание картинок локально
3. Обновление путей к картинкам
"""

import json
import uuid
import os
import requests
import time
from pathlib import Path
from typing import Dict, List

# Пути
BASE_DIR = Path(__file__).resolve().parent.parent
FIXTURES_PATH = BASE_DIR / 'authentication' / 'fixtures' / 'gym_exercises.json'
MEDIA_ROOT = BASE_DIR / 'media' / 'exercises'
OUTPUT_PATH = BASE_DIR / 'authentication' / 'fixtures' / 'gym_exercises_translated.json'

# Создаём папку для изображений
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)


def generate_uuid() -> str:
    """Генерация UUID"""
    return str(uuid.uuid4())


def download_image(url: str, exercise_id: str, image_num: int) -> str:
    """Скачать изображение и вернуть локальный путь"""
    try:
        # Создаём папку для упражнения
        exercise_dir = MEDIA_ROOT / exercise_id
        exercise_dir.mkdir(exist_ok=True)
        
        # Скачиваем
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # Сохраняем
        file_path = exercise_dir / f'{image_num}.jpg'
        with open(file_path, 'wb') as f:
            f.write(response.content)
        
        # Возвращаем относительный путь для Django
        return f'/media/exercises/{exercise_id}/{image_num}.jpg'
    
    except Exception as e:
        print(f"  ❌ Ошибка скачивания {url}: {e}")
        return url  # Вернуть оригинальный URL


def process_exercise(exercise: Dict, index: int, total: int) -> Dict:
    """Обработка одного упражнения"""
    exercise_id = generate_uuid()
    fields = exercise['fields']
    name = fields.get('name', '<no-name>')
    
    print(f"\n[{index + 1}/{total}] {name}")
    
    # 1. Генерируем UUID
    exercise['pk'] = exercise_id
    
    # 2. Скачиваем изображения
    print(f"  🖼️  Скачивание изображений...")
    if fields.get('image_url_main'):
        fields['image_url_main'] = download_image(
            fields['image_url_main'], 
            exercise_id, 
            0
        )
    
    if fields.get('image_url_secondary'):
        fields['image_url_secondary'] = download_image(
            fields['image_url_secondary'], 
            exercise_id, 
            1
        )
    
    # 3. Добавляем timestamps
    fields['created_at'] = '2025-10-13T12:00:00Z'
    fields['updated_at'] = '2025-10-13T12:00:00Z'
    
    print(f"  ✅ Готово!")
    
    return exercise


def main():
    print("="*70)
    print("🌐 ОБНОВЛЕНИЕ FIXTURES (UUID + ЛОКАЛЬНЫЕ ИЗОБРАЖЕНИЯ)")
    print("="*70)
    
    # Загружаем JSON
    print(f"\n📥 Загрузка {FIXTURES_PATH}...")
    with open(FIXTURES_PATH, 'r', encoding='utf-8') as f:
        exercises = json.load(f)
    
    total = len(exercises)
    print(f"✓ Загружено {total} упражнений")
    
    # Спрашиваем режим
    print("\nВыберите режим:")
    print("  1) Все упражнения")
    print("  2) Тестовый (10 упражнений)")
    print("  3) Указать количество")
    
    choice = input("\nВыбор [1/2/3]: ").strip()
    
    limit = None
    if choice == '2':
        limit = 10
    elif choice == '3':
        try:
            limit = int(input("Количество: "))
        except Exception:
            print("Неверное число, используем все упражнения.")
            limit = None
    
    if limit:
        exercises = exercises[:limit]
        total = limit
    
    print(f"\n🔄 Обработка {total} упражнений...\n")
    
    # Обрабатываем
    updated_exercises = []
    errors = 0
    
    for i, exercise in enumerate(exercises):
        try:
            updated = process_exercise(exercise, i, total)
            updated_exercises.append(updated)
            
            # Прогресс каждые 10
            if (i + 1) % 10 == 0:
                percentage = ((i + 1) / total) * 100
                print(f"\n📊 Прогресс: {i + 1}/{total} ({percentage:.1f}%)")
                
        except Exception as e:
            errors += 1
            print(f"  ❌ ОШИБКА: {e}")
            # Сохраняем оригинал при ошибке
            updated_exercises.append(exercise)
    
    # Сохраняем результат
    print(f"\n💾 Сохранение в {OUTPUT_PATH}...")
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(updated_exercises, f, ensure_ascii=False, indent=2)
    
    # Статистика
    print("\n" + "="*70)
    print("📊 СТАТИСТИКА")
    print("="*70)
    print(f"Всего упражнений: {total}")
    print(f"✅ Обработано: {total - errors}")
    print(f"❌ Ошибок: {errors}")
    print(f"💾 Файл сохранён: {OUTPUT_PATH}")
    print(f"🖼️  Изображения в: {MEDIA_ROOT}")
    print("="*70)
    
    print("\n✨ Следующий шаг:")
    print(f"   python3 manage.py loaddata authentication/fixtures/gym_exercises_translated.json")


if __name__ == '__main__':
    main()