#!/usr/bin/env python3
"""
БЫСТРАЯ ИНСТРУКЦИЯ ПО ПЕРЕВОДУ УПРАЖНЕНИЙ
==========================================

1. УСТАНОВКА:
   pip install aiohttp

2. НАСТРОЙКА YANDEX CLOUD:
   - Создайте сервисный аккаунт: https://console.cloud.yandex.ru
   - Роль: ai.translate.user
   - Создайте API ключ (показывается 1 раз!)
   - Скопируйте Folder ID из URL: console.cloud.yandex.ru/folders/{ID}

3. НАСТРОЙКА CREDENTIALS:

   Вариант A - Файл .env (рекомендуется):
   ```
   YANDEX_TRANSLATE_API_KEY=AQVNxxx...
   YANDEX_FOLDER_ID=b1gxxxxxxxxx
   ```

   Вариант B - Переменные окружения:
   export YANDEX_TRANSLATE_API_KEY="..."
   export YANDEX_FOLDER_ID="..."

   Вариант C - Аргументы:
   python3 scripts/translate_exercises_async.py --api-key "..." --folder-id "..."

4. ЗАПУСК:

   # Тестовый запуск (без сохранения):
   python3 scripts/translate_exercises_async.py --dry-run

   # Реальный перевод:
   python3 scripts/translate_exercises_async.py

   # С кастомным батч-размером:
   python3 scripts/translate_exercises_async.py --batch-size 100

   # Перевести всё заново (даже переведённые):
   python3 scripts/translate_exercises_async.py --force

   # Перевести одно упражнение:
   python3 scripts/translate_exercises_async.py --exercise-id "uuid"

5. РЕЗУЛЬТАТ:
   ✅ Все упражнения получат поле name_ru
   ✅ API будет возвращать оба варианта (name и name_ru)
   ✅ ~30-60 секунд для 873 упражнений

6. ПРОВЕРКА:
   python3 manage.py shell
   >>> from authentication.models import Exercise
   >>> Exercise.objects.exclude(name_ru='').count()

📚 Полная документация: TRANSLATION_README.md
"""

print(__doc__)
