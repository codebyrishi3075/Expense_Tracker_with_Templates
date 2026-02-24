from django.contrib import admin
from .models import ContactMessage


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display  = ('full_name', 'email', 'subject', 'is_resolved', 'created_at')
    list_filter   = ('is_resolved', 'created_at')
    search_fields = ('email', 'subject', 'message')
    ordering      = ('-created_at',)
    # Allow admin to mark messages as resolved
    actions       = ['mark_resolved', 'mark_unresolved']

    def mark_resolved(self, request, queryset):
        queryset.update(is_resolved=True)
        self.message_user(request, "Selected messages marked as resolved.")
    mark_resolved.short_description = "Mark selected as Resolved"

    def mark_unresolved(self, request, queryset):
        queryset.update(is_resolved=False)
        self.message_user(request, "Selected messages marked as unresolved.")
    mark_unresolved.short_description = "Mark selected as Unresolved"