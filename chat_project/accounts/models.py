
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    """Custom User model extending Django's AbstractUser"""
    
    STATUS_CHOICES = [
        ('online', 'Online'),
        ('offline', 'Offline'),
        ('away', 'Away'),
        ('busy', 'Busy'),
    ]
    
    email = models.EmailField(unique=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    bio = models.TextField(max_length=500, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='offline')
    last_seen = models.DateTimeField(default=timezone.now)
    is_online = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    class Meta:
        db_table = 'users'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.username
    
    def update_last_seen(self):
        """Update the last seen timestamp"""
        self.last_seen = timezone.now()
        self.save(update_fields=['last_seen'])
    
    def set_online_status(self, is_online=True):
        """Set user online/offline status"""
        self.is_online = is_online
        self.status = 'online' if is_online else 'offline'
        if is_online:
            self.update_last_seen()
        self.save(update_fields=['is_online', 'status', 'last_seen'])


class UserProfile(models.Model):
    """Extended user profile information"""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone_number = models.CharField(max_length=20, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    location = models.CharField(max_length=100, blank=True)
    website = models.URLField(blank=True)
    notification_preferences = models.JSONField(default=dict)
    privacy_settings = models.JSONField(default=dict)
    
    class Meta:
        db_table = 'user_profiles'
    
    def __str__(self):
        return f"{self.user.username}'s Profile"