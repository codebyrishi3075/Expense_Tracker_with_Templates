from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpRequest, HttpResponse
from .models import User, UserToken
from .authentication import create_access_token, create_refresh_token
from django.contrib.auth import authenticate, login, logout
from django.utils import timezone
from datetime import timedelta

# Create your views here.


def register_view(request: HttpRequest) -> HttpResponse:
    if request.method == 'GET':
        return render(request, 'account/account.html')

    elif request.method == 'POST':
        print("POST DATA:", request.POST)
        user = None  # Safeguard for cleanup on exception

        try:
            first_name = request.POST.get("first_name", '').strip()
            last_name = request.POST.get("last_name", '').strip()
            email = request.POST.get("email", '').strip()
            phone_number = request.POST.get("phone_number", '').strip()
            password = request.POST.get("password", '')
            confirm_password = request.POST.get("confirm_password", '')

            # Validation
            if not all([first_name, last_name, email, password, confirm_password, phone_number]):
                return JsonResponse({'error': 'All fields are required!'}, status=400)

            # Validate phone number is exactly 10 digits
            if not phone_number.isdigit() or len(phone_number) != 10:
                return JsonResponse({'error': 'Phone number must be exactly 10 digits!'}, status=400)

            if User.objects.filter(email=email).exists():
                return JsonResponse({'error': 'Email already exists!'}, status=400)

            # Auto-generate username from email (part before @)
            username = email.split('@')[0]
            
            if User.objects.filter(username=username).exists():
                return JsonResponse({'error': 'Username already exists!'}, status=400)

            if password != confirm_password:
                return JsonResponse({'error': 'Passwords do not match!'}, status=400)

            if len(password) < 5:
                return JsonResponse({'error': 'Password must be at least 5 characters long'}, status=400)

            # Create the user (inactive)
            user = User.objects.create_user(
                first_name=first_name,
                last_name=last_name,
                username=username,
                email=email,
                phone_number=phone_number,
                password=password,
                is_active=True
            )

            print("User created successfully:", user.email)

            # Send verification email
            # -------------------------

            return JsonResponse({
                'success': True,
                'message': 'Check your email for the activation link!',
                'redirect_url': '/accounts/login/'
            }, status=200)

        except Exception as e:
            print("Error during registration:", str(e))
            if user:  # Delete only if user was created
                user.delete()
            return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({'error': 'Invalid HTTP method'}, status=405)



def login_view(request: HttpRequest) -> HttpResponse:
    if request.method == 'GET':
        return render(request, 'account/login.html')

    elif request.method == 'POST':
        try:
            email = request.POST.get("email")
            password = request.POST.get("password")

            user = authenticate(request, username=email, password=password)
            
            if user is None:
                return JsonResponse({'status': 'error', 'message': 'Invalid credentials'}, status=401)
            
            if not user.is_active:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Your email is not verified. Please check your inbox and activate your account.'
                }, status=403)

            login(request, user)

            access_token = create_access_token(user)
            refresh_token = create_refresh_token(user)

            # Determine redirect URL based on role
            redirect_url = '/accounts/dashboard/'

            # Save refresh token in DB
            UserToken.objects.create(
                user=user,
                token=refresh_token,
                expired_at=timezone.now() + timedelta(days=7)
            )

            response = JsonResponse({
                "status": "success",
                "redirect_url": redirect_url
            })

            # Set tokens in HTTP-only cookies
            response.set_cookie(
                key='access_token',
                value=access_token,
                httponly=True,
                secure=False,
                samesite='Lax',
                max_age=2400,
                path='/'
            )

            response.set_cookie(
                key='refresh_token',
                value=refresh_token,
                httponly=True,
                secure=False,
                samesite='Lax',
                max_age=7 * 24 * 60 * 60,
                path="/"
            )

            return response

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    return JsonResponse({'status': 'error', 'message': 'Invalid HTTP method'}, status=405)

from accounts.decorators import jwt_required

@jwt_required
def dashboard_view(request):
    context = {
        'user': request.user,
        'username': request.user.username,
    }
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        # AJAX request, return partial dashboard content only
        return render(request, 'accounts/dashboard.html', context)
    else:
        # When AJAX request is not detected, render 
        return render(request, 'accounts/dashboard.html', context)


def logout_view(request):
    try:
        user = request.user
        refresh_token = request.COOKIES.get('refresh_token')

        if refresh_token:
            UserToken.objects.filter(user=user, token=refresh_token).delete()

        logout(request)

        response = redirect('accounts:loginUser')

        # Delete cookies with the correct paths
        response.delete_cookie('access_token', path='/')     # Access token
        response.delete_cookie('refresh_token', path='/')    # Refresh token

        return response

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)