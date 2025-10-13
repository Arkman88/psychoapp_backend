from django.contrib.auth.models import AbstractUser
from django.contrib.auth.base_user import BaseUserManager
from django.db import models
import uuid


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, username=None, **extra_fields):
        if not email:
            raise ValueError('The given email must be set')
        email = self.normalize_email(email)
        if username is None:
            username = email.split('@')[0]
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, username=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, username, **extra_fields)

    def create_superuser(self, email, password, username=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, username, **extra_fields)


class User(AbstractUser):
    """Кастомная модель пользователя с поддержкой OAuth провайдеров"""
    
    PROVIDER_CHOICES = [
        ('email', 'Email'),
        ('google', 'Google'),
        ('yandex', 'Яндекс'),
        ('vk', 'VK'),
        ('anonymous', 'Anonymous'),
    ]
    
    GENDER_CHOICES = [
        ('male', 'Мужской'),
        ('female', 'Женский'),
        ('other', 'Другой'),
        ('prefer_not_to_say', 'Предпочитаю не указывать'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    display_name = models.CharField(max_length=255)
    photo_url = models.URLField(blank=True, null=True)
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES, default='email')
    provider_id = models.CharField(max_length=255, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    email_verified = models.BooleanField(default=False)
    
    # Метаданные пользователя
    age = models.IntegerField(blank=True, null=True)
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    language = models.CharField(max_length=10, default='ru')
    timezone = models.CharField(max_length=50, default='Europe/Moscow')
    
    # Настройки
    notifications_enabled = models.BooleanField(default=True)
    biometric_enabled = models.BooleanField(default=False)
    theme = models.CharField(max_length=10, default='auto')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login_at = models.DateTimeField(null=True, blank=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['display_name']

    objects = UserManager()
    
    class Meta:
        db_table = 'users'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.email


class Exercise(models.Model):
    """Модель упражнения в базе"""
    
    CATEGORY_CHOICES = [
        ('breathing', 'Дыхательные'),
        ('relaxation', 'Расслабление'),
        ('meditation', 'Медитация'),
        ('physical', 'Физические'),
        ('mindfulness', 'Осознанность'),
        ('visualization', 'Визуализация'),
        ('cognitive', 'Когнитивные'),
        ('other', 'Другое'),
    ]
    
    DIFFICULTY_CHOICES = [
        ('beginner', 'Начальный'),
        ('intermediate', 'Средний'),
        ('advanced', 'Продвинутый'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, db_index=True)  # Основное название (английское)
    name_ru = models.CharField(max_length=255, blank=True, db_index=True, help_text='Русский перевод названия')
    description = models.TextField(blank=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='other')
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default='beginner')
    
    # Параметры упражнения
    duration_min = models.IntegerField(null=True, blank=True, help_text='Минимальная длительность в секундах')
    duration_max = models.IntegerField(null=True, blank=True, help_text='Максимальная длительность в секундах')
    repetitions = models.IntegerField(null=True, blank=True, help_text='Количество повторений')
    
    # Инструкции
    instructions = models.TextField(blank=True, help_text='Пошаговые инструкции')
    audio_url = models.URLField(blank=True, null=True, help_text='Ссылка на аудио-гайд')
    video_url = models.URLField(blank=True, null=True, help_text='Ссылка на видео-гайд')
    
    # Изображения
    image_url_main = models.URLField(blank=True, null=True, help_text='Основное изображение упражнения')
    image_url_secondary = models.URLField(blank=True, null=True, help_text='Дополнительное изображение')
    
    # Метаданные
    is_active = models.BooleanField(default=True)
    usage_count = models.IntegerField(default=0, help_text='Счётчик использования')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'exercises'
        ordering = ['-usage_count', 'name']
        indexes = [
            models.Index(fields=['category', 'difficulty']),
            models.Index(fields=['-usage_count']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"


class ExerciseAlias(models.Model):
    """Варианты названий и синонимы для упражнений"""
    
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, related_name='aliases')
    alias = models.CharField(max_length=255, db_index=True, help_text='Вариант названия или синоним')
    
    # Метрики для обучения
    match_count = models.IntegerField(default=0, help_text='Сколько раз этот алиас был выбран')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'exercise_aliases'
        unique_together = [['exercise', 'alias']]
        ordering = ['-match_count', 'alias']
        indexes = [
            models.Index(fields=['alias']),
        ]
    
    def __str__(self):
        return f"{self.alias} → {self.exercise.name}"


class UserExerciseLog(models.Model):
    """Лог использования упражнений пользователем"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='exercise_logs')
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, related_name='user_logs')
    
    # Данные распознавания
    recognized_text = models.TextField(blank=True, help_text='Распознанный текст от пользователя')
    confidence_score = models.FloatField(null=True, blank=True, help_text='Уверенность распознавания (0-1)')
    similarity_score = models.FloatField(null=True, blank=True, help_text='Оценка схожести (0-1)')
    
    # Параметры выполнения
    duration_seconds = models.IntegerField(null=True, blank=True)
    repetitions_done = models.IntegerField(null=True, blank=True)
    completed = models.BooleanField(default=False)
    
    # Обратная связь
    user_rating = models.IntegerField(null=True, blank=True, help_text='Оценка 1-5')
    user_notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'user_exercise_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['exercise', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.display_name} - {self.exercise.name} ({self.created_at.date()})"


class UserSession(models.Model):
    """Модель для отслеживания сессий пользователей"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    device_id = models.CharField(max_length=255)
    device_type = models.CharField(max_length=50)  # ios, android
    device_name = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    refresh_token = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_sessions'
        ordering = ['-last_activity']
    
    def __str__(self):
        return f"{self.user.email} - {self.device_type}"
