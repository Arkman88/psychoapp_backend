# API Testing Examples

## Регистрация нового пользователя

```bash
curl -X POST http://127.0.0.1:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "TestPassword123!",
    "password_confirm": "TestPassword123!",
    "first_name": "Иван",
    "last_name": "Иванов"
  }'
```

## Вход (Login)

```bash
curl -X POST http://127.0.0.1:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "TestPassword123!"
  }'
```

## Получение профиля

```bash
curl -X GET http://127.0.0.1:8000/api/auth/profile/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Обновление профиля

```bash
curl -X PUT http://127.0.0.1:8000/api/auth/profile/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Новое Имя",
    "last_name": "Новая Фамилия"
  }'
```

## Обновление расширенного профиля

```bash
curl -X PATCH http://127.0.0.1:8000/api/auth/profile/update/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+7 999 123 45 67",
    "date_of_birth": "1990-01-01",
    "bio": "Краткая информация о себе"
  }'
```

## Обновление токена

```bash
curl -X POST http://127.0.0.1:8000/api/auth/token/refresh/ \
  -H "Content-Type: application/json" \
  -d '{
    "refresh": "YOUR_REFRESH_TOKEN"
  }'
```

## Смена пароля

```bash
curl -X POST http://127.0.0.1:8000/api/auth/change-password/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "old_password": "TestPassword123!",
    "new_password": "NewPassword123!",
    "new_password_confirm": "NewPassword123!"
  }'
```

## Выход (Logout)

```bash
curl -X POST http://127.0.0.1:8000/api/auth/logout/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "refresh": "YOUR_REFRESH_TOKEN"
  }'
```

---

## Пример работы с токенами для мобильного приложения

1. **Регистрация или вход** - получите `access` и `refresh` токены
2. **Сохраните токены** в безопасном хранилище приложения
3. **Используйте access token** для всех защищенных запросов в заголовке `Authorization: Bearer {access_token}`
4. **Обновляйте токен** когда access token истекает (через 1 час), используя refresh token
5. **При выходе** отправьте refresh token на endpoint logout для его блокировки

## Коды ответов

- `200 OK` - Успешный запрос
- `201 Created` - Успешное создание (регистрация)
- `400 Bad Request` - Ошибка валидации данных
- `401 Unauthorized` - Неверные учетные данные или токен
- `403 Forbidden` - Доступ запрещен
- `404 Not Found` - Ресурс не найден
