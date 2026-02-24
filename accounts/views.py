import random
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

from .models import User, UserToken, EmailOTP
from .authentication import create_access_token, create_refresh_token
from .decorators import jwt_required


def generate_otp():
    return str(random.randint(100000, 999999))


def send_otp_email(user: User, purpose: str = 'register') -> None:
    EmailOTP.objects.filter(user=user, purpose=purpose).delete()
    otp = generate_otp()
    EmailOTP.objects.create(user=user, otp=otp, purpose=purpose)

    if purpose == 'register':
        subject = "Verify Your Email — Expense Tracker"
        message = (
            f"Hi {user.first_name or user.username},\n\n"
            f"Your email verification OTP is:\n\n"
            f"  {otp}\n\n"
            f"This OTP is valid for 15 minutes.\n"
            f"Do not share this with anyone.\n\n"
            f"— Expense Tracker Team"
        )
    else:
        subject = "Password Reset OTP — Expense Tracker"
        message = (
            f"Hi {user.first_name or user.username},\n\n"
            f"Your password reset OTP is:\n\n"
            f"  {otp}\n\n"
            f"This OTP is valid for 15 minutes.\n"
            f"If you did not request this, please ignore this email.\n\n"
            f"— Expense Tracker Team"
        )

    send_mail(subject, message, settings.EMAIL_HOST_USER, [user.email], fail_silently=False)


# ═══════════════════════════════════
# REGISTER
# ═══════════════════════════════════
def register_view(request: HttpRequest) -> HttpResponse:
    if request.method == 'GET':
        return render(request, 'accounts/register.html')

    elif request.method == 'POST':
        user = None
        try:
            first_name       = request.POST.get("first_name", '').strip()
            last_name        = request.POST.get("last_name", '').strip()
            email            = request.POST.get("email", '').strip()
            phone_number     = request.POST.get("phone_number", '').strip()
            password         = request.POST.get("password", '')
            confirm_password = request.POST.get("confirm_password", '')

            if not all([first_name, last_name, email, password, confirm_password, phone_number]):
                return JsonResponse({'error': 'All fields are required!'}, status=400)

            if not phone_number.isdigit() or len(phone_number) != 10:
                return JsonResponse({'error': 'Phone number must be exactly 10 digits!'}, status=400)

            if User.objects.filter(email=email).exists():
                return JsonResponse({'error': 'Email already registered!'}, status=400)

            username = email.split('@')[0]
            if User.objects.filter(username=username).exists():
                import uuid
                username = username + str(uuid.uuid4())[:4]

            if password != confirm_password:
                return JsonResponse({'error': 'Passwords do not match!'}, status=400)

            if len(password) < 5:
                return JsonResponse({'error': 'Password must be at least 5 characters.'}, status=400)

            user = User.objects.create_user(
                first_name        = first_name,
                last_name         = last_name,
                username          = username,
                email             = email,
                phone_number      = phone_number,
                password          = password,
                is_active         = False,
                is_email_verified = False,
            )

            send_otp_email(user, purpose='register')

            return JsonResponse({
                'success'      : True,
                'message'      : 'OTP sent to your email. Please verify to activate your account.',
                'redirect_url' : f'/accounts/verify-otp/?email={email}&purpose=register'
            }, status=201)

        except Exception as e:
            print("Registration error:", str(e))
            if user:
                user.delete()
            return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({'error': 'Invalid HTTP method'}, status=405)


# ═══════════════════════════════════
# VERIFY OTP
# ═══════════════════════════════════
def verify_otp_view(request: HttpRequest) -> HttpResponse:
    if request.method == 'GET':
        email   = request.GET.get('email', '')
        purpose = request.GET.get('purpose', 'register')
        return render(request, 'accounts/verify_email.html', {'email': email, 'purpose': purpose})

    elif request.method == 'POST':
        try:
            email   = request.POST.get('email', '').strip()
            otp     = request.POST.get('otp', '').strip()
            purpose = request.POST.get('purpose', 'register')

            if not email or not otp:
                return JsonResponse({'error': 'Email and OTP are required!'}, status=400)

            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return JsonResponse({'error': 'Invalid email.'}, status=404)

            otp_obj = EmailOTP.objects.filter(
                user    = user,
                otp     = otp,
                purpose = purpose,
                is_used = False
            ).last()

            if not otp_obj:
                return JsonResponse({'error': 'Invalid OTP. Please check and try again.'}, status=400)

            if otp_obj.is_expired():
                return JsonResponse({'error': 'OTP has expired. Please request a new one.'}, status=400)

            otp_obj.is_used = True
            otp_obj.save()

            if purpose == 'register':
                user.is_active         = True
                user.is_email_verified = True
                user.save()
                return JsonResponse({
                    'success'      : True,
                    'message'      : 'Email verified successfully! You can now login.',
                    'redirect_url' : '/accounts/login/'
                })
            else:
                return JsonResponse({
                    'success'      : True,
                    'message'      : 'OTP verified. Please set your new password.',
                    'redirect_url' : f'/accounts/password-reset/confirm/?email={email}'
                })

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({'error': 'Invalid HTTP method'}, status=405)


# ═══════════════════════════════════
# RESEND OTP
# ═══════════════════════════════════
def resend_otp_view(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        try:
            email   = request.POST.get('email', '').strip()
            purpose = request.POST.get('purpose', 'register')

            if not email:
                return JsonResponse({'error': 'Email is required!'}, status=400)

            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return JsonResponse({'error': 'User not found!'}, status=404)

            if purpose == 'register' and user.is_email_verified:
                return JsonResponse({'error': 'Account already verified. Please login.'}, status=400)

            send_otp_email(user, purpose=purpose)
            return JsonResponse({'success': True, 'message': 'New OTP sent to your email!'})

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({'error': 'Invalid HTTP method'}, status=405)


# ═══════════════════════════════════
# LOGIN
# ═══════════════════════════════════
def login_view(request: HttpRequest) -> HttpResponse:
    if request.method == 'GET':
        if request.COOKIES.get('access_token'):
            return redirect('dashboard:home')
        return render(request, 'accounts/login.html')

    elif request.method == 'POST':
        try:
            email    = request.POST.get("email", '').strip()
            password = request.POST.get("password", '')

            user = authenticate(request, username=email, password=password)

            if user is None:
                return JsonResponse({'status': 'error', 'message': 'Invalid email or password!'}, status=401)

            if not user.is_email_verified:
                return JsonResponse({
                    'status'       : 'error',
                    'message'      : 'Email not verified. Please check your inbox.',
                    'redirect_url' : f'/accounts/verify-otp/?email={email}&purpose=register'
                }, status=403)

            login(request, user)

            access_token  = create_access_token(user)
            refresh_token = create_refresh_token(user)

            UserToken.objects.create(
                user       = user,
                token      = refresh_token,
                expired_at = timezone.now() + timedelta(days=7)
            )

            # ✅ FIX: redirect to /dashboard/ not /accounts/dashboard/
            response = JsonResponse({"status": "success", "redirect_url": "/dashboard/"})
            response.set_cookie('access_token',  access_token,  httponly=True, secure=False, samesite='Lax', max_age=2400,       path='/')
            response.set_cookie('refresh_token', refresh_token, httponly=True, secure=False, samesite='Lax', max_age=7*24*60*60, path='/')
            return response

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    return JsonResponse({'status': 'error', 'message': 'Invalid HTTP method'}, status=405)


# ═══════════════════════════════════
# DASHBOARD — ✅ FIX: redirect to dashboard app
# ═══════════════════════════════════
@jwt_required
def dashboard_view(request):
    """
    /accounts/dashboard/ → redirect to /dashboard/
    Template accounts/dashboard.html exist nahi karta.
    dashboard app ka template use hota hai.
    """
    return redirect('dashboard:home')


# ═══════════════════════════════════
# PROFILE
# ═══════════════════════════════════
@jwt_required
def profile_view(request):
    user = request.user

    if request.method == 'POST':
        try:
            first_name   = request.POST.get('first_name', '').strip()
            last_name    = request.POST.get('last_name', '').strip()
            phone_number = request.POST.get('phone_number', '').strip()

            if not all([first_name, last_name]):
                return JsonResponse({'error': 'First and last name are required!'}, status=400)

            if phone_number and (not phone_number.isdigit() or len(phone_number) != 10):
                return JsonResponse({'error': 'Phone number must be exactly 10 digits!'}, status=400)

            user.first_name   = first_name
            user.last_name    = last_name
            user.phone_number = phone_number
            user.save()

            return JsonResponse({'success': True, 'message': 'Profile updated successfully!'})

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    return render(request, 'accounts/profile.html', {'user': user})


# ═══════════════════════════════════
# UPLOAD PROFILE PICTURE
# ═══════════════════════════════════
@jwt_required
def upload_avatar_view(request):
    if request.method == 'POST':
        try:
            file = request.FILES.get('profile_image')

            if not file:
                return JsonResponse({'error': 'No file provided.'}, status=400)

            allowed_types = ['image/jpeg', 'image/png', 'image/jpg', 'image/webp']
            if file.content_type not in allowed_types:
                return JsonResponse({'error': 'Only JPG, PNG, WEBP images allowed.'}, status=400)

            user = request.user
            user.profile_image = file
            user.save()

            return JsonResponse({
                'success'           : True,
                'message'           : 'Profile picture updated!',
                'profile_image_url' : request.build_absolute_uri(user.profile_image.url)
            })

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({'error': 'Invalid HTTP method'}, status=405)


# ═══════════════════════════════════
# PASSWORD RESET — Step 1: Request OTP
# ═══════════════════════════════════
def password_reset_request_view(request: HttpRequest) -> HttpResponse:
    if request.method == 'GET':
        return render(request, 'accounts/password_reset_request.html')

    elif request.method == 'POST':
        try:
            email = request.POST.get('email', '').strip()

            if not email:
                return JsonResponse({'error': 'Email is required!'}, status=400)

            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return JsonResponse({'error': 'No account found with this email.'}, status=404)

            send_otp_email(user, purpose='reset')

            return JsonResponse({
                'success'      : True,
                'message'      : 'Password reset OTP sent to your email!',
                'redirect_url' : f'/accounts/verify-otp/?email={email}&purpose=reset'
            })

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({'error': 'Invalid HTTP method'}, status=405)


# ═══════════════════════════════════
# PASSWORD RESET — Step 2: Confirm
# ═══════════════════════════════════
def password_reset_confirm_view(request: HttpRequest) -> HttpResponse:
    if request.method == 'GET':
        email = request.GET.get('email', '')
        return render(request, 'accounts/password_reset_confirm.html', {'email': email})

    elif request.method == 'POST':
        try:
            email        = request.POST.get('email', '').strip()
            new_password = request.POST.get('new_password', '')
            confirm_pass = request.POST.get('confirm_password', '')

            if not email or not new_password:
                return JsonResponse({'error': 'Email and new password are required!'}, status=400)

            if new_password != confirm_pass:
                return JsonResponse({'error': 'Passwords do not match!'}, status=400)

            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return JsonResponse({'error': 'Invalid email.'}, status=404)

            try:
                validate_password(new_password, user)
            except ValidationError as e:
                return JsonResponse({'error': list(e.messages)}, status=400)

            user.set_password(new_password)
            user.save()

            return JsonResponse({
                'success'      : True,
                'message'      : 'Password reset successful! Please login.',
                'redirect_url' : '/accounts/login/'
            })

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({'error': 'Invalid HTTP method'}, status=405)


# ═══════════════════════════════════
# LOGOUT
# ═══════════════════════════════════
def logout_view(request):
    try:
        refresh_token = request.COOKIES.get('refresh_token')
        if refresh_token:
            UserToken.objects.filter(user=request.user, token=refresh_token).delete()

        logout(request)

        response = redirect('accounts:loginUser')
        response.delete_cookie('access_token',  path='/')
        response.delete_cookie('refresh_token', path='/')
        return response

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)