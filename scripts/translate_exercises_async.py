#!/usr/bin/env python3
"""
Асинхронный перевод названий упражнений на русский язык
Использует Yandex Cloud Translate API
"""

import os
import sys
import django
import asyncio
import aiohttp
import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

# Настройка Django
sys.path.append(str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from authentication.models import Exercise
from django.conf import settings
from asgiref.sync import sync_to_async


class YandexTranslator:
    """Асинхронный переводчик через Yandex Cloud Translate API"""
    
    def __init__(self, api_key: str, folder_id: str):
        self.api_key = api_key
        self.folder_id = folder_id
        self.base_url = "https://translate.api.cloud.yandex.net/translate/v2/translate"
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Статистика
        self.total = 0
        self.translated = 0
        self.errors = 0
        self.skipped = 0
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def translate_text(self, text: str, source_lang: str = 'en', target_lang: str = 'ru') -> Optional[str]:
        """Перевести один текст"""
        if not self.session:
            raise RuntimeError("Session not initialized. Use 'async with' context manager")
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Api-Key {self.api_key}'
        }
        
        payload = {
            'folderId': self.folder_id,
            'texts': [text],
            'sourceLanguageCode': source_lang,
            'targetLanguageCode': target_lang
        }
        
        try:
            async with self.session.post(self.base_url, headers=headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    translations = data.get('translations', [])
                    if translations:
                        return translations[0].get('text')
                else:
                    error_text = await response.text()
                    print(f"❌ Ошибка перевода '{text}': {response.status} - {error_text}")
                    return None
        except Exception as e:
            print(f"❌ Исключение при переводе '{text}': {e}")
            return None
    
    async def translate_batch(self, texts: List[str], batch_size: int = 100) -> List[Optional[str]]:
        """Перевести пакет текстов"""
        if not self.session:
            raise RuntimeError("Session not initialized")
        
        # Yandex API поддерживает до 10000 символов за раз
        # Разбиваем на небольшие батчи
        results = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_results = await asyncio.gather(
                *[self.translate_text(text) for text in batch],
                return_exceptions=True
            )
            
            for result in batch_results:
                if isinstance(result, Exception):
                    print(f"❌ Ошибка в батче: {result}")
                    results.append(None)
                else:
                    results.append(result)
            
            # Небольшая задержка между батчами
            await asyncio.sleep(0.1)
        
        return results
    
    def print_stats(self):
        """Вывести статистику"""
        print("\n" + "="*60)
        print("📊 СТАТИСТИКА ПЕРЕВОДА")
        print("="*60)
        print(f"Всего упражнений: {self.total}")
        print(f"✅ Переведено: {self.translated}")
        print(f"⏭️  Пропущено (уже есть перевод): {self.skipped}")
        print(f"❌ Ошибок: {self.errors}")
        print(f"Процент успеха: {(self.translated / max(self.total - self.skipped, 1) * 100):.1f}%")
        print("="*60)


async def translate_exercises(
    api_key: str,
    folder_id: str,
    batch_size: int = 50,
    skip_existing: bool = True,
    dry_run: bool = False
):
    """
    Асинхронно переводит все упражнения
    
    Args:
        api_key: API ключ Yandex Cloud
        folder_id: ID папки в Yandex Cloud
        batch_size: Размер пакета для параллельного перевода
        skip_existing: Пропускать упражнения с существующим переводом
        dry_run: Режим тестирования без сохранения
    """
    
    # Получить упражнения без перевода
    if skip_existing:
        qs = Exercise.objects.filter(name_ru='')
    else:
        qs = Exercise.objects.all()

    exercises = await sync_to_async(list)(qs)
    total_count = len(exercises)
    
    if total_count == 0:
        print("✅ Все упражнения уже переведены!")
        return
    
    print(f"🔄 Начинаем перевод {total_count} упражнений...")
    print(f"📦 Размер батча: {batch_size}")
    print(f"🧪 Режим тестирования: {'Да' if dry_run else 'Нет'}")
    print("")
    
    async with YandexTranslator(api_key, folder_id) as translator:
        translator.total = total_count
        
        # Обрабатываем по батчам для контроля памяти
        for i in range(0, total_count, batch_size):
            batch = list(exercises[i:i + batch_size])
            
            print(f"📦 Батч {i//batch_size + 1}/{(total_count + batch_size - 1)//batch_size}")
            print(f"   Упражнения {i+1}-{min(i+batch_size, total_count)} из {total_count}")
            
            # Собираем тексты для перевода
            texts_to_translate = []
            exercises_map = {}
            
            for exercise in batch:
                # Пропускаем если уже есть перевод
                if skip_existing and exercise.name_ru:
                    translator.skipped += 1
                    continue
                
                texts_to_translate.append(exercise.name)
                exercises_map[exercise.name] = exercise
            
            if not texts_to_translate:
                print("   ⏭️  Все упражнения в батче уже переведены")
                continue
            
            # Переводим асинхронно
            translations = await translator.translate_batch(texts_to_translate, batch_size=20)
            
            # Сохраняем результаты
            updated_exercises = []
            
            for original, translation in zip(texts_to_translate, translations):
                exercise = exercises_map[original]
                
                if translation:
                    exercise.name_ru = translation
                    updated_exercises.append(exercise)
                    translator.translated += 1
                    print(f"   ✅ {original[:50]:<50} → {translation[:50]}")
                else:
                    translator.errors += 1
                    print(f"   ❌ Не удалось перевести: {original}")
            
            # Bulk update для производительности
            if updated_exercises and not dry_run:
                await sync_to_async(Exercise.objects.bulk_update)(updated_exercises, ['name_ru'])
            
            print("")
        
        # Итоговая статистика
        translator.print_stats()
        
        if dry_run:
            print("\n⚠️  ВНИМАНИЕ: Это был тестовый запуск. Изменения НЕ сохранены в БД.")


async def translate_single_exercise(exercise_id: str, api_key: str, folder_id: str):
    """Перевести одно конкретное упражнение"""
    try:
        exercise = Exercise.objects.get(id=exercise_id)
    except Exercise.DoesNotExist:
        print(f"❌ Упражнение с ID {exercise_id} не найдено")
        return
    
    print(f"📝 Переводим: {exercise.name}")
    
    async with YandexTranslator(api_key, folder_id) as translator:
        translation = await translator.translate_text(exercise.name)
        
        if translation:
            exercise.name_ru = translation
            exercise.save()
            print(f"✅ Перевод: {translation}")
            print(f"💾 Сохранено в БД")
        else:
            print(f"❌ Не удалось перевести")


def load_credentials():
    """Загрузить credentials из переменных окружения или файла"""
    api_key = os.getenv('YANDEX_TRANSLATE_API_KEY')
    folder_id = os.getenv('YANDEX_FOLDER_ID')
    
    if not api_key or not folder_id:
        # Попробовать загрузить из файла .env
        env_file = Path(__file__).parent.parent / '.env'
        if env_file.exists():
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('YANDEX_TRANSLATE_API_KEY='):
                        api_key = line.split('=', 1)[1].strip('"\'')
                    elif line.startswith('YANDEX_FOLDER_ID='):
                        folder_id = line.split('=', 1)[1].strip('"\'')
    
    return api_key, folder_id


async def main():
    """Главная функция"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Асинхронный перевод упражнений на русский')
    parser.add_argument('--api-key', help='Yandex Cloud API ключ')
    parser.add_argument('--folder-id', help='Yandex Cloud Folder ID')
    parser.add_argument('--batch-size', type=int, default=50, help='Размер батча (default: 50)')
    parser.add_argument('--force', action='store_true', help='Перевести все, даже с существующим переводом')
    parser.add_argument('--dry-run', action='store_true', help='Тестовый запуск без сохранения')
    parser.add_argument('--exercise-id', help='Перевести одно конкретное упражнение')
    
    args = parser.parse_args()
    
    # Загрузить credentials
    api_key = args.api_key
    folder_id = args.folder_id
    
    if not api_key or not folder_id:
        env_api_key, env_folder_id = load_credentials()
        api_key = api_key or env_api_key
        folder_id = folder_id or env_folder_id
    
    if not api_key or not folder_id:
        print("❌ Необходимо указать API ключ и Folder ID:")
        print("   1. Через аргументы: --api-key YOUR_KEY --folder-id YOUR_FOLDER_ID")
        print("   2. Через переменные окружения: YANDEX_TRANSLATE_API_KEY и YANDEX_FOLDER_ID")
        print("   3. Через файл .env в корне проекта")
        print("\n📖 Как получить credentials:")
        print("   https://cloud.yandex.ru/docs/translate/api-ref/authentication")
        sys.exit(1)
    
    # Запуск
    if args.exercise_id:
        await translate_single_exercise(args.exercise_id, api_key, folder_id)
    else:
        await translate_exercises(
            api_key=api_key,
            folder_id=folder_id,
            batch_size=args.batch_size,
            skip_existing=not args.force,
            dry_run=args.dry_run
        )


if __name__ == '__main__':
    asyncio.run(main())
