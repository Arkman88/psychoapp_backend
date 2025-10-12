from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, get_user_model
from django.conf import settings
from datetime import datetime
import requests as http_requests
import json

from .serializers import (
    RegisterSerializer, 
    LoginSerializer, 
    UserSerializer,
    ChangePasswordSerializer,
    OAuthSerializer,
    ResetPasswordSerializer,
)
from .models import UserSession
from .yandex_services import YandexSpeechKit, YandexVision, YandexGPT

User = get_user_model()


def get_tokens_for_user(user):
    """Генерация JWT токенов для пользователя"""
    refresh = RefreshToken.for_user(user)
    return {
        'accessToken': str(refresh.access_token),
        'refreshToken': str(refresh),
        'expiresIn': 3600,  # 1 час
    }


def get_client_ip(request):
    """Получение IP адреса клиента"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    """Регистрация через email/password"""
    # Преобразуем возможные camelCase поля от клиента в snake_case
    data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
    if 'displayName' in data and 'display_name' not in data:
        data['display_name'] = data.pop('displayName')
    if 'photoUrl' in data and 'photo_url' not in data:
        data['photo_url'] = data.pop('photoUrl')
    # можно добавить другие маппинги при необходимости
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        tokens = get_tokens_for_user(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'tokens': tokens,
        }, status=status.HTTP_201_CREATED)
    
    print("REGISTER FAILED. request.data =", request.data)
    print("REGISTER ERRORS =", serializer.errors)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """Вход через email/password"""
    serializer = LoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    email = serializer.validated_data['email']
    password = serializer.validated_data['password']
    
    # Аутентификация по email
    try:
        user = User.objects.get(email=email)
        if not user.check_password(password):
            return Response(
                {'message': 'Неверный email или пароль'},
                status=status.HTTP_401_UNAUTHORIZED
            )
    except User.DoesNotExist:
        return Response(
            {'message': 'Неверный email или пароль'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    # Обновляем время последнего входа
    user.last_login_at = datetime.now()
    user.save()
    
    tokens = get_tokens_for_user(user)
    
    return Response({
        'user': UserSerializer(user).data,
        'tokens': tokens,
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def google_login_view(request):
    """Вход через Google OAuth"""
    serializer = OAuthSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    id_token = serializer.validated_data.get('id_token')
    
    try:
        # В продакшене здесь должна быть проверка Google токена
        # from google.oauth2 import id_token as google_id_token
        # from google.auth.transport import requests
        # idinfo = google_id_token.verify_oauth2_token(
        #     id_token, requests.Request(), settings.GOOGLE_OAUTH_CLIENT_ID
        # )
        
        # Для разработки используем мок данные
        email = request.data.get('email', 'google_user@gmail.com')
        display_name = request.data.get('display_name', 'Google User')
        photo_url = request.data.get('photo_url', '')
        
        # Найти или создать пользователя
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': email,
                'display_name': display_name,
                'photo_url': photo_url,
                'provider': 'google',
                'email_verified': True,
            }
        )
        
        user.last_login_at = datetime.now()
        user.save()
        
        tokens = get_tokens_for_user(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'tokens': tokens,
        })
    
    except Exception as e:
        return Response(
            {'message': f'Ошибка Google аутентификации: {str(e)}'},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def yandex_login_view(request):
    """Вход через Yandex OAuth"""
    serializer = OAuthSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    access_token = serializer.validated_data.get('access_token')
    
    try:
        # Получение информации о пользователе Yandex
        response = http_requests.get(
            'https://login.yandex.ru/info',
            headers={'Authorization': f'OAuth {access_token}'}
        )
        
        if response.status_code != 200:
            return Response(
                {'message': 'Неверный Yandex токен'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        yandex_user = response.json()
        email = yandex_user.get('default_email') or f"{yandex_user['id']}@yandex.oauth"
        
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': yandex_user.get('login', email),
                'display_name': yandex_user.get('display_name', yandex_user.get('login', '')),
                'provider': 'yandex',
                'provider_id': yandex_user['id'],
                'email_verified': True,
            }
        )
        
        user.last_login_at = datetime.now()
        user.save()
        
        tokens = get_tokens_for_user(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'tokens': tokens,
        })
    except Exception as e:
        return Response(
            {'message': f'Ошибка Yandex аутентификации: {str(e)}'},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def vk_login_view(request):
    """Вход через VK OAuth"""
    serializer = OAuthSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    user_data = serializer.validated_data.get('user', {})
    
    try:
        vk_id = user_data.get('id')
        email = user_data.get('email') or f"vk_{vk_id}@vk.oauth"
        first_name = user_data.get('first_name', '')
        last_name = user_data.get('last_name', '')
        display_name = f"{first_name} {last_name}".strip() or f"VK User {vk_id}"
        
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': f"vk_{vk_id}",
                'display_name': display_name,
                'provider': 'vk',
                'provider_id': str(vk_id),
                'email_verified': bool(user_data.get('email')),
            }
        )
        
        user.last_login_at = datetime.now()
        user.save()
        
        tokens = get_tokens_for_user(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'tokens': tokens,
        })
    except Exception as e:
        return Response(
            {'message': f'Ошибка VK аутентификации: {str(e)}'},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """Выход из системы"""
    try:
        refresh_token = request.data.get('refresh')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        
        return Response({'message': 'Успешный выход'})
    except Exception as e:
        return Response(
            {'message': 'Неверный токен'},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET', 'PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def current_user_view(request):
    """Получение и обновление профиля текущего пользователя"""
    if request.method == 'GET':
        return Response(UserSerializer(request.user).data)
    
    elif request.method in ['PUT', 'PATCH']:
        partial = request.method == 'PATCH'
        serializer = UserSerializer(request.user, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password_view(request):
    """Смена пароля"""
    serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
    
    if serializer.is_valid():
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        return Response({'message': 'Пароль успешно изменен'})
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password_view(request):
    """Сброс пароля (отправка email)"""
    serializer = ResetPasswordSerializer(data=request.data)
    
    if serializer.is_valid():
        email = serializer.validated_data['email']
        
        try:
            user = User.objects.get(email=email)
            # Здесь должна быть логика отправки email
            # send_password_reset_email(user)
            
            return Response({'message': 'Инструкции отправлены на email'})
        except User.DoesNotExist:
            # Не раскрываем, существует ли пользователь
            return Response({'message': 'Инструкции отправлены на email'})
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_app_config(request):
    """
    Возвращает публичные настройки приложения.
    НЕ возвращайте секретные ключи (SECRET_KEY, API_KEY и т.д.)
    """
    config = {
        'debug': settings.DEBUG,
        'allowed_hosts': settings.ALLOWED_HOSTS,
        # добавьте только публичные настройки
        'google_oauth_client_id': settings.GOOGLE_OAUTH_CLIENT_ID if hasattr(settings, 'GOOGLE_OAUTH_CLIENT_ID') else None,
        'yandex_oauth_client_id': settings.YANDEX_OAUTH_CLIENT_ID if hasattr(settings, 'YANDEX_OAUTH_CLIENT_ID') else None,
        # НЕ добавляйте SECRET_KEY, YANDEX_GPT_API_KEY и другие секреты
    }
    return Response(config)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def speech_to_text_view(request):
    """
    Распознавание речи через Yandex SpeechKit
    Ожидает audio файл в request.FILES
    """
    try:
        audio_file = request.FILES.get('audio')
        if not audio_file:
            return Response(
                {'message': 'Аудио файл не найден', 'error': 'AUDIO_REQUIRED'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Читаем аудио данные
        audio_data = audio_file.read()
        
        # Распознаём речь
        text = YandexSpeechKit.recognize_audio(audio_data)
        
        return Response({
            'text': text,
            'success': True
        })
        
    except Exception as e:
        return Response(
            {'message': f'Ошибка распознавания речи: {str(e)}', 'error': 'RECOGNITION_FAILED'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def analyze_image_view(request):
    """
    Анализ изображения через Yandex Vision
    Ожидает image файл в request.FILES
    """
    try:
        image_file = request.FILES.get('image')
        if not image_file:
            return Response(
                {'message': 'Изображение не найдено', 'error': 'IMAGE_REQUIRED'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Читаем данные изображения
        image_data = image_file.read()
        
        # Анализируем и очищаем текст из изображения
        cleaned_text = YandexVision.analyze_workout_image(image_data)
        
        return Response({
            'text': cleaned_text,
            'success': True
        })
        
    except Exception as e:
        return Response(
            {'message': f'Ошибка анализа изображения: {str(e)}', 'error': 'ANALYSIS_FAILED'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def parse_workout_text_view(request):
    """
    Парсинг текста тренировки с помощью YandexGPT
    Принимает { "text": "жим лёжа 80кг 10 раз, присед 100кг 8 повторений" }
    Возвращает структурированные данные
    """
    try:
        text = request.data.get('text', '')
        
        if not text:
            return Response(
                {'message': 'Текст не может быть пустым', 'error': 'TEXT_REQUIRED'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Парсим тренировку через YandexGPT
        workout_data = YandexGPT.parse_workout_from_text(text)
        
        return Response({
            'workout': workout_data,
            'success': True
        })
        
    except Exception as e:
        return Response(
            {'message': f'Ошибка парсинга текста: {str(e)}', 'error': 'PARSING_FAILED'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ai_recommendations_view(request):
    """
    AI рекомендации на основе истории тренировок пользователя
    Принимает:
    - { "history": "текстовая история" } или
    - { "workouts": [...], "stats": {...}, "records": {...} }
    """
    try:
        # Поддерживаем оба формата: строка или структурированные данные
        user_history = request.data.get('history')
        
        if not user_history:
            # Пробуем получить структурированные данные
            user_history = {
                'workouts': request.data.get('workouts', []),
                'stats': request.data.get('stats', {}),
                'records': request.data.get('records', {})
            }
            
            # Проверяем, что хоть что-то передано
            if not user_history['workouts'] and not user_history['stats'] and not user_history['records']:
                return Response(
                    {'message': 'История тренировок не может быть пустой', 'error': 'HISTORY_REQUIRED'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Генерируем рекомендации
        recommendations = YandexGPT.generate_workout_recommendations(user_history)
        
        return Response({
            'recommendations': recommendations,
            'success': True
        })
        
    except Exception as e:
        return Response(
            {'message': f'Ошибка генерации рекомендаций: {str(e)}', 'error': 'GENERATION_FAILED'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )