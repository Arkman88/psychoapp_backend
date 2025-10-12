# PsychoApp Server

Django REST API сервер для мобильного приложения PsychoApp с функциями регистрации, аутентификации пользователей и интеграцией с AI сервисами.

## Возможности

- ✅ Регистрация и вход через Email/Password
- ✅ OAuth аутентификация (Google, Yandex, VK)
- ✅ JWT токены для безопасной аутентификации
- ✅ Управление профилем пользователя
- ✅ PostgreSQL база данных
- ✅ Интеграция с AI сервисами (Yandex GPT, ChatGPT, DeepSeek)

## Установка

1. Создайте виртуальное окружение:
```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# или .venv\Scripts\activate на Windows
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Настройте PostgreSQL:
```bash
# Установите PostgreSQL (macOS)
brew install postgresql
brew services start postgresql

# Создайте базу данных
createdb psychoapp_db
```

4. Настройте переменные окружения:
```bash
cp .env.example .env
# Отредактируйте .env файл с вашими настройками
```

5. Выполните миграции:
```bash
python manage.py makemigrations
python manage.py migrate
```

6. Создайте суперпользователя:
```bash
python manage.py createsuperuser
```

7. Запустите сервер:
```bash
python manage.py runserver
```

## Переменные окружения

### Основные настройки
- `SECRET_KEY` - секретный ключ Django
- `DEBUG` - режим отладки (True/False)
- `ALLOWED_HOSTS` - разрешенные хосты

### База данных PostgreSQL
- `DB_ENGINE` - django.db.backends.postgresql
- `DB_NAME` - имя базы данных (psychoapp_db)
- `DB_USER` - пользователь PostgreSQL
- `DB_PASSWORD` - пароль PostgreSQL
- `DB_HOST` - хост (localhost)
- `DB_PORT` - порт (5432)

### OAuth провайдеры
- `GOOGLE_OAUTH_CLIENT_ID` - Google OAuth Client ID
- `GOOGLE_OAUTH_CLIENT_SECRET` - Google OAuth Client Secret
- `YANDEX_CLIENT_ID` - Yandex OAuth Client ID
- `YANDEX_CLIENT_SECRET` - Yandex OAuth Client Secret

### AI API ключи
- `YANDEX_GPT_API_KEY` - API ключ Yandex GPT
- `YANDEX_GPT_FOLDER_ID` - ID папки Yandex Cloud
- `CHATGPT_API_KEY` - API ключ OpenAI (ChatGPT)
- `DEEPSEEK_API_KEY` - API ключ DeepSeek

## API Endpoints

### Регистрация
- **POST** `/api/auth/register/`
  ```json
  {
    "email": "user@example.com",
    "password": "SecurePassword123",
    "display_name": "Иван Иванов"
  }
  ```

### Вход
- **POST** `/api/auth/login/`
  ```json
  {
    "email": "user@example.com",
    "password": "SecurePassword123"
  }
  ```

### OAuth Аутентификация

#### Google
- **POST** `/api/auth/google/`
  ```json
  {
    "provider": "google",
    "id_token": "google_id_token_here",
    "email": "user@gmail.com",
    "display_name": "User Name",
    "photo_url": "https://..."
  }
  ```

#### Yandex
- **POST** `/api/auth/yandex/`
  ```json
  {
    "provider": "yandex",
    "access_token": "yandex_access_token"
  }
  ```

#### VK
- **POST** `/api/auth/vk/`
  ```json
  {
    "provider": "vk",
    "user": {
      "id": 123456,
      "first_name": "Иван",
      "last_name": "Иванов",
      "email": "user@vk.com"
    }
  }
  ```

### Обновление токена
- **POST** `/api/auth/refresh/`
  ```json
  {
    "refresh": "refresh_token_here"
  }
  ```

### Профиль пользователя
- **GET** `/api/auth/me/`
  - Headers: `Authorization: Bearer <access_token>`

- **PUT/PATCH** `/api/auth/me/`
  ```json
  {
    "display_name": "Новое Имя",
    "phone_number": "+7 999 123 45 67",
    "age": 25,
    "gender": "male",
    "country": "Russia",
    "language": "ru"
  }
  ```

### Смена пароля
- **POST** `/api/auth/change-password/`
  ```json
  {
    "old_password": "OldPassword123",
    "new_password": "NewPassword123"
  }
  ```

### Сброс пароля
- **POST** `/api/auth/reset-password/`
  ```json
  {
    "email": "user@example.com"
  }
  ```

### Выход
- **POST** `/api/auth/logout/`
  - Headers: `Authorization: Bearer <access_token>`
  ```json
  {
    "refresh": "refresh_token_here"
  }
  ```

## Структура проекта

```
ServerPsychoApp/
├── config/                 # Настройки проекта
│   ├── settings.py        # Основные настройки Django
│   ├── urls.py            # Главные URL маршруты
│   ├── ai_config.py       # Конфигурация AI сервисов
│   └── wsgi.py
├── authentication/         # Приложение аутентификации
│   ├── models.py          # Модели User, UserSession
│   ├── serializers.py     # Сериализаторы
│   ├── views.py           # API views
│   ├── urls.py            # URL маршруты
│   └── admin.py           # Админка
├── manage.py
├── requirements.txt
├── .env                   # Переменные окружения (не в git)
├── .env.example          # Пример переменных окружения
├── .gitignore
└── README.md
```

## Модели данных

### User (Пользователь)
- `id` - UUID (первичный ключ)
- `email` - Email (уникальный)
- `display_name` - Отображаемое имя
- `photo_url` - URL фото профиля
- `provider` - Провайдер аутентификации (email/google/yandex/vk)
- `provider_id` - ID в системе провайдера
- `phone_number` - Номер телефона
- `email_verified` - Email подтвержден
- `age` - Возраст
- `gender` - Пол
- `country` - Страна
- `language` - Язык
- `timezone` - Часовой пояс
- `notifications_enabled` - Уведомления включены
- `biometric_enabled` - Биометрия включена
- `theme` - Тема оформления
- `created_at` - Дата создания
- `updated_at` - Дата обновления
- `last_login_at` - Последний вход

### UserSession (Сессия пользователя)
- `user` - Пользователь (FK)
- `device_id` - ID устройства
- `device_type` - Тип устройства (ios/android)
- `device_name` - Название устройства
- `ip_address` - IP адрес
- `user_agent` - User Agent
- `refresh_token` - Refresh токен
- `is_active` - Активна
- `created_at` - Дата создания
- `last_activity` - Последняя активность

## Технологии

- Django 5.0
- Django REST Framework
- JWT Authentication (Simple JWT)
- PostgreSQL
- CORS Headers
- Python Decouple

## Разработка

### Создание миграций
```bash
python manage.py makemigrations
python manage.py migrate
```

### Запуск тестов
```bash
python test_api.py
```

### Доступ к админке
```
http://localhost:8000/admin/
```

## Деплой

Для продакшена:
1. Установите `DEBUG=False`
2. Настройте `ALLOWED_HOSTS`
3. Используйте сильный `SECRET_KEY`
4. Настройте PostgreSQL
5. Соберите статику: `python manage.py collectstatic`
6. Используйте Gunicorn + Nginx
7. Настройте HTTPS
8. Настройте CORS для вашего домена

## Лицензия

MIT
