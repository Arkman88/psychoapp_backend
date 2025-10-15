"""
Тесты для парсера упражнений
"""

from authentication.exercise_parser import ExerciseParser


def test_simple_pattern():
    """Тест простого шаблона"""
    
    # Тест 1: Классический формат
    result = ExerciseParser.parse("жим лежа 5 подходов по 40кг на 10 раз")
    print("\n=== Тест 1: Простой шаблон ===")
    print(f"Текст: 'жим лежа 5 подходов по 40кг на 10 раз'")
    print(f"Упражнение: {result['exercise_name']}")
    print(f"Структурировано: {result['is_structured']}")
    print(f"Подходы ({len(result['sets'])}):")
    for s in result['sets']:
        print(f"  - Подход {s['set_number']}: {s.get('reps', '?')} раз x {s.get('weight_kg', '?')}кг")
    if result.get('sets'):
        print(f"Краткое описание: {ExerciseParser.format_sets_summary(result['sets'])}")
    
    assert result['exercise_name'] == 'жим лежа'
    assert result['is_structured'] == True
    assert len(result['sets']) == 5
    assert result['sets'][0]['reps'] == 10
    assert result['sets'][0]['weight_kg'] == 40
    
    # Тест 2: С словами вместо цифр
    result2 = ExerciseParser.parse("приседания три подхода по двенадцать раз с весом 60кг")
    print("\n=== Тест 2: С текстовыми числами ===")
    print(f"Текст: 'приседания три подхода по двенадцать раз с весом 60кг'")
    print(f"Упражнение: {result2['exercise_name']}")
    print(f"Подходы: {len(result2['sets'])}")
    
    assert result2['exercise_name'] == 'приседания'
    assert len(result2['sets']) == 3
    assert result2['sets'][0]['reps'] == 12
    
    # Тест 3: Без веса
    result3 = ExerciseParser.parse("отжимания 4 подхода по 15 раз")
    print("\n=== Тест 3: Без веса ===")
    print(f"Текст: 'отжимания 4 подхода по 15 раз'")
    print(f"Упражнение: {result3['exercise_name']}")
    print(f"Подходы: {len(result3['sets'])}")
    print(f"Первый подход: {result3['sets'][0]}")
    
    assert result3['exercise_name'] == 'отжимания'
    assert len(result3['sets']) == 4
    assert result3['sets'][0]['reps'] == 15
    assert 'weight_kg' not in result3['sets'][0]


def test_complex_pattern():
    """Тест сложного шаблона"""
    
    # Тест 1: Разные веса
    result = ExerciseParser.parse("жим 3 подхода: 2 из них 4 раза по 40кг и один 4 раза по 50кг")
    print("\n=== Тест 4: Сложный шаблон (разные веса) ===")
    print(f"Текст: 'жим 3 подхода: 2 из них 4 раза по 40кг и один 4 раза по 50кг'")
    print(f"Упражнение: {result['exercise_name']}")
    print(f"Структурировано: {result['is_structured']}")
    print(f"Подходы ({len(result['sets'])}):")
    for s in result['sets']:
        print(f"  - Подход {s['set_number']}: {s.get('reps', '?')} раз x {s.get('weight_kg', '?')}кг")
    if result.get('sets'):
        print(f"Краткое описание: {ExerciseParser.format_sets_summary(result['sets'])}")
    
    assert result['exercise_name'] == 'жим'
    assert result['is_structured'] == True
    assert len(result['sets']) == 3
    assert result['sets'][0]['weight_kg'] == 40
    assert result['sets'][1]['weight_kg'] == 40
    assert result['sets'][2]['weight_kg'] == 50
    
    # Тест 2: Три группы
    result2 = ExerciseParser.parse("становая 5 подходов: 2 из них 5 раз по 100кг и 2 из них 3 раза по 120кг и один 1 раз по 140кг")
    print("\n=== Тест 5: Сложный шаблон (три группы) ===")
    print(f"Текст: 'становая 5 подходов: 2 из них 5 раз по 100кг и 2 из них 3 раза по 120кг и один 1 раз по 140кг'")
    print(f"Упражнение: {result2['exercise_name']}")
    print(f"Подходы ({len(result2['sets'])}):")
    for s in result2['sets']:
        print(f"  - Подход {s['set_number']}: {s.get('reps', '?')} раз x {s.get('weight_kg', '?')}кг")
    if result2.get('sets'):
        print(f"Краткое описание: {ExerciseParser.format_sets_summary(result2['sets'])}")
    
    assert result2['exercise_name'] == 'становая'
    assert len(result2['sets']) == 5


def test_unstructured():
    """Тест нераспознанных фраз"""
    
    result = ExerciseParser.parse("просто текст без структуры")
    print("\n=== Тест 6: Неструктурированный текст ===")
    print(f"Текст: 'просто текст без структуры'")
    print(f"Упражнение: {result['exercise_name']}")
    print(f"Структурировано: {result['is_structured']}")
    print(f"Подходы: {len(result['sets'])}")
    
    assert result['exercise_name'] == 'просто текст без структуры'
    assert result['is_structured'] == False
    assert len(result['sets']) == 0


if __name__ == '__main__':
    print("=" * 60)
    print("ТЕСТИРОВАНИЕ ПАРСЕРА УПРАЖНЕНИЙ")
    print("=" * 60)
    
    test_simple_pattern()
    test_complex_pattern()
    test_unstructured()
    
    print("\n" + "=" * 60)
    print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ")
    print("=" * 60)
