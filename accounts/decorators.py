from functools import wraps
from django.http import JsonResponse

from accounts.authentication import decode_access_token
from accounts.models import User


def jwt_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        token = request.COOKIES.get('access_token')
        print(f"DEBUG: Access token from cookie: {token}")

        if not token:
            print("DEBUG: No access token found in cookies")
            return JsonResponse({'error': 'Unauthorized'}, status=401)

        try:
            payload = decode_access_token(token)
            print(f"DEBUG: Token payload: {payload}")
            user = User.objects.get(id=payload['user_id'])
            request.user = user
        except Exception as e:
            print(f"DEBUG: Token decode error: {e}")
            return JsonResponse({'error': str(e)}, status=401)

        return view_func(request, *args, **kwargs)
    return wrapper