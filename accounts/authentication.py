import jwt
from datetime import datetime, timedelta, timezone
from accounts.models import User
import os


def create_access_token(user: User):
    payload = {
        'user_id': user.id,
        'username': user.username,
        'iat': datetime.now(timezone.utc),
        'exp': datetime.now(timezone.utc) + timedelta(seconds=2400),    # Access token expires in 40 minutes
    }
    secret = os.getenv('JWT_SECRET_KEY', 'default_secret')
    return jwt.encode(payload, secret, algorithm='HS256')

def decode_access_token(token):
    SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'default_secret')
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        print(payload)
        return payload
    except jwt.ExpiredSignatureError:
        raise Exception("Token expired")
    except jwt.InvalidTokenError:
        raise Exception("Invalid token")

def create_refresh_token(user: User):
    payload = {
        'user_id': user.id,
        'iat': datetime.now(timezone.utc),
        'exp': datetime.now(timezone.utc) + timedelta(days=7),
    }
    secret = os.getenv('JWT_REFRESH_SECRET_KEY', 'default_secret')
    return jwt.encode(payload, secret, algorithm='HS256')

def decode_refresh_token(token):
    try:
        secret = os.getenv('JWT_REFRESH_SECRET_KEY', 'default_secret')
        return jwt.decode(token, secret, algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        raise ValueError("Refresh token expired")
    except jwt.DecodeError:
        raise ValueError("Invalid refresh token")