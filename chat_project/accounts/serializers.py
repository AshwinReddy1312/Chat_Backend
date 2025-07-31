
from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import User,   UserProfile


class UserRegistrationSerializer(serializers.ModelSerializer):
    # SERIALIZER FOR USER REGISTRATION
    
    password=serializers.CharField(write_only=True,validators=[validate_password])
    password_confirm=serializers.CharField(write_only=True)
    
    class Meta:
        model=User
        fields=('id', 'username', 'email', 'password', 'password_confirm', 'first_name', 'last_name')
        
    def validate(self,attrs):
        if attrs['password'] != attrs['password-confirm']:
            raise serializers.ValidationError("Passwords Don't Match")
        return attrs
    
    def create(self,validated_data):
        validated_data.pop('password_confirm')
        user=User.objects.create_user(**validated_data)
        UserProfile.objects.create(user=user)
        return user
    
class UserLoginSerializer(serializers.Serializer):
    # SERIALIZER FOR LOGIN
    
    email=serializers.EmailField()
    password=serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        email=attrs.get('email')
        password=attrs.get('password')
        
        if email and password:
            user = authenticate(username=email, password=password)
            if not user:
                raise serializers.ValidationError('Invalid credentials')
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled')
            attrs['user'] = user
        else:
            raise serializers.ValidationError('Must include email and password')
        

    
class UserProfileSerializer(serializers.ModelSerializer):
    # SERIALIZER FOR USER PROFILE
    
    phone_number = serializers.CharField(source='profile.phone_number', allow_blank=True)
    date_of_birth = serializers.DateField(source='profile.date_of_birth', allow_null=True)
    location = serializers.CharField(source='profile.location', allow_blank=True)
    website = serializers.URLField(source='profile.website', allow_blank=True)
    
    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'first_name', 'last_name', 
            'avatar', 'bio', 'status', 'last_seen', 'is_online',
            'phone_number', 'date_of_birth', 'location', 'website',
            'created_at'
        )
        read_only_fields = ('id', 'last_seen', 'created_at')
    
    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', {})
        
        # Update user fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update profile fields
        if profile_data:
            profile = instance.profile
            for attr, value in profile_data.items():
                setattr(profile, attr, value)
            profile.save()
        
        return instance


class UserListSerializer(serializers.ModelSerializer):
    """Serializer for user list (minimal data)"""
    
    class Meta:
        model = User
        fields = ('id', 'username', 'avatar', 'status', 'is_online', 'last_seen')


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing password"""
    
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("New passwords don't match")
        return attrs
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect")
        return value
        
   
