from functools import wraps
from django.shortcuts import redirect
from django.contrib.auth import get_user_model
from .authentication import decode_access_token, decode_refresh_token, create_access_token
from .models import UserToken
from django.utils import timezone

User = get_user_model()


def jwt_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        access_token = request.COOKIES.get('access_token')
        refresh_token = request.COOKIES.get('refresh_token')

        user = None

        # Step 1: Try access token first
        if access_token:
            try:
                payload = decode_access_token(access_token)
                user = User.objects.get(id=payload['user_id'])
            except Exception:
                user = None

        # Step 2: If access token expired/invalid, try refresh token
        if user is None and refresh_token:
            try:
                payload = decode_refresh_token(refresh_token)

                # Check refresh token is valid in DB and not expired
                db_token = UserToken.objects.filter(
                    token=refresh_token,
                    expired_at__gt=timezone.now()
                ).first()

                if db_token:
                    user = User.objects.get(id=payload['user_id'])
                    # Issue new access token
                    new_access_token = create_access_token(user)

                    request.user = user
                    response = view_func(request, *args, **kwargs)

                    # Set new access token in cookie
                    response.set_cookie(
                        key='access_token',
                        value=new_access_token,
                        httponly=True,
                        secure=False,
                        samesite='Lax',
                        max_age=2400,
                        path='/'
                    )
                    return response

            except Exception:
                pass

        # Step 3: No valid token found → redirect to login
        if user is None:
            return redirect('accounts:loginUser')

        request.user = user
        return view_func(request, *args, **kwargs)

    return wrapper