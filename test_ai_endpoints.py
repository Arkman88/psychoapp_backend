#!/usr/bin/env python3
"""
Примеры запросов к улучшенным AI endpoints
Демонстрация новых возможностей с детальными промптами
"""

import requests
import json

# Конфигурация
API_BASE_URL = 'http://89.22.235.198'
# Замените на ваш токен после авторизации
ACCESS_TOKEN = 'your-access-token-here'

headers = {
    'Authorization': f'Bearer {ACCESS_TOKEN}',
    'Content-Type': 'application/json'
}


def test_parse_workout_basic():
    """Тест базового парсинга текста"""
    print("\n" + "="*60)
    print("ТЕСТ 1: Базовый парсинг текста тренировки")
    print("="*60)
    
    texts = [
        "жим лёжа 80 кг 3 подхода по 10",
        "присед 100кг 5 по 5, становая тяга 120кг 3х8",
        "подтягивания своего веса 3 подхода по 12 повторений",
        "bench press 185 lbs 3x8",  # английский
    ]
    
    for text in texts:
        print(f"\nВход: {text}")
        
        response = requests.post(
            f'{API_BASE_URL}/api/auth/parse-workout/',
            headers=headers,
            json={'text': text}
        )
        
        if response.ok:
            result = response.json()
            print(f"✓ Ответ: {json.dumps(result['workout'], indent=2, ensure_ascii=False)}")
        else:
            print(f"✗ Ошибка: {response.text}")


def test_parse_workout_complex():
    """Тест сложного парсинга с разными форматами"""
    print("\n" + "="*60)
    print("ТЕСТ 2: Сложный парсинг (разные форматы)")
    print("="*60)
    
    complex_text = """
    Сегодняшняя тренировка:
    1. Жим штанги лёжа - 80кг на 10, потом 85кг на 8, последний 90 на 6
    2. Разводка гантелей 20 кг - 3 сета по 12
    3. Французский жим 35 килограмм 10 повторов 3 подхода
    """
    
    print(f"Вход:\n{complex_text}")
    
    response = requests.post(
        f'{API_BASE_URL}/api/auth/parse-workout/',
        headers=headers,
        json={'text': complex_text}
    )
    
    if response.ok:
        result = response.json()
        print(f"\n✓ Structured data:")
        print(json.dumps(result['workout'], indent=2, ensure_ascii=False))
        print(f"\nFormatted text: {result['workout'].get('formatted_text', '')}")
    else:
        print(f"✗ Ошибка: {response.text}")


def test_recommendations_simple():
    """Тест простых рекомендаций (текстовая история)"""
    print("\n" + "="*60)
    print("ТЕСТ 3: AI Рекомендации (текстовая история)")
    print("="*60)
    
    history = """
    Последние тренировки:
    - 10.10.2025: Жим лёжа 80кг 3x10, Жим гантелей 25кг 3x10
    - 08.10.2025: Становая тяга 120кг 3x8, Приседания 100кг 5x5
    - 06.10.2025: Жим лёжа 75кг 3x12, Разводка гантелей 20кг 3x12
    - 04.10.2025: Становая тяга 110кг 5x5, Подтягивания 3x10
    
    Цель: набор мышечной массы
    """
    
    print(f"История:\n{history}")
    
    response = requests.post(
        f'{API_BASE_URL}/api/auth/ai-recommendations/',
        headers=headers,
        json={'history': history}
    )
    
    if response.ok:
        result = response.json()
        print("\n✓ Рекомендации:")
        for i, rec in enumerate(result['recommendations'], 1):
            print(f"\n{i}. [{rec.get('type', 'general').upper()}] {rec.get('title', '')}")
            print(f"   Приоритет: {rec.get('priority', 'medium')}")
            print(f"   {rec.get('description', '')}")
    else:
        print(f"✗ Ошибка: {response.text}")


