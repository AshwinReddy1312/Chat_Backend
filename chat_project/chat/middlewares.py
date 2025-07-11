
from django.utils import timezone
from django.contrib.auth.models import AnonymousUser
from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.contrib.auth import get_user_model
from urllib.parse import parse_qs
import jwt
from django.conf import settings

User = get_user_model()


@database_sync_to_async
def get_user_from_token(token_string):
    """Get user from JWT token"""
    try:
        # Validate token
        UntypedToken(token_string)
        
        # Decode token to get user ID
        decoded_token = jwt.decode(
            token_string,
            settings.SECRET_KEY,
            algorithms=["HS256"]
        )
        
        user_id = decoded_token.get('user_id')
        if user_id:
            user = User.objects.get(id=user_id)
            # Update last seen
            user.update_last_seen()
            return user
    
    except (InvalidToken, TokenError, User.DoesNotExist, jwt.DecodeError):
        pass
    
    return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """JWT Authentication middleware for WebSocket connections"""
    
    async def __call__(self, scope, receive, send):
        # Get token from query string
        query_string = scope.get('query_string', b'').decode()
        query_params = parse_qs(query_string)
        token = query_params.get('token', [None])[0]
        
        if token:
            scope['user'] = await get_user_from_token(token)
        else:
            scope['user'] = AnonymousUser()
        
        return await super().__call__(scope, receive, send)


class UpdateLastSeenMiddleware:
    """Middleware to update user's last seen timestamp"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Update last seen for authenticated users
        if request.user.is_authenticated:
            request.user.update_last_seen()
        
        return response