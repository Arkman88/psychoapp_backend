"""
Сервисы для работы с Yandex Cloud API
- SpeechKit (распознавание речи)
- Vision (распознавание изображений)
- YandexGPT (генерация текста и рекомендаций)
"""

import requests
import base64
import subprocess
import tempfile
import os
import shutil
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class YandexSpeechKit:
    """Сервис для распознавания речи через Yandex SpeechKit"""
    
    BASE_URL = 'https://stt.api.cloud.yandex.net/speech/v1/stt:recognize'
    
    @classmethod
    def convert_to_oggopus(cls, audio_data):
        """
        Конвертация AAC/M4A → OggOpus для Yandex SpeechKit
        
        Args:
            audio_data: байтовые данные AAC аудио
            
        Returns:
            bytes: байтовые данные OggOpus
        """
        logger.info(f"Starting audio conversion, input size: {len(audio_data)} bytes")
        
        # Определяем путь к FFmpeg
        ffmpeg_path = shutil.which('ffmpeg') or '/usr/bin/ffmpeg'
        
        # Проверяем наличие FFmpeg
        if not os.path.exists(ffmpeg_path):
            raise Exception(f"FFmpeg не найден по пути {ffmpeg_path}. Установите: apt install ffmpeg (Ubuntu) или brew install ffmpeg (macOS)")
        
        try:
            ffmpeg_check = subprocess.run(
                [ffmpeg_path, '-version'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5
            )
            if ffmpeg_check.returncode != 0:
                raise Exception("FFmpeg не установлен или не работает")
            logger.info(f"FFmpeg найден: {ffmpeg_path} - {ffmpeg_check.stdout.decode('utf-8').splitlines()[0]}")
        except FileNotFoundError:
            raise Exception(f"FFmpeg не найден по пути {ffmpeg_path}")
        except subprocess.TimeoutExpired:
            raise Exception("FFmpeg не отвечает")
        
        # Создаём временный файл для входного AAC
        with tempfile.NamedTemporaryFile(suffix='.m4a', delete=False) as input_file:
            input_file.write(audio_data)
            input_path = input_file.name
        
        # Создаём временный файл для выходного OggOpus
        with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as output_file:
            output_path = output_file.name
        
        try:
            logger.info(f"Converting: {input_path} → {output_path}")
            
            # FFmpeg команда: AAC -> Ogg (Opus) в ogg-контейнере
            result = subprocess.run([
                ffmpeg_path,
                '-y',  # перезаписывать без подтверждения
                '-i', input_path,
                '-ac', '1',  # моно
                '-ar', '16000',  # 16kHz (требование Yandex)
                '-c:a', 'libopus',  # кодек Opus
                '-b:a', '64k',  # битрейт
                '-vbr', 'on',  # variable bitrate
                '-f', 'ogg',  # формат контейнера
                output_path
            ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
            
            logger.info(f"FFmpeg stdout: {result.stdout.decode('utf-8', errors='ignore')[:500]}")
            logger.info(f"FFmpeg stderr: {result.stderr.decode('utf-8', errors='ignore')[:500]}")
            
            # Проверяем, что файл создан и не пустой
            if not os.path.exists(output_path):
                raise Exception(f"FFmpeg не создал выходной файл: {output_path}")
            
            output_size = os.path.getsize(output_path)
            if output_size == 0:
                raise Exception("FFmpeg создал пустой файл")
            
            # Читаем результат
            with open(output_path, 'rb') as f:
                opus_data = f.read()
            
            logger.info(f"✅ Conversion successful: {len(audio_data)} → {len(opus_data)} bytes")
            return opus_data
            
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode('utf-8', errors='ignore') if e.stderr else 'Unknown error'
            logger.error(f"❌ FFmpeg conversion failed (exit code {e.returncode}): {error_msg}")
            raise Exception(f'FFmpeg conversion failed: {error_msg[:500]}')
        
        except subprocess.TimeoutExpired:
            logger.error("❌ FFmpeg timeout (>30s)")
            raise Exception("FFmpeg timeout: конвертация заняла больше 30 секунд")
            
        finally:
            # Удаляем временные файлы
            try:
                if os.path.exists(input_path):
                    os.unlink(input_path)
                if os.path.exists(output_path):
                    os.unlink(output_path)
            except Exception as cleanup_error:
                logger.warning(f"Cleanup error: {cleanup_error}")
    
    @classmethod
    def recognize_audio(cls, audio_data, lang='ru-RU'):
        """
        Распознать аудио файл с автоматической конвертацией
        
        Args:
            audio_data: байтовые данные аудио (AAC/M4A)
            lang: язык распознавания (по умолчанию ru-RU)
            
        Returns:
            str: распознанный текст
        """
        if not settings.YANDEX_GPT_API_KEY or not settings.YANDEX_GPT_FOLDER_ID:
            raise Exception('Yandex API ключи не настроены')
        
        logger.info(f"Starting speech recognition, input size: {len(audio_data)} bytes")
        
        # Конвертируем AAC → OggOpus
        opus_data = None
        conversion_error = None
        
        try:
            opus_data = cls.convert_to_oggopus(audio_data)
            logger.info(f"✅ Audio conversion successful: {len(audio_data)} → {len(opus_data)} bytes")
        except Exception as e:
            conversion_error = str(e)
            logger.error(f"❌ Audio conversion failed: {e}")
        
        # Если конвертация не удалась — возвращаем понятную ошибку
        if opus_data is None:
            error_msg = f"Не удалось сконвертировать аудио в OggOpus. FFmpeg ошибка: {conversion_error}. Проверьте, что FFmpeg установлен на сервере (apt install ffmpeg)."
            logger.error(error_msg)
            raise Exception(error_msg)
        
        headers = {
            'Authorization': f'Api-Key {settings.YANDEX_GPT_API_KEY}',
            'Content-Type': 'audio/ogg; codecs=opus',
        }
        
        params = {
            'folderId': settings.YANDEX_GPT_FOLDER_ID,
            'lang': lang,
        }
        
        logger.info(f"Sending {len(opus_data)} bytes to Yandex SpeechKit")
        
        response = requests.post(
            cls.BASE_URL,
            headers=headers,
            params=params,
            data=opus_data,
            timeout=30
        )
        
        logger.info(f"Yandex SpeechKit response: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            text = result.get('result', '')
            logger.info(f"Recognition successful: '{text}'")
            return text
        else:
            logger.error(f"SpeechKit error: {response.status_code} - {response.text}")
            raise Exception(f'SpeechKit error ({response.status_code}): {response.text}')


class YandexVision:
    """Сервис для распознавания изображений через Yandex Vision"""
    
    BASE_URL = 'https://vision.api.cloud.yandex.net/vision/v1/batchAnalyze'
    
    @classmethod
    def analyze_image(cls, image_data, features=None):
        """
        Анализ изображения
        
        Args:
            image_data: байтовые данные изображения
            features: список типов анализа (по умолчанию TEXT_DETECTION)
            
        Returns:
            dict: результаты анализа
        """
        if not settings.YANDEX_GPT_API_KEY or not settings.YANDEX_GPT_FOLDER_ID:
            raise Exception('Yandex API ключи не настроены')
        
        if features is None:
            features = [{'type': 'TEXT_DETECTION'}]
        
        headers = {
            'Authorization': f'Api-Key {settings.YANDEX_GPT_API_KEY}',
            'Content-Type': 'application/json',
        }
        
        # Конвертируем изображение в base64
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        body = {
            'folderId': settings.YANDEX_GPT_FOLDER_ID,
            'analyze_specs': [{
                'content': image_base64,
                'features': features
            }]
        }
        
        response = requests.post(
            cls.BASE_URL,
            headers=headers,
            json=body
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f'Vision error ({response.status_code}): {response.text}')
    
    @classmethod
    def extract_text_from_image(cls, image_data):
        """
        Извлечь текст из изображения
        
        Args:
            image_data: байтовые данные изображения
            
        Returns:
            str: извлеченный текст
        """
        result = cls.analyze_image(image_data)
        
        try:
            texts = []
            for spec_result in result.get('results', []):
                for result_item in spec_result.get('results', []):
                    if 'textDetection' in result_item:
                        for page in result_item['textDetection'].get('pages', []):
                            for block in page.get('blocks', []):
                                for line in block.get('lines', []):
                                    line_text = ' '.join([
                                        word['text'] 
                                        for word in line.get('words', [])
                                    ])
                                    texts.append(line_text)
            
            return '\n'.join(texts)
        except Exception as e:
            raise Exception(f'Ошибка парсинга результата Vision: {str(e)}')
    
    @classmethod
    def analyze_workout_image(cls, image_data):
        """
        Анализ изображения тренировки с очисткой и структурированием текста
        
        Args:
            image_data: байтовые данные изображения
            
        Returns:
            str: очищенный текст тренировки
        """
        from .yandex_services import YandexGPT
        
        # Сначала извлекаем текст из изображения
        raw_text = cls.extract_text_from_image(image_data)
        
        if not raw_text.strip():
            return ""
        
        # Затем очищаем и структурируем текст с помощью GPT
        system_prompt = """Ты — помощник для распознавания тренировок из фотографий.
Очисти и структурируй текст, извлечённый из изображения тренировки.

Правила:
- Убери лишний текст, оставь только упражнения
- Исправь опечатки в названиях упражнений
- Стандартизируй формат записи (упражнение вес×повторы)
- Если текст не о тренировке, верни пустую строку
- Группируй подходы одного упражнения вместе

Формат вывода: простой текст, каждое упражнение с новой строки."""

        user_prompt = f"""Очисти этот текст из изображения:

"{raw_text}"

Верни только очищенный текст тренировки или пустую строку если это не тренировка."""

        try:
            cleaned_text = YandexGPT.generate_text(user_prompt, temperature=0.3, system_prompt=system_prompt)
            return cleaned_text.strip()
        except Exception as e:
            # В случае ошибки возвращаем исходный текст
            return raw_text


class YandexGPT:
    """Сервис для работы с YandexGPT"""
    
    BASE_URL = 'https://llm.api.cloud.yandex.net/foundationModels/v1/completion'
    
    @classmethod
    def generate_text(cls, prompt, temperature=0.6, max_tokens=2000, system_prompt=None):
        """
        Генерация текста через YandexGPT
        
        Args:
            prompt: текст запроса пользователя
            temperature: температура генерации (0.0-1.0)
            max_tokens: максимальное количество токенов
            system_prompt: системный промпт (опционально)
            
        Returns:
            str: сгенерированный текст
        """
        if not settings.YANDEX_GPT_API_KEY or not settings.YANDEX_GPT_FOLDER_ID:
            raise Exception('YandexGPT API ключи не настроены')
        
        headers = {
            'Authorization': f'Api-Key {settings.YANDEX_GPT_API_KEY}',
            'Content-Type': 'application/json',
        }
        
        messages = []
        
        if system_prompt:
            messages.append({
                'role': 'system',
                'text': system_prompt,
            })
        
        messages.append({
            'role': 'user',
            'text': prompt,
        })
        
        body = {
            'modelUri': f'gpt://{settings.YANDEX_GPT_FOLDER_ID}/yandexgpt-lite',
            'completionOptions': {
                'stream': False,
                'temperature': temperature,
                'maxTokens': max_tokens,
            },
            'messages': messages
        }
        
        response = requests.post(
            cls.BASE_URL,
            headers=headers,
            json=body
        )
        
        if response.status_code == 200:
            result = response.json()
            return result['result']['alternatives'][0]['message']['text']
        else:
            raise Exception(f'YandexGPT error ({response.status_code}): {response.text}')
    
    @classmethod
    def parse_workout_from_text(cls, text):
        """
        Парсинг тренировки из текста с помощью YandexGPT
        
        Args:
            text: текст с описанием тренировки
            
        Returns:
            dict: структурированные данные тренировки
        """
        system_prompt = """Ты — помощник для фитнес-приложения. 
Твоя задача — преобразовать естественный текст с описанием тренировки в структурированный JSON формат.

Правила:
- Распознавай названия упражнений на русском и английском
- Преобразуй веса в числа (кг), повторения в числа
- Если вес не указан, используй 0
- Если повторения не указаны, используй 1
- Группируй подходы по упражнениям
- Создай читаемое formatted_text для отображения

Формат вывода: строго JSON без дополнительных комментариев."""

        user_prompt = f"""Преобразуй этот текст в формат тренировки:

"{text}"

Ответ в формате:
{{
  "exercises": [
    {{
      "name": "название упражнения",
      "sets": [
        {{"weight": 80, "reps": 10}},
        {{"weight": 85, "reps": 8}}
      ]
    }}
  ],
  "formatted_text": "жим лёжа 80×10, 85×8"
}}"""
        
        response = cls.generate_text(user_prompt, temperature=0.3, system_prompt=system_prompt)
        
        # Пытаемся распарсить JSON из ответа
        import json
        try:
            # Извлекаем JSON из ответа (может быть обёрнут в ```json)
            response = response.strip()
            if response.startswith('```'):
                response = response.split('```')[1]
                if response.startswith('json'):
                    response = response[4:]
            
            return json.loads(response.strip())
        except json.JSONDecodeError as e:
            # Fallback: возвращаем базовую структуру
            return {
                "exercises": [],
                "formatted_text": text,
                "error": f"Не удалось распарсить ответ: {str(e)}"
            }
    
    @classmethod
    def generate_workout_recommendations(cls, user_history):
        """
        Генерация рекомендаций на основе истории тренировок
        
        Args:
            user_history: словарь с историей тренировок пользователя
                {
                    "workouts": [...],  # список последних тренировок
                    "stats": {...},     # общая статистика
                    "records": {...}    # личные рекорды
                }
            
        Returns:
            str: рекомендации
        """
        system_prompt = """Ты — опытный AI-тренер, специализирующийся на силовых тренировках, бодибилдинге и анализе прогресса.

Твоя задача — дать конкретные, применимые советы на основе истории тренировок пользователя.

Правила рекомендаций:
- Анализируй прогресс, частоту тренировок, объёмы
- Давай советы по прогрессии, восстановлению, вариациям
- Учитывай текущую форму и возможное перетренированность
- Рекомендации должны быть реалистичными и безопасными
- Приоритизируй: высокая нагрузка → отдых, стагнация → смена программы

Формат вывода: строго JSON массив без дополнительных комментариев."""

        # Если передана строка, используем как есть
        if isinstance(user_history, str):
            history_text = user_history
        else:
            # Форматируем структурированные данные
            import json
            workouts = user_history.get('workouts', [])
            stats = user_history.get('stats', {})
            records = user_history.get('records', {})
            
            workouts_text = ""
            for workout in workouts[-5:]:  # последние 5 тренировок
                workouts_text += f"Дата: {workout.get('date', 'Неизвестно')}\n"
                for exercise in workout.get('exercises', []):
                    sets_text = ", ".join([f"{s.get('weight', 0)}×{s.get('reps', 0)}" for s in exercise.get('sets', [])])
                    workouts_text += f"- {exercise.get('name', 'Упражнение')}: {sets_text}\n"
                workouts_text += "\n"
            
            history_text = f"""СТАТИСТИКА:
- Всего тренировок: {stats.get('totalWorkouts', 0)}
- Общий объём: {stats.get('totalVolume', 0)} кг
- Текущая серия: {stats.get('currentStreak', 0)} дней подряд
- Средняя частота: {stats.get('avgFrequency', 0)} тренировок/неделю

ЛИЧНЫЕ РЕКОРДЫ:
{json.dumps(records, indent=2, ensure_ascii=False)}

ПОСЛЕДНИЕ ТРЕНИРОВКИ:
{workouts_text}"""

        prompt = f"""Проанализируй тренировочную историю пользователя и дай персональные рекомендации.

{history_text}

Дай 3-5 конкретных рекомендаций в формате JSON:
[
  {{
    "type": "progression|recovery|variation|technique|nutrition",
    "title": "Краткий заголовок",
    "description": "Подробное объяснение с конкретными советами",
    "priority": "low|medium|high"
  }}
]"""

        try:
            response = cls.generate_text(prompt, temperature=0.7, max_tokens=2000, system_prompt=system_prompt)
            
            # Пытаемся распарсить JSON
            import json
            response = response.strip()
            if response.startswith('```'):
                response = response.split('```')[1]
                if response.startswith('json'):
                    response = response[4:]
            
            recommendations = json.loads(response.strip())
            
            # Если это массив, возвращаем как есть
            if isinstance(recommendations, list):
                return recommendations[:5]  # максимум 5 рекомендаций
            
            # Если объект, оборачиваем в массив
            return [recommendations]
            
        except Exception as e:
            # Fallback: возвращаем текстовый ответ как одну рекомендацию
            return [
                {
                    "type": "analysis",
                    "title": "Рекомендации на основе истории",
                    "description": response if 'response' in locals() else str(e),
                    "priority": "medium"
                }
            ]
