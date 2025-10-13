#!/usr/bin/env python3
"""
Простой последовательный перевод с немедленным сохранением
Идеально для прерываний - можно продолжить в любой момент
"""

import os
import sys
import django
import time
import requests
from pathlib import Path

# Настройка Django
sys.path.append(str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from authentication.models import Exercise
from django.conf import settings


class SimpleTranslator:
    """Простой переводчик с rate limiting"""
    
    def __init__(self, api_key: str, folder_id: str, requests_per_second: int = 15):
        self.api_key = api_key
        self.folder_id = folder_id
        self.base_url = "https://translate.api.cloud.yandex.net/translate/v2/translate"
        self.delay = 1.0 / requests_per_second  # Задержка между запросами
        self.last_request_time = 0
        
        # Статистика
        self.total = 0
        self.translated = 0
        self.errors = 0
        self.skipped = 0
        self.start_time = None
    
    def translate_text(self, text: str, source_lang: str = 'en', target_lang: str = 'ru') -> str:
        """Перевести один текст"""
        # Rate limiting: ждём если нужно
        now = time.time()
        time_since_last = now - self.last_request_time
        if time_since_last < self.delay:
            time.sleep(self.delay - time_since_last)
        
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
        
        for attempt in range(1, 4):  # 3 попытки
            try:
                response = requests.post(
                    self.base_url,
                    headers=headers,
                    json=payload,
                    timeout=10
                )
                
                self.last_request_time = time.time()
                
                if response.status_code == 200:
                    data = response.json()
                    translations = data.get('translations', [])
                    if translations:
                        return translations[0].get('text')
                
                elif response.status_code == 429:  # Rate limit
                    retry_after = int(response.headers.get('Retry-After', 2))
                    print(f"      ⏳ Rate limit, ждём {retry_after}s...")
                    time.sleep(retry_after)
                    continue
                
                else:
                    print(f"      ❌ Ошибка {response.status_code}: {response.text[:100]}")
                    if attempt < 3:
                        time.sleep(2 ** (attempt - 1))
                        continue
                    return None
            
            except requests.exceptions.Timeout:
                print(f"      ⏱️  Timeout (попытка {attempt}/3)")
                if attempt < 3:
                    time.sleep(2)
                    continue
                return None
            
            except Exception as e:
                print(f"      ❌ Исключение: {e}")
                if attempt < 3:
                    time.sleep(2)
                    continue
                return None
        
        return None
    
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


def translate_exercises_simple(
    api_key: str,
    folder_id: str,
    requests_per_second: int = 15,
    skip_existing: bool = True
):
    """
    Последовательный перевод с немедленным сохранением
    """
    
    # Получить упражнения без перевода
    if skip_existing:
        exercises = list(Exercise.objects.filter(name_ru='').order_by('id'))
    else:
        exercises = list(Exercise.objects.all().order_by('id'))
    
    total_count = len(exercises)
    
    if total_count == 0:
        print("✅ Все упражнения уже переведены!")
        return
    
    translator = SimpleTranslator(api_key, folder_id, requests_per_second)
    translator.total = total_count
    translator.start_time = time.time()
    
    print("="*70)
    print("🌐 YANDEX TRANSLATE - ПОСЛЕДОВАТЕЛЬНЫЙ ПЕРЕВОД")
    print("="*70)
    print(f"📝 Упражнений к переводу: {total_count}")
    print(f"🚦 Rate limit: {requests_per_second} запросов/сек")
    print(f"💾 Сохранение: Немедленно после каждого перевода")
    print(f"⏭️  Пропуск переведённых: {'Да' if skip_existing else 'Нет'}")
    print(f"⏱️  Ожидаемое время: ~{total_count / requests_per_second:.0f} секунд")
    print("="*70 + "\n")
    
    try:
        for i, exercise in enumerate(exercises, 1):
            # Пропускаем если уже есть перевод
            if skip_existing and exercise.name_ru:
                translator.skipped += 1
                continue
            
            # Переводим
            translation = translator.translate_text(exercise.name)
            
            if translation:
                # Сохраняем немедленно
                exercise.name_ru = translation
                exercise.save()
                
                translator.translated += 1
                print(f"[{i}/{total_count}] ✅ {exercise.name[:45]:<45} → {translation[:45]}")
            else:
                translator.errors += 1
                print(f"[{i}/{total_count}] ❌ {exercise.name[:60]}")
            
            # Показываем промежуточную статистику каждые 100 упражнений
            if i % 100 == 0:
                elapsed = time.time() - translator.start_time
                rate = translator.translated / elapsed
                remaining = total_count - i
                eta = remaining / rate if rate > 0 else 0
                print(f"\n   💾 Сохранено {translator.translated}, ошибок {translator.errors}")
                print(f"   ⏱️  ETA: ~{eta:.0f}s ({rate:.2f} переводов/сек)\n")
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Прервано пользователем!")
        translator.print_stats()
        print("\n💡 Прогресс сохранён. Запустите скрипт снова для продолжения.")
        sys.exit(130)
    
    # Итоговая статистика
    translator.print_stats()
    print(f"\n✅ Переводы успешно сохранены в базе данных!")


def load_credentials():
    """Загрузить credentials из переменных окружения"""
    api_key = os.getenv('YANDEX_TRANSLATE_API_KEY') or os.getenv('YANDEX_API_KEY')
    folder_id = os.getenv('YANDEX_FOLDER_ID')
    
    if not api_key or not folder_id:
        env_file = Path(__file__).parent.parent / '.env'
        if env_file.exists():
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if '=' in line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        value = value.strip('"\'')
                        if key in ['YANDEX_TRANSLATE_API_KEY', 'YANDEX_API_KEY']:
                            api_key = value
                        elif key == 'YANDEX_FOLDER_ID':
                            folder_id = value
    
    return api_key, folder_id


def main():
    """Главная функция"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Последовательный перевод с немедленным сохранением',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  # Перевести все непереведённые (15 req/s)
  python scripts/translate_exercises_sequential.py
  
  # Увеличить скорость до 18 req/s
  python scripts/translate_exercises_sequential.py --rate-limit 18
  
  # Перевести все заново
  python scripts/translate_exercises_sequential.py --force

Особенности:
  - Можно прервать в любой момент (Ctrl+C)
  - Прогресс сохраняется после каждого перевода
  - Просто запустите снова для продолжения
        """
    )
    
    parser.add_argument('--api-key', help='Yandex Cloud API ключ')
    parser.add_argument('--folder-id', help='Yandex Cloud Folder ID')
    parser.add_argument('--rate-limit', type=int, default=15, help='Запросов в секунду (default: 15)')
    parser.add_argument('--force', action='store_true', help='Перевести все заново')
    
    args = parser.parse_args()
    
    # Загрузить credentials
    api_key = args.api_key or load_credentials()[0]
    folder_id = args.folder_id or load_credentials()[1]
    
    if not api_key or not folder_id:
        print("❌ Необходимо указать API ключ и Folder ID")
        print("   Добавьте в .env или передайте через аргументы")
        sys.exit(1)
    
    # Запуск
    translate_exercises_simple(
        api_key=api_key,
        folder_id=folder_id,
        requests_per_second=args.rate_limit,
        skip_existing=not args.force
    )


if __name__ == '__main__':
    main()
