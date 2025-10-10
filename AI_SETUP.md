# Настройка AI Сервисов для PsychoApp

В проекте поддерживается интеграция с тремя AI сервисами:
- Yandex GPT
- ChatGPT (OpenAI)
- DeepSeek

## 1. Yandex GPT

### Получение API ключа

1. Зарегистрируйтесь в [Yandex Cloud](https://cloud.yandex.ru/)
2. Создайте каталог (folder) в консоли Yandex Cloud
3. Подключите сервис Yandex Foundation Models
4. Получите API ключ:
   - Перейдите в раздел "Сервисные аккаунты"
   - Создайте сервисный аккаунт
   - Назначьте роль `ai.languageModels.user`
   - Создайте API ключ

### Настройка в .env

```env
YANDEX_GPT_API_KEY=AQVN...your-api-key
YANDEX_GPT_FOLDER_ID=b1g...your-folder-id
```

### Пример использования

```python
import requests
from django.conf import settings

def call_yandex_gpt(prompt):
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    
    headers = {
        "Authorization": f"Api-Key {settings.YANDEX_GPT_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "modelUri": f"gpt://{settings.YANDEX_GPT_FOLDER_ID}/yandexgpt-lite",
        "completionOptions": {
            "stream": False,
            "temperature": 0.7,
            "maxTokens": 2000
        },
        "messages": [
            {
                "role": "user",
                "text": prompt
            }
        ]
    }
    
    response = requests.post(url, headers=headers, json=data)
    return response.json()
```

### Документация
- [Yandex GPT API](https://cloud.yandex.ru/docs/foundation-models/concepts/)
- [Быстрый старт](https://cloud.yandex.ru/docs/foundation-models/quickstart)

## 2. ChatGPT (OpenAI)

### Получение API ключа

1. Зарегистрируйтесь на [platform.openai.com](https://platform.openai.com/)
2. Перейдите в [API keys](https://platform.openai.com/api-keys)
3. Создайте новый API ключ
4. Пополните баланс аккаунта

### Настройка в .env

```env
CHATGPT_API_KEY=sk-...your-api-key
```

### Установка библиотеки

```bash
pip install openai
```

### Пример использования

```python
from openai import OpenAI
from django.conf import settings

client = OpenAI(api_key=settings.CHATGPT_API_KEY)

def call_chatgpt(prompt):
    response = client.chat.completions.create(
        model="gpt-4",  # или "gpt-3.5-turbo"
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=2000
    )
    return response.choices[0].message.content
```

### Модели и цены

| Модель | Входные токены | Выходные токены |
|--------|---------------|-----------------|
| GPT-4 | $0.03 / 1K | $0.06 / 1K |
| GPT-4 Turbo | $0.01 / 1K | $0.03 / 1K |
| GPT-3.5 Turbo | $0.0005 / 1K | $0.0015 / 1K |

### Документация
- [OpenAI API Documentation](https://platform.openai.com/docs/api-reference)
- [Python Library](https://github.com/openai/openai-python)

## 3. DeepSeek

### Получение API ключа

1. Зарегистрируйтесь на [platform.deepseek.com](https://platform.deepseek.com/)
2. Перейдите в раздел API Keys
3. Создайте новый API ключ
4. Пополните баланс (если требуется)

### Настройка в .env

```env
DEEPSEEK_API_KEY=sk-...your-api-key
```

### Пример использования

```python
import requests
from django.conf import settings

def call_deepseek(prompt):
    url = "https://api.deepseek.com/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 2000
    }
    
    response = requests.post(url, headers=headers, json=data)
    return response.json()
```

### Документация
- [DeepSeek API Documentation](https://platform.deepseek.com/api-docs/)

## Общая структура для работы с AI

### Создайте утилиту для AI запросов

`authentication/ai_utils.py`:

```python
from django.conf import settings
from config.ai_config import (
    YANDEX_GPT_CONFIG,
    CHATGPT_CONFIG,
    DEEPSEEK_CONFIG,
    DEFAULT_AI_PROVIDER
)
import requests


class AIService:
    """Универсальный сервис для работы с AI"""
    
    @staticmethod
    def get_completion(prompt, provider=None):
        """Получить ответ от AI"""
        provider = provider or DEFAULT_AI_PROVIDER
        
        if provider == 'yandex':
            return AIService._call_yandex_gpt(prompt)
        elif provider == 'chatgpt':
            return AIService._call_chatgpt(prompt)
        elif provider == 'deepseek':
            return AIService._call_deepseek(prompt)
        else:
            raise ValueError(f"Unknown AI provider: {provider}")
    
    @staticmethod
    def _call_yandex_gpt(prompt):
        """Yandex GPT запрос"""
        url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
        
        headers = {
            "Authorization": f"Api-Key {YANDEX_GPT_CONFIG['api_key']}",
            "Content-Type": "application/json"
        }
        
        data = {
            "modelUri": f"gpt://{YANDEX_GPT_CONFIG['folder_id']}/{YANDEX_GPT_CONFIG['model']}",
            "completionOptions": {
                "stream": False,
                "temperature": YANDEX_GPT_CONFIG['temperature'],
                "maxTokens": YANDEX_GPT_CONFIG['max_tokens']
            },
            "messages": [{"role": "user", "text": prompt}]
        }
        
        response = requests.post(url, headers=headers, json=data)
        result = response.json()
        
        if response.status_code == 200:
            return result['result']['alternatives'][0]['message']['text']
        else:
            raise Exception(f"Yandex GPT error: {result}")
    
    @staticmethod
    def _call_chatgpt(prompt):
        """ChatGPT запрос"""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=CHATGPT_CONFIG['api_key'])
            
            response = client.chat.completions.create(
                model=CHATGPT_CONFIG['model'],
                messages=[{"role": "user", "content": prompt}],
                temperature=CHATGPT_CONFIG['temperature'],
                max_tokens=CHATGPT_CONFIG['max_tokens']
            )
            
            return response.choices[0].message.content
        except ImportError:
            raise Exception("OpenAI library not installed. Run: pip install openai")
    
    @staticmethod
    def _call_deepseek(prompt):
        """DeepSeek запрос"""
        url = "https://api.deepseek.com/v1/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_CONFIG['api_key']}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": DEEPSEEK_CONFIG['model'],
            "messages": [{"role": "user", "content": prompt}],
            "temperature": DEEPSEEK_CONFIG['temperature'],
            "max_tokens": DEEPSEEK_CONFIG['max_tokens']
        }
        
        response = requests.post(url, headers=headers, json=data)
        result = response.json()
        
        if response.status_code == 200:
            return result['choices'][0]['message']['content']
        else:
            raise Exception(f"DeepSeek error: {result}")


# Пример использования
def get_ai_response(user_message, provider='yandex'):
    """Получить ответ от AI на сообщение пользователя"""
    try:
        response = AIService.get_completion(user_message, provider)
        return {
            'success': True,
            'response': response,
            'provider': provider
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'provider': provider
        }
```

### Использование в views

```python
from .ai_utils import get_ai_response

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ai_chat_view(request):
    """Отправить сообщение AI"""
    message = request.data.get('message')
    provider = request.data.get('provider', 'yandex')  # yandex, chatgpt, deepseek
    
    if not message:
        return Response({'error': 'Message is required'}, status=400)
    
    result = get_ai_response(message, provider)
    
    if result['success']:
        return Response({
            'response': result['response'],
            'provider': result['provider']
        })
    else:
        return Response({
            'error': result['error']
        }, status=500)
```

## Обновление requirements.txt

Добавьте необходимые библиотеки:

```txt
openai==1.12.0  # Для ChatGPT
```

## Переменная DEFAULT_AI_PROVIDER

В `.env` можете указать провайдера по умолчанию:

```env
DEFAULT_AI_PROVIDER=yandex  # или chatgpt, deepseek
```

## Безопасность

⚠️ **Важно:**
- Никогда не коммитьте `.env` файл в git
- Используйте разные API ключи для разработки и продакшена
- Установите лимиты расходов в настройках провайдеров
- Логируйте все AI запросы для мониторинга расходов
- Реализуйте rate limiting для AI endpoints

## Мониторинг расходов

Создайте модель для логирования AI запросов:

```python
class AIRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    provider = models.CharField(max_length=20)
    prompt = models.TextField()
    response = models.TextField()
    tokens_used = models.IntegerField(default=0)
    cost = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
```

## Полезные ссылки

- [Yandex GPT](https://cloud.yandex.ru/docs/foundation-models/)
- [OpenAI Platform](https://platform.openai.com/)
- [DeepSeek Platform](https://platform.deepseek.com/)
