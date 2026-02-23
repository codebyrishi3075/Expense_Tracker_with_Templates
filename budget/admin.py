from django.contrib import admin
from .models import BudgetCategory, Budget


@admin.register(BudgetCategory)
class BudgetCategoryAdmin(admin.ModelAdmin):
    list_display  = ('id', 'name', 'user', 'created_at')
    search_fields = ('name', 'user__email')
    list_filter   = ('created_at',)


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display  = ('user', 'category', 'month', 'amount', 'created_at')
    list_filter   = ('month', 'category')
    search_fields = ('user__email',)
    ordering      = ('-month',)