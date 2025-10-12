"""
Конфигурация для AI сервисов
"""
from decouple import config

# Yandex GPT Configuration
YANDEX_GPT_CONFIG = {
    'api_key': config('YANDEX_GPT_API_KEY', default=''),
    'folder_id': config('YANDEX_GPT_FOLDER_ID', default=''),
    'model': 'yandexgpt-lite',  # или 'yandexgpt'
    'temperature': 0.7,
    'max_tokens': 2000,
}

# ChatGPT (OpenAI) Configuration
CHATGPT_CONFIG = {
    'api_key': config('CHATGPT_API_KEY', default=''),
    'model': 'gpt-4',  # или 'gpt-3.5-turbo'
    'temperature': 0.7,
    'max_tokens': 2000,
}

# DeepSeek Configuration
DEEPSEEK_CONFIG = {
    'api_key': config('DEEPSEEK_API_KEY', default=''),
    'model': 'deepseek-chat',
    'temperature': 0.7,
    'max_tokens': 2000,
}

# Выбор активного AI провайдера по умолчанию
DEFAULT_AI_PROVIDER = config('DEFAULT_AI_PROVIDER', default='yandex')  # 'yandex', 'chatgpt', 'deepseek'