def test_recommendations_structured():
    """Тест структурированных рекомендаций"""
    print("\n" + "="*60)
    print("ТЕСТ 4: AI Рекомендации (структурированные данные)")
    print("="*60)
    
    data = {
        "workouts": [
            {
                "date": "2025-10-10",
                "exercises": [
                    {
                        "name": "Жим лёжа",
                        "sets": [
                            {"weight": 80, "reps": 10},
                            {"weight": 80, "reps": 10},
                            {"weight": 80, "reps": 9}
                        ]
                    },
                    {
                        "name": "Приседания",
                        "sets": [
                            {"weight": 100, "reps": 5},
                            {"weight": 100, "reps": 5},
                            {"weight": 100, "reps": 4}
                        ]
                    }
                ]
            },
            {
                "date": "2025-10-08",
                "exercises": [
                    {
                        "name": "Становая тяга",
                        "sets": [
                            {"weight": 120, "reps": 8},
                            {"weight": 120, "reps": 7},
                            {"weight": 120, "reps": 6}
                        ]
                    }
                ]
            }
        ],
        "stats": {
            "totalWorkouts": 15,
            "totalVolume": 45000,
            "currentStreak": 3,
            "avgFrequency": 3.5
        },
        "records": {
            "Жим лёжа": {"weight": 85, "reps": 8, "date": "2025-10-05"},
            "Приседания": {"weight": 110, "reps": 5, "date": "2025-09-28"},
            "Становая тяга": {"weight": 130, "reps": 5, "date": "2025-10-01"}
        }
    }
    
    print("Отправка структурированных данных...")
    
    response = requests.post(
        f'{API_BASE_URL}/api/auth/ai-recommendations/',
        headers=headers,
        json=data
    )
    
    if response.ok:
        result = response.json()
        print("\n✓ Персональные рекомендации:")
        for i, rec in enumerate(result['recommendations'], 1):
            priority_emoji = {
                'high': '🔴',
                'medium': '🟡',
                'low': '🟢'
            }.get(rec.get('priority', 'medium'), '⚪')
            
            print(f"\n{i}. {priority_emoji} [{rec.get('type', 'general').upper()}] {rec.get('title', '')}")
            print(f"   {rec.get('description', '')}")
    else:
        print(f"✗ Ошибка: {response.text}")


def test_image_analysis():
    """Тест анализа изображения с очисткой текста"""
    print("\n" + "="*60)
    print("ТЕСТ 5: Анализ изображения тренировки")
    print("="*60)
    
    # Для теста нужно иметь файл изображения
    try:
        with open('test_workout_image.jpg', 'rb') as f:
            files = {'image': f}
            
            response = requests.post(
                f'{API_BASE_URL}/api/auth/analyze-image/',
                headers={'Authorization': f'Bearer {ACCESS_TOKEN}'},
                files=files
            )
            
            if response.ok:
                result = response.json()
                print(f"\n✓ Извлечённый и очищенный текст:")
                print(result['text'])
            else:
                print(f"✗ Ошибка: {response.text}")
    except FileNotFoundError:
        print("⚠ Файл test_workout_image.jpg не найден")
        print("Создайте изображение с текстом тренировки для теста")


def main():
    """Главная функция"""
    print("="*60)
    print("ТЕСТИРОВАНИЕ УЛУЧШЕННЫХ AI ENDPOINTS")
    print("="*60)
    
    if ACCESS_TOKEN == 'your-access-token-here':
        print("\n❌ ОШИБКА: Установите ACCESS_TOKEN в начале файла")
        print("\nКак получить токен:")
        print(f"curl -X POST {API_BASE_URL}/api/auth/login/ \\")
        print('  -H "Content-Type: application/json" \\')
        print('  -d \'{"email":"your@email.com","password":"your-password"}\'')
        return
    
    try:
        # Запускаем тесты
        test_parse_workout_basic()
        test_parse_workout_complex()
        test_recommendations_simple()
        test_recommendations_structured()
        test_image_analysis()
        
        print("\n" + "="*60)
        print("✓ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
        print("="*60)
        
    except KeyboardInterrupt:
        print("\n\n⚠ Тестирование прервано")
    except Exception as e:
        print(f"\n\n❌ Ошибка: {e}")


if __name__ == '__main__':
    main()
