from django.contrib import admin
from .models import UserSettings


@admin.register(UserSettings)
class UserSettingsAdmin(admin.ModelAdmin):
    list_display  = ('user', 'currency', 'monthly_budget_limit', 'created_at', 'updated_at')
    search_fields = ('user__email',)
    ordering      = ('-created_at',)