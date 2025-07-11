from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .import views


urlpatterns = [
    # Authentication
    path('register/', views.UserRegistrationView.as_view(), name='user-register'),
    path('login/', views.UserLoginView.as_view(), name='user-login'),
    path('logout/', views.logout_view, name='user-logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    
    # User Profile
    path('profile/', views.UserProfileView.as_view(), name='user-profile'),
    path('change-password/', views.ChangePasswordView.as_view(), name='change-password'),
    
    # User Management
    path('users/', views.UserListView.as_view(), name='user-list'),
    path('users/online/', views.OnlineUsersView.as_view(), name='online-users'),
    path('users/search/', views.user_search, name='user-search'),
    path('users/status/', views.update_user_status, name='update-status'),
]

   