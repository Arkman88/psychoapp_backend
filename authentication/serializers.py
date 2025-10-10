from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from .models import UserSession

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

