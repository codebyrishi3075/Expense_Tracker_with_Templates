from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import User, EmailOTP, UserToken


# ═══════════════════════════════════════════════════════════
# CUSTOM FORMS
# ═══════════════════════════════════════════════════════════

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model  = User
        fields = ('email', 'username')


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model  = User
        fields = '__all__'


# ═══════════════════════════════════════════════════════════
# USER ADMIN
# ═══════════════════════════════════════════════════════════

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form     = CustomUserChangeForm
    add_form = CustomUserCreationForm

    list_display = (
        'id', 'email', 'username', 'first_name', 'last_name',
        'phone_number', 'is_active', 'is_email_verified', 'is_staff', 'date_joined',
    )

    list_filter = ('is_active', 'is_staff', 'is_superuser', 'is_email_verified', 'date_joined')

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('username', 'first_name', 'last_name', 'phone_number', 'profile_image')}),
        ('Permissions', {'fields': ('is_active', 'is_email_verified', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields' : ('email', 'username', 'password1', 'password2', 'first_name', 'last_name'),
        }),
        ('Permissions', {'fields': ('is_active', 'is_email_verified', 'is_staff', 'is_superuser')}),
    )

    search_fields  = ('email', 'username', 'first_name', 'last_name')
    ordering       = ('-date_joined',)
    readonly_fields = ('date_joined', 'last_login')

    def save_model(self, request, obj, form, change):
        if not change and obj.password and not obj.password.startswith('pbkdf2_'):
            obj.set_password(obj.password)
        super().save_model(request, obj, form, change)


# ═══════════════════════════════════════════════════════════
# EMAIL OTP ADMIN
# ═══════════════════════════════════════════════════════════

@admin.register(EmailOTP)
class EmailOTPAdmin(admin.ModelAdmin):
    list_display    = ('id', 'user', 'otp', 'purpose', 'is_used', 'created_at', 'is_expired_status')
    list_filter     = ('purpose', 'is_used', 'created_at')
    search_fields   = ('user__email', 'otp')
    readonly_fields = ('created_at',)
    ordering        = ('-created_at',)

    def is_expired_status(self, obj):
        return obj.is_expired()
    is_expired_status.short_description = 'Expired?'
    is_expired_status.boolean           = True


# ═══════════════════════════════════════════════════════════
# USER TOKEN ADMIN
# ═══════════════════════════════════════════════════════════

@admin.register(UserToken)
class UserTokenAdmin(admin.ModelAdmin):
    list_display  = ('id', 'user', 'created_at', 'expired_at')
    search_fields = ('user__email',)
    ordering      = ('-created_at',)


# ═══════════════════════════════════════════════════════════
# ADMIN SITE BRANDING
# ═══════════════════════════════════════════════════════════

admin.site.site_header  = "Expense Tracker Admin"
admin.site.site_title   = "Expense Tracker Admin Portal"
admin.site.index_title  = "Welcome to Expense Tracker Administration"