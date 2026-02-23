from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.conf import settings


class User(AbstractUser):
    email             = models.EmailField(unique=True)
    phone_number      = models.CharField(max_length=10, blank=True, null=True)
    is_email_verified = models.BooleanField(default=False)
    profile_image     = models.ImageField(upload_to='profiles/', null=True, blank=True)

    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email


class UserToken(models.Model):
    """Stores JWT refresh tokens in DB"""
    user       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tokens')
    token      = models.CharField(max_length=500, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expired_at = models.DateTimeField()

    def __str__(self):
        return f"Token for {self.user.email} (Expires: {self.expired_at})"


class EmailOTP(models.Model):
    """OTP for email verification and password reset — same as DRF project"""
    PURPOSE_CHOICES = (
        ('register', 'Register'),
        ('reset',    'Password Reset'),
    )

    user       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='otps')
    otp        = models.CharField(max_length=6)
    purpose    = models.CharField(max_length=10, choices=PURPOSE_CHOICES, default='register')
    created_at = models.DateTimeField(auto_now_add=True)
    is_used    = models.BooleanField(default=False)

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=15)

    def __str__(self):
        return f"OTP({self.purpose}) for {self.user.email}"