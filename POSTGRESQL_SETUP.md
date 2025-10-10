# Настройка PostgreSQL для PsychoApp

## Установка PostgreSQL

### macOS
```bash
# Установка через Homebrew
brew install postgresql@15

# Запуск PostgreSQL
brew services start postgresql@15

# Проверка статуса
brew services list | grep postgresql
```

### Linux (Ubuntu/Debian)
```bash
# Установка
sudo apt update
sudo apt install postgresql postgresql-contrib

# Запуск
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Проверка
sudo systemctl status postgresql
```

### Windows
1. Скачайте установщик с https://www.postgresql.org/download/windows/
2. Запустите установщик и следуйте инструкциям
3. Запомните пароль для пользователя postgres

## Создание базы данных

### Способ 1: Через командную строку

```bash
# Подключение к PostgreSQL
psql postgres

# Создание пользователя (если нужно)
CREATE USER psychoapp_user WITH PASSWORD 'your_secure_password';

# Создание базы данных
CREATE DATABASE psychoapp_db;

# Предоставление прав
GRANT ALL PRIVILEGES ON DATABASE psychoapp_db TO psychoapp_user;

# Выход
\q
```

### Способ 2: Через createdb (macOS/Linux)

```bash
# Создание базы данных
createdb psychoapp_db

# Если нужен конкретный пользователь
createuser psychoapp_user --pwprompt
createdb -O psychoapp_user psychoapp_db
```

## Настройка .env файла

Обновите файл `.env` с вашими настройками PostgreSQL:

```env
# Database settings - PostgreSQL
DB_ENGINE=django.db.backends.postgresql
DB_NAME=psychoapp_db
DB_USER=postgres  # или psychoapp_user
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
```

## Применение миграций

После настройки базы данных:

```bash
# Активируйте виртуальное окружение
source .venv/bin/activate

# Примените миграции
python manage.py migrate

# Создайте суперпользователя
python manage.py createsuperuser
```

## Проверка подключения

```bash
# Подключение к базе данных
psql -h localhost -U postgres -d psychoapp_db

# Просмотр таблиц
\dt

# Просмотр пользователей
SELECT id, email, display_name, provider FROM users LIMIT 5;

# Выход
\q
```

## Полезные команды PostgreSQL

### Управление базами данных
```sql
-- Список всех баз данных
\l

-- Подключение к базе данных
\c psychoapp_db

-- Список таблиц
\dt

-- Описание таблицы
\d users

-- Размер базы данных
SELECT pg_size_pretty(pg_database_size('psychoapp_db'));
```

### Управление пользователями
```sql
-- Список пользователей
\du

-- Создание пользователя
CREATE USER psychoapp_user WITH PASSWORD 'password';

-- Изменение пароля
ALTER USER psychoapp_user WITH PASSWORD 'new_password';

-- Предоставление прав
GRANT ALL PRIVILEGES ON DATABASE psychoapp_db TO psychoapp_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO psychoapp_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO psychoapp_user;
```

### Резервное копирование

```bash
# Создание резервной копии
pg_dump psychoapp_db > backup.sql

# Создание резервной копии в custom формате
pg_dump -Fc psychoapp_db > backup.dump

# Восстановление из резервной копии
psql psychoapp_db < backup.sql

# Восстановление из custom формата
pg_restore -d psychoapp_db backup.dump
```

## Решение проблем

### Проблема: "role does not exist"
```bash
# Создайте пользователя
createuser -s postgres
```

### Проблема: "could not connect to server"
```bash
# Проверьте, запущен ли PostgreSQL
brew services list  # macOS
sudo systemctl status postgresql  # Linux

# Запустите PostgreSQL
brew services start postgresql  # macOS
sudo systemctl start postgresql  # Linux
```

### Проблема: "password authentication failed"
```bash
# Сбросьте пароль пользователя
psql postgres
ALTER USER postgres WITH PASSWORD 'new_password';
\q
```

### Проблема: "database does not exist"
```bash
# Создайте базу данных
createdb psychoapp_db
```

## Оптимизация для продакшена

В `settings.py` добавьте:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT'),
        'CONN_MAX_AGE': 600,  # Переиспользование соединений
        'OPTIONS': {
            'connect_timeout': 10,
        }
    }
}
```

## Мониторинг

### Просмотр активных подключений
```sql
SELECT pid, usename, application_name, client_addr, state 
FROM pg_stat_activity 
WHERE datname = 'psychoapp_db';
```

### Просмотр медленных запросов
```sql
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
```

## Ссылки

- [Документация PostgreSQL](https://www.postgresql.org/docs/)
- [Django Database Documentation](https://docs.djangoproject.com/en/5.0/ref/databases/#postgresql-notes)
- [psycopg2 Documentation](https://www.psycopg.org/docs/)
