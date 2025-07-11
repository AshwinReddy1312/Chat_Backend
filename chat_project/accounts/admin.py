
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserProfile


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    # CUSTOM USER ADMIN
    
    list_display = ('username', 'email', 'first_name', 'last_name', 'status', 'is_online', 'last_seen', 'is_staff')
    list_filter = ('status', 'is_online', 'is_staff', 'is_superuser', 'is_active', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': ('avatar', 'bio', 'status', 'last_seen', 'is_online')
        }),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Additional Info', {
            'fields': ('email', 'avatar', 'bio')
        }),
    )


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    #USER PROFILE ADMIN
    
    list_display = ('user', 'phone_number', 'location', 'date_of_birth')
    search_fields = ('user__username', 'user__email', 'phone_number', 'location')
    list_filter = ('date_of_birth',)