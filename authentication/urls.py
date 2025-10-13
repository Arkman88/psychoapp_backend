from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

app_name = 'authentication'

urlpatterns = [
    # Email/Password Authentication
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    
    # OAuth Authentication
    path('google/', views.google_login_view, name='google_login'),
    path('yandex/', views.yandex_login_view, name='yandex_login'),
    path('vk/', views.vk_login_view, name='vk_login'),
    
    # User Management
    path('logout/', views.logout_view, name='logout'),
    path('me/', views.current_user_view, name='current_user'),
    path('change-password/', views.change_password_view, name='change_password'),
    path('reset-password/', views.reset_password_view, name='reset_password'),
    
    # Token Management
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Yandex AI Services
    path('speech-to-text/', views.speech_to_text_view, name='speech_to_text'),
    path('analyze-image/', views.analyze_image_view, name='analyze_image'),
    path('parse-workout/', views.parse_workout_text_view, name='parse_workout'),
    path('ai-recommendations/', views.ai_recommendations_view, name='ai_recommendations'),
    
    # Exercise Matching and Management
    path('exercises/match/', views.match_exercise_view, name='match_exercise'),
    path('exercises/quick-match/', views.quick_match_exercise_view, name='quick_match_exercise'),
    path('exercises/confirm/', views.confirm_exercise_view, name='confirm_exercise'),
    path('exercises/', views.list_exercises_view, name='list_exercises'),
    path('exercises/<uuid:exercise_id>/', views.exercise_detail_view, name='exercise_detail'),
    path('exercises/history/', views.user_exercise_history_view, name='exercise_history'),
    path('exercises/categories/', views.exercise_categories_view, name='exercise_categories'),
]
