from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from .models import UserSession, Exercise, ExerciseAlias, UserExerciseLog

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Сериализатор для пользователя с метаданными"""
    metadata = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'display_name', 'photo_url', 'provider',
            'phone_number', 'email_verified', 'created_at', 'last_login_at',
            'metadata'
        ]
        read_only_fields = ['id', 'created_at', 'email_verified', 'provider']
    
    def get_metadata(self, obj):
        return {
            'age': obj.age,
            'gender': obj.gender,
            'country': obj.country,
            'language': obj.language,
            'timezone': obj.timezone,
            'preferences': {
                'notifications': obj.notifications_enabled,
                'biometric': obj.biometric_enabled,
                'theme': obj.theme,
            }
        }


class RegisterSerializer(serializers.ModelSerializer):
    """Сериализатор для регистрации пользователя через email/password"""
    password = serializers.CharField(
        write_only=True, 
        required=True, 
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    
    class Meta:
        model = User
        fields = ['email', 'password', 'display_name']
    
    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            username=validated_data['email'],
            display_name=validated_data['display_name'],
            password=validated_data['password'],
            provider='email'
        )
        return user


class LoginSerializer(serializers.Serializer):
    """Сериализатор для входа через email/password"""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})


class OAuthSerializer(serializers.Serializer):
    """Сериализатор для OAuth аутентификации"""
    provider = serializers.ChoiceField(choices=['google', 'yandex', 'vk'])
    id_token = serializers.CharField(required=False)
    access_token = serializers.CharField(required=False)
    user = serializers.DictField(required=False)


class UserSessionSerializer(serializers.ModelSerializer):
    """Сериализатор для сессий пользователя"""
    
    class Meta:
        model = UserSession
        fields = [
            'id', 'device_id', 'device_type', 'device_name',
            'ip_address', 'is_active', 'created_at', 'last_activity'
        ]
        read_only_fields = ['id', 'created_at', 'last_activity']


class ChangePasswordSerializer(serializers.Serializer):
    """Сериализатор для смены пароля"""
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(
        required=True, 
        write_only=True,
        validators=[validate_password]
    )
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Неверный текущий пароль")
        return value


class ResetPasswordSerializer(serializers.Serializer):
    """Сериализатор для сброса пароля"""
    email = serializers.EmailField(required=True)


# ========== Сериализаторы для упражнений ==========

class ExerciseAliasSerializer(serializers.ModelSerializer):
    """Сериализатор для вариантов названий упражнений"""
    
    class Meta:
        model = ExerciseAlias
        fields = ['id', 'alias', 'match_count']


class ExerciseSerializer(serializers.ModelSerializer):
    """Сериализатор для упражнений"""
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    difficulty_display = serializers.CharField(source='get_difficulty_display', read_only=True)
    aliases = ExerciseAliasSerializer(many=True, read_only=True)
    
    class Meta:
        model = Exercise
        fields = [
            'id', 'name', 'name_ru', 'description', 'category', 'category_display',
            'difficulty', 'difficulty_display', 'duration_min', 'duration_max',
            'repetitions', 'instructions', 'audio_url', 'video_url',
            'image_url_main', 'image_url_secondary',
            'usage_count', 'aliases', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'usage_count', 'created_at', 'updated_at']


class ExerciseMatchSerializer(serializers.Serializer):
    """Сериализатор для результатов сопоставления упражнений"""
    exercise_id = serializers.UUIDField()
    name = serializers.CharField()
    name_ru = serializers.CharField(allow_blank=True)
    matched_variant = serializers.CharField()
    category = serializers.CharField()
    category_display = serializers.CharField()
    difficulty = serializers.CharField()
    difficulty_display = serializers.CharField()
    description = serializers.CharField()
    similarity_score = serializers.FloatField()
    instructions = serializers.CharField()
    duration_min = serializers.IntegerField(allow_null=True)
    duration_max = serializers.IntegerField(allow_null=True)
    repetitions = serializers.IntegerField(allow_null=True)
    audio_url = serializers.URLField(allow_null=True)
    video_url = serializers.URLField(allow_null=True)
    image_url_main = serializers.URLField(allow_null=True)
    image_url_secondary = serializers.URLField(allow_null=True)
    usage_count = serializers.IntegerField()
    extracted_params = serializers.DictField()


class ExerciseMatchRequestSerializer(serializers.Serializer):
    """Сериализатор для запроса на поиск упражнений"""
    recognized_text = serializers.CharField(required=True, help_text='Распознанный текст')
    category = serializers.ChoiceField(
        choices=Exercise.CATEGORY_CHOICES,
        required=False,
        allow_null=True,
        help_text='Фильтр по категории'
    )
    confidence = serializers.FloatField(
        required=False,
        min_value=0.0,
        max_value=1.0,
        help_text='Уверенность распознавания речи (0-1)'
    )


class UserExerciseLogSerializer(serializers.ModelSerializer):
    """Сериализатор для логов выполнения упражнений"""
    exercise_name = serializers.CharField(source='exercise.name', read_only=True)
    exercise_category = serializers.CharField(source='exercise.category', read_only=True)
    
    class Meta:
        model = UserExerciseLog
        fields = [
            'id', 'exercise', 'exercise_name', 'exercise_category',
            'recognized_text', 'confidence_score', 'similarity_score',
            'duration_seconds', 'repetitions_done', 'completed',
            'user_rating', 'user_notes', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ExerciseConfirmSerializer(serializers.Serializer):
    """Сериализатор для подтверждения выбора упражнения пользователем"""
    exercise_id = serializers.UUIDField(required=True)
    recognized_text = serializers.CharField(required=True)
    similarity_score = serializers.FloatField(required=False)
    confidence_score = serializers.FloatField(required=False)
    duration_seconds = serializers.IntegerField(required=False, allow_null=True)
    repetitions_done = serializers.IntegerField(required=False, allow_null=True)
    completed = serializers.BooleanField(default=False)
    user_rating = serializers.IntegerField(required=False, allow_null=True, min_value=1, max_value=5)
    user_notes = serializers.CharField(required=False, allow_blank=True)


