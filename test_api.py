# ...existing code...
#!/usr/bin/env python
"""
Скрипт для тестирования API регистрации и входа.
Запуск: python test_api.py
"""

import requests
import json
import sys

BASE_URL = "http://127.0.0.1:8000/api/auth"

def _parse_tokens(resp_json):
    if not resp_json:
        return None, None
    if 'tokens' in resp_json:
        t = resp_json['tokens']
        return t.get('accessToken') or t.get('access'), t.get('refreshToken') or t.get('refresh')
    if 'access' in resp_json and 'refresh' in resp_json:
        return resp_json.get('access'), resp_json.get('refresh')
    return resp_json.get('accessToken'), resp_json.get('refreshToken')

def test_register():
    print("\n=== Тестирование регистрации ===")
    data = {
        "email": "test@example.com",
        "password": "TestPassword123!",
        "display_name": "Test User"
    }
    resp = requests.post(f"{BASE_URL}/register/", json=data)
    print("Статус:", resp.status_code)
    try:
        print("Ответ:", json.dumps(resp.json(), indent=2, ensure_ascii=False))
    except Exception:
        print("Не удалось распарсить ответ, raw:", resp.text)
    return resp

def test_login(email, password):
    print("\n=== Тестирование входа ===")
    data = {"email": email, "password": password}
    resp = requests.post(f"{BASE_URL}/login/", json=data)
    print("Статус:", resp.status_code)
    try:
        print("Ответ:", json.dumps(resp.json(), indent=2, ensure_ascii=False))
    except Exception:
        print("Не удалось распарсить ответ, raw:", resp.text)
    return resp

if __name__ == "__main__":
    print("Убедитесь, что сервер запущен на http://127.0.0.1:8000")
    input("Нажмите Enter для начала...")
    r = test_register()
    # если 400 — печатаем тело (уже делается)
    if r.status_code == 201:
        tokens = _parse_tokens(r.json())
        access, refresh = tokens
        if access:
            h = {"Authorization": f"Bearer {access}"}
            p = requests.get(f"{BASE_URL}/me/", headers=h)
            print("Profile status:", p.status_code)
            print(p.text)
    # тест входа
    l = test_login("test@example.com", "TestPassword123!")
    sys.exit(0)