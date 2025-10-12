from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import UserSession

User = get_user_model()


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Админка для кастомной модели пользователя"""
    list_display = ('email', 'display_name', 'provider', 'email_verified', 'is_staff', 'created_at')
    list_filter = ('provider', 'email_verified', 'is_staff', 'is_superuser', 'is_active', 'created_at')
    search_fields = ('email', 'display_name', 'username')
    ordering = ('-created_at',)
    
    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        ('Личная информация', {'fields': ('display_name', 'photo_url', 'phone_number')}),
        ('OAuth', {'fields': ('provider', 'provider_id', 'email_verified')}),
        ('Метаданные', {'fields': ('age', 'gender', 'country', 'language', 'timezone')}),
        ('Настройки', {'fields': ('notifications_enabled', 'biometric_enabled', 'theme')}),
        ('Права доступа', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Важные даты', {'fields': ('last_login', 'last_login_at', 'created_at', 'updated_at')}),
    )
    
    readonly_fields = ('created_at', 'updated_at', 'last_login_at')
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'display_name', 'password1', 'password2'),
        }),
    )


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    """Админка для сессий пользователей"""
    list_display = ('user', 'device_type', 'device_name', 'is_active', 'created_at', 'last_activity')
    list_filter = ('device_type', 'is_active', 'created_at')
    search_fields = ('user__email', 'device_id', 'device_name', 'ip_address')
    readonly_fields = ('created_at', 'last_activity')
    ordering = ('-last_activity',)
