#!/usr/bin/env python3
"""
Асинхронный перевод упражнений с rate limiting для Yandex Translate API
Лимит: 20 запросов в секунду (используем 15 для безопасности)
"""

import os
import sys
import django
import asyncio
import aiohttp
import json
import time
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from collections import deque

# Настройка Django
sys.path.append(str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from authentication.models import Exercise
from django.conf import settings
from asgiref.sync import sync_to_async


class RateLimiter:
    """Rate limiter с sliding window"""
    
    def __init__(self, max_requests: int, time_window: float = 1.0):
        """
        Args:
            max_requests: Максимальное количество запросов
            time_window: Временное окно в секундах (по умолчанию 1 секунда)
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
        self.lock = asyncio.Lock()
    
    async def acquire(self):
        """Ожидание разрешения на выполнение запроса"""
        async with self.lock:
            now = time.time()
            
            # Удаляем старые запросы за пределами временного окна
            while self.requests and self.requests[0] < now - self.time_window:
                self.requests.popleft()
            
            # Если достигли лимита, ждём
            if len(self.requests) >= self.max_requests:
                # Время ожидания = время до выхода самого старого запроса из окна
                sleep_time = self.requests[0] + self.time_window - now + 0.01
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                    # Рекурсивно повторяем попытку
                    await self.acquire()
                    return
            
            # Добавляем текущий запрос
            self.requests.append(now)


class YandexTranslatorWithRateLimit:
    """Переводчик Yandex с rate limiting"""
    
    def __init__(self, api_key: str, folder_id: str, requests_per_second: int = 15):
        self.api_key = api_key
        self.folder_id = folder_id
        self.base_url = "https://translate.api.cloud.yandex.net/translate/v2/translate"
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Rate limiter (15 req/s для безопасности, лимит 20 req/s)
        self.rate_limiter = RateLimiter(max_requests=requests_per_second, time_window=1.0)
        
        # Статистика
        self.total = 0
        self.translated = 0
        self.errors = 0
        self.skipped = 0
        self.start_time = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        self.start_time = time.time()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def _request_with_retries(
        self, 
        text: str, 
        source_lang: str = 'en', 
        target_lang: str = 'ru',
        max_retries: int = 3
    ) -> Optional[str]:
        """Выполнить запрос с retry и exponential backoff"""
        
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
        
        for attempt in range(1, max_retries + 1):
            try:
                # Ждём разрешения от rate limiter
                await self.rate_limiter.acquire()
                
                async with self.session.post(self.base_url, headers=headers, json=payload, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        translations = data.get('translations', [])
                        if translations:
                            return translations[0].get('text')
                    
                    elif response.status == 429:  # Too Many Requests
                        retry_after = int(response.headers.get('Retry-After', 2))
                        print(f"   ⏳ Rate limit (попытка {attempt}/{max_retries}), ждём {retry_after}s...")
                        await asyncio.sleep(retry_after)
                        continue
                    
                    else:
                        error_text = await response.text()
                        print(f"   ❌ Ошибка {response.status} (попытка {attempt}/{max_retries}): {error_text[:100]}")
                        
                        if attempt < max_retries:
                            backoff = 2 ** (attempt - 1)  # 1s, 2s, 4s
                            await asyncio.sleep(backoff)
                            continue
                        
                        return None
            
            except asyncio.TimeoutError:
                print(f"   ⏱️  Timeout (попытка {attempt}/{max_retries})")
                if attempt < max_retries:
                    await asyncio.sleep(2 ** (attempt - 1))
                    continue
                return None
            
            except Exception as e:
                print(f"   ❌ Исключение (попытка {attempt}/{max_retries}): {e}")
                if attempt < max_retries:
                    await asyncio.sleep(2 ** (attempt - 1))
                    continue
                return None
        
        return None
    
    async def translate_text(self, text: str, source_lang: str = 'en', target_lang: str = 'ru') -> Optional[str]:
        """Перевести один текст"""
        if not self.session:
            raise RuntimeError("Session not initialized. Use 'async with' context manager")
        
        return await self._request_with_retries(text, source_lang, target_lang)
    
    def print_stats(self):
        """Вывести статистику"""
        elapsed = time.time() - self.start_time if self.start_time else 0
        rate = self.translated / elapsed if elapsed > 0 else 0
        
        print("\n" + "="*70)
        print("📊 СТАТИСТИКА ПЕРЕВОДА")
        print("="*70)
        print(f"Всего упражнений: {self.total}")
        print(f"✅ Переведено: {self.translated}")
        print(f"⏭️  Пропущено (уже есть перевод): {self.skipped}")
        print(f"❌ Ошибок: {self.errors}")
        print(f"⏱️  Время работы: {elapsed:.1f}s")
        print(f"🚀 Средняя скорость: {rate:.2f} переводов/сек")
        print(f"📈 Процент успеха: {(self.translated / max(self.total - self.skipped, 1) * 100):.1f}%")
        print("="*70)


async def translate_exercises(
    api_key: str,
    folder_id: str,
    requests_per_second: int = 15,
    batch_size: int = 100,
    skip_existing: bool = True,
    dry_run: bool = False
):
    """
    Асинхронно переводит все упражнения с rate limiting
    
    Args:
        api_key: API ключ Yandex Cloud
        folder_id: ID папки в Yandex Cloud
        requests_per_second: Лимит запросов в секунду (по умолчанию 15)
        batch_size: Размер батча для сохранения в БД (по умолчанию 100)
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
    
    print("="*70)
    print("🌐 YANDEX TRANSLATE - АСИНХРОННЫЙ ПЕРЕВОД С RATE LIMITING")
    print("="*70)
    print(f"📝 Упражнений к переводу: {total_count}")
    print(f"🚦 Rate limit: {requests_per_second} запросов/сек")
    print(f"💾 Размер батча для сохранения: {batch_size}")
    print(f"🧪 Режим тестирования: {'Да' if dry_run else 'Нет'}")
    print(f"⏭️  Пропуск переведённых: {'Да' if skip_existing else 'Нет'}")
    print("="*70 + "\n")
    
    async with YandexTranslatorWithRateLimit(api_key, folder_id, requests_per_second) as translator:
        translator.total = total_count
        
        # Обрабатываем с контролируемым параллелизмом
        semaphore = asyncio.Semaphore(10)  # Максимум 10 одновременных запросов
        save_batch = []
        save_lock = asyncio.Lock()
        
        async def translate_exercise(exercise: Exercise, index: int):
            """Перевести одно упражнение и сохранить батчами"""
            nonlocal save_batch
            
            async with semaphore:
                # Пропускаем если уже есть перевод
                if skip_existing and exercise.name_ru:
                    translator.skipped += 1
                    return None
                
                translation = await translator.translate_text(exercise.name)
                
                if translation:
                    translator.translated += 1
                    print(f"   [{index+1}/{total_count}] ✅ {exercise.name[:40]:<40} → {translation[:40]}")
                    
                    exercise.name_ru = translation
                    
                    # Сохраняем батчами сразу же
                    if not dry_run:
                        async with save_lock:
                            save_batch.append(exercise)
                            
                            # Когда набрали batch_size - сохраняем
                            if len(save_batch) >= batch_size:
                                await sync_to_async(Exercise.objects.bulk_update)(save_batch, ['name_ru'])
                                print(f"   💾 Сохранено {translator.translated} переводов")
                                save_batch = []
                    
                    return (exercise, translation)
                else:
                    translator.errors += 1
                    print(f"   [{index+1}/{total_count}] ❌ {exercise.name[:60]}")
                    return None
        
        # Запускаем все переводы параллельно (с контролем через semaphore и rate_limiter)
        tasks = [translate_exercise(ex, i) for i, ex in enumerate(exercises)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Сохраняем остаток батча
        if save_batch and not dry_run:
            print(f"\n💾 Сохраняем последний батч ({len(save_batch)} упражнений)...")
            await sync_to_async(Exercise.objects.bulk_update)(save_batch, ['name_ru'])
            print(f"   ✅ Итого сохранено: {translator.translated}")
        
        # Итоговая статистика
        translator.print_stats()
        
        if dry_run:
            print("\n⚠️  ВНИМАНИЕ: Это был тестовый запуск. Изменения НЕ сохранены в БД.")
        else:
            print(f"\n✅ Переводы успешно сохранены в базе данных!")


def load_credentials():
    """Загрузить credentials из переменных окружения"""
    api_key = os.getenv('YANDEX_TRANSLATE_API_KEY') or os.getenv('YANDEX_API_KEY')
    folder_id = os.getenv('YANDEX_FOLDER_ID')
    
    if not api_key or not folder_id:
        # Попробовать загрузить из файла .env
        env_file = Path(__file__).parent.parent / '.env'
        if env_file.exists():
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if '=' in line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        value = value.strip('"\'')
                        if key == 'YANDEX_TRANSLATE_API_KEY' or key == 'YANDEX_API_KEY':
                            api_key = value
                        elif key == 'YANDEX_FOLDER_ID':
                            folder_id = value
    
    return api_key, folder_id


async def main():
    """Главная функция"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Асинхронный перевод упражнений с rate limiting',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  # Перевести все непереведённые упражнения (15 req/s)
  python scripts/translate_exercises_with_rate_limit.py
  
  # Тестовый запуск без сохранения
  python scripts/translate_exercises_with_rate_limit.py --dry-run
  
  # Увеличить скорость до 18 req/s (осторожно!)
  python scripts/translate_exercises_with_rate_limit.py --rate-limit 18
  
  # Перевести все заново (force)
  python scripts/translate_exercises_with_rate_limit.py --force
        """
    )
    
    parser.add_argument('--api-key', help='Yandex Cloud API ключ')
    parser.add_argument('--folder-id', help='Yandex Cloud Folder ID')
    parser.add_argument('--rate-limit', type=int, default=15, help='Запросов в секунду (default: 15, max: 20)')
    parser.add_argument('--batch-size', type=int, default=100, help='Размер батча для сохранения (default: 100)')
    parser.add_argument('--force', action='store_true', help='Перевести все, даже с существующим переводом')
    parser.add_argument('--dry-run', action='store_true', help='Тестовый запуск без сохранения')
    
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
        print("   2. Через переменные окружения: YANDEX_API_KEY и YANDEX_FOLDER_ID")
        print("   3. Через файл .env в корне проекта")
        print("\n📖 Как получить credentials:")
        print("   https://cloud.yandex.ru/docs/translate/api-ref/authentication")
        sys.exit(1)
    
    # Проверка rate limit
    if args.rate_limit > 20:
        print("⚠️  ВНИМАНИЕ: Лимит Yandex Translate - 20 req/s!")
        print(f"   Установлено: {args.rate_limit} req/s")
        print("   Рекомендуется: 15-18 req/s для безопасности")
        response = input("   Продолжить? (y/N): ")
        if response.lower() != 'y':
            sys.exit(0)
    
    # Запуск
    try:
        await translate_exercises(
            api_key=api_key,
            folder_id=folder_id,
            requests_per_second=args.rate_limit,
            batch_size=args.batch_size,
            skip_existing=not args.force,
            dry_run=args.dry_run
        )
    except KeyboardInterrupt:
        print("\n\n⚠️  Прервано пользователем")
        sys.exit(130)


if __name__ == '__main__':
    asyncio.run(main())
