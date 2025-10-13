"""
Management команда для добавления алиасов к упражнениям
Запустить: python manage.py add_exercise_aliases
"""

from django.core.management.base import BaseCommand
from authentication.models import Exercise, ExerciseAlias


class Command(BaseCommand):
    help = 'Добавляет начальные алиасы для упражнений'
    
    # Словарь: название упражнения -> список алиасов
    ALIASES = {
        'Диафрагмальное дыхание': [
            'дыхание животом',
            'глубокое дыхание',
            'дыхательное упражнение',
            'дыхание диафрагмой',
            'брюшное дыхание',
            'животное дыхание',
        ],
        'Дыхание 4-7-8': [
            'дыхание четыре семь восемь',
            'техника 4-7-8',
            'упражнение 4 7 8',
            'дыхание для сна',
            'успокаивающее дыхание',
        ],
        'Прогрессивная мышечная релаксация': [
            'прогрессивная релаксация',
            'мышечная релаксация',
            'пмр',
            'напряжение и расслабление',
            'расслабление мышц',
        ],
        'Медитация осознанности': [
            'медитация',
            'осознанная медитация',
            'майндфулнес',
            'mindfulness медитация',
            'практика осознанности',
            'концентрация на дыхании',
        ],
        'Сканирование тела': [
            'бодискан',
            'body scan',
            'сканирование ощущений',
            'осознание тела',
            'путешествие по телу',
        ],
        'Визуализация безопасного места': [
            'безопасное место',
            'визуализация места',
            'представь безопасность',
            'воображаемое убежище',
            'мысленное убежище',
        ],
        'Заземление 5-4-3-2-1': [
            'заземление',
            'техника 5 4 3 2 1',
            'упражнение 54321',
            'пять чувств',
            'техника заземления',
            'grounding',
        ],
        'Когнитивная реструктуризация': [
            'реструктуризация мыслей',
            'когнитивное упражнение',
            'работа с мыслями',
            'изменение мышления',
            'переоценка мыслей',
        ],
        'Лёгкая растяжка': [
            'растяжка',
            'стретчинг',
            'потягивание',
            'разминка',
            'упражнения на растяжку',
            'мягкая растяжка',
        ],
        'Квадратное дыхание': [
            'коробочное дыхание',
            'дыхание квадратом',
            'box breathing',
            'дыхание 4-4-4-4',
            'равномерное дыхание',
        ],
    }
    
    def handle(self, *args, **options):
        self.stdout.write('Добавление алиасов для упражнений...')
        
        added_count = 0
        skipped_count = 0
        
        for exercise_name, aliases in self.ALIASES.items():
            try:
                exercise = Exercise.objects.get(name=exercise_name, is_active=True)
                
                for alias in aliases:
                    # Проверяем, не существует ли уже такой алиас
                    if not ExerciseAlias.objects.filter(exercise=exercise, alias=alias).exists():
                        ExerciseAlias.objects.create(
                            exercise=exercise,
                            alias=alias,
                            match_count=0
                        )
                        added_count += 1
                        self.stdout.write(f'  ✓ Добавлен алиас "{alias}" для "{exercise_name}"')
                    else:
                        skipped_count += 1
                        
            except Exercise.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f'  ⚠ Упражнение "{exercise_name}" не найдено')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'\nГотово! Добавлено: {added_count}, Пропущено: {skipped_count}')
        )
