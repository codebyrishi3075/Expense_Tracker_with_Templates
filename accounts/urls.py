from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Auth
    path('register/',                    views.register_view,                  name='registerUser'),
    path('login/',                       views.login_view,                     name='loginUser'),
    path('logout/',                      views.logout_view,                    name='logoutUser'),

    # OTP Verification (register + reset both use same template)
    path('verify-otp/',                  views.verify_otp_view,                name='verifyOTP'),
    path('resend-otp/',                  views.resend_otp_view,                name='resendOTP'),

    # Dashboard & Profile
    path('dashboard/',                   views.dashboard_view,                 name='dashboard'),
    path('profile/',                     views.profile_view,                   name='profile'),
    path('profile/avatar/',              views.upload_avatar_view,             name='uploadAvatar'),

    # Password Reset
    path('password-reset/request/',      views.password_reset_request_view,   name='passwordResetRequest'),
    path('password-reset/confirm/',      views.password_reset_confirm_view,   name='passwordResetConfirm'),
]