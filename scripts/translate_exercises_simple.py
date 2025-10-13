#!/usr/bin/env python3
"""
Простой асинхронный перевод упражнений через googletrans
Не требует API ключей - работает сразу!
"""

import os
import sys
import django
import asyncio
from pathlib import Path

# Настройка Django
sys.path.append(str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from authentication.models import Exercise
from asgiref.sync import sync_to_async


@sync_to_async
def get_exercises_without_translation():
    """Получить упражнения без перевода (async-safe)"""
    return list(Exercise.objects.filter(name_ru=''))


@sync_to_async
def save_translation(exercise_id, translation):
    """Сохранить перевод (async-safe)"""
    exercise = Exercise.objects.get(id=exercise_id)
    exercise.name_ru = translation
    exercise.save()


async def translate_exercises_simple():
    """Простой перевод через googletrans"""
    
    try:
        from googletrans import Translator
    except ImportError:
        print("❌ Модуль googletrans не установлен!")
        print("📦 Установите: pip install googletrans==4.0.0-rc1")
        sys.exit(1)
    
    translator = Translator()
    
    # Получить упражнения без перевода
    exercises = await get_exercises_without_translation()
    total = len(exercises)
    
    if total == 0:
        print("✅ Все упражнения уже переведены!")
        return
    
    print(f"🔄 Начинаем перевод {total} упражнений...")
    print(f"⚡ Используется бесплатный Google Translate\n")
    
    translated = 0
    errors = 0
    
    # Переводим по одному (Google Translate бесплатный имеет ограничения)
    for i, exercise in enumerate(exercises, 1):
        try:
            # Перевод
            result = translator.translate(exercise.name, src='en', dest='ru')
            translation = result.text
            
            # Сохранение (async-safe)
            await save_translation(exercise.id, translation)
            
            translated += 1
            
            # Прогресс
            percentage = (i / total) * 100
            print(f"[{i}/{total}] ({percentage:.1f}%) ✅ {exercise.name[:40]:<40} → {translation[:40]}")
            
            # Небольшая задержка чтобы не блокировать Google
            if i % 10 == 0:
                await asyncio.sleep(1)
            else:
                await asyncio.sleep(0.2)
                
        except Exception as e:
            errors += 1
            print(f"[{i}/{total}] ❌ Ошибка: {exercise.name[:40]} - {str(e)[:50]}")
            await asyncio.sleep(2)  # Больше задержка при ошибке
    
    # Статистика
    print("\n" + "="*70)
    print("📊 СТАТИСТИКА ПЕРЕВОДА")
    print("="*70)
    print(f"Всего упражнений: {total}")
    print(f"✅ Переведено: {translated}")
    print(f"❌ Ошибок: {errors}")
    print(f"Процент успеха: {(translated / total * 100):.1f}%")
    print("="*70)


if __name__ == '__main__':
    asyncio.run(translate_exercises_simple())
