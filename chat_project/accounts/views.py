from rest_framework import status,generics,permissions
from rest_framework.decorators import api_view,permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny,IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import login
from django.db.models import Q
from .models import User
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, UserProfileSerializer,
    UserListSerializer, ChangePasswordSerializer
)
class UserRegistrationView(generics.CreateAPIView):
    # USER REGISTRATION END POINT
    
    queryset=User.objects.all()
    serializer_class=UserRegistrationSerializer
    permission_classes=[AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer=self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user=serializer.save()
        
        # Generate JWT Tokens
        refresh=RefreshToken.for_user(user)
        return Response({
            'user':UserProfileSerializer(user).data,
            'tokens':{
                'refresh':str(refresh),
                'access':str(refresh.acces_token),
            }
        },status=status.HTTP_201_CREATED)
        
        
        
class UserLoginView(generics.GenericAPIView):
    # USER LOGIN ENDPOINT
    
    serializer_class = UserLoginSerializer
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        login(request, user)
        
        # Update user online status
        user.set_online_status(True)
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserProfileSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    # User logout endpoint
    
    try:
        # Update user offline status
        request.user.set_online_status(False)
        
        # Blacklist the refresh token
        refresh_token = request.data.get('refresh_token')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        
        return Response({'message': 'Successfully logged out'})
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(generics.RetrieveUpdateAPIView):
    #USER PROFILE VIEW AND UPDATE ENDPOINT
    
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user


class UserListView(generics.ListAPIView):
        #LIST ALL USERS ENDPOINT
    
    serializer_class = UserListSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['status', 'is_online']
    search_fields = ['username', 'first_name', 'last_name', 'email']
    ordering_fields = ['username', 'last_seen', 'created_at']
    ordering = ['-last_seen']
    
    def get_queryset(self):
        return User.objects.exclude(id=self.request.user.id)


class OnlineUsersView(generics.ListAPIView):
    #ONLINE USERS ENDPOINT
    
    serializer_class = UserListSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return User.objects.filter(
            is_online=True
        ).exclude(id=self.request.user.id)


class ChangePasswordView(generics.UpdateAPIView):
    #CHNAGE PASSWORD ENDPOINT
    
    serializer_class = ChangePasswordSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user
    
    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = self.get_object()
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        return Response({'message': 'Password changed successfully'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_search(request):
    """Search users endpoint"""
    
    query = request.GET.get('q', '')
    if not query:
        return Response({'results': []})
    
    users = User.objects.filter(
        Q(username__icontains=query) |
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(email__icontains=query)
    ).exclude(id=request.user.id)[:10]
    
    serializer = UserListSerializer(users, many=True)
    return Response({'results': serializer.data})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_user_status(request):
    """Update user status endpoint"""
    
    status_value = request.data.get('status')
    if status_value not in ['online', 'offline', 'away', 'busy']:
        return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
    
    user = request.user
    user.status = status_value
    user.is_online = status_value == 'online'
    if status_value == 'online':
        user.update_last_seen()
    user.save()
    
    return Response({'message': 'Status updated successfully'})