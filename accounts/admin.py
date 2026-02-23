from django.contrib import admin

# Register your models here.
from .models import User, UserToken

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'first_name', 'last_name', 'is_staff', 'is_active')
    search_fields = ('email', 'first_name', 'last_name')
    list_filter = ('is_staff', 'is_active')
    ordering = ('email',)

@admin.register(UserToken)
class UserTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'token', 'created_at', 'expired_at')
    search_fields = ('user__email', 'token')
    list_filter = ('created_at', 'expired_at')
    ordering = ('-created_at',)