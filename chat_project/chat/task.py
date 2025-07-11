
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import Message, DirectMessage
from accounts.models import User


@shared_task
def cleanup_old_messages():
    """Clean up old messages (older than 30 days)"""
    
    cutoff_date = timezone.now() - timedelta(days=30)
    
    # Delete old chat room messages
    old_messages = Message.objects.filter(
        created_at__lt=cutoff_date,
        is_deleted=True
    )
    deleted_count = old_messages.count()
    old_messages.delete()
    
    # Delete old direct messages
    old_direct_messages = DirectMessage.objects.filter(
        created_at__lt=cutoff_date,
        is_deleted=True
    )
    deleted_direct_count = old_direct_messages.count()
    old_direct_messages.delete()
    
    return f"Deleted {deleted_count} chat messages and {deleted_direct_count} direct messages"


@shared_task
def update_user_last_seen():
    """Update last seen for users who haven't been active"""
    
    # Mark users as offline if they haven't been seen for 5 minutes
    cutoff_time = timezone.now() - timedelta(minutes=5)
    
    offline_users = User.objects.filter(
        is_online=True,
        last_seen__lt=cutoff_time
    )
    
    updated_count = offline_users.update(
        is_online=False,
        status='offline'
    )
    
    return f"Updated {updated_count} users to offline status"


@shared_task
def send_notification_email(user_id, message_content, sender_name):
    """Send email notification for new messages"""
    
    try:
        from django.core.mail import send_mail
        from django.conf import settings
        
        user = User.objects.get(id=user_id)
        
        subject = f"New message from {sender_name}"
        message = f"You have a new message from {sender_name}:\n\n{message_content}"
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        
        return f"Email sent to {user.email}"
    
    except User.DoesNotExist:
        return "User not found"
    except Exception as e:
        return f"Failed to send email: {str(e)}"


@shared_task
def generate_chat_analytics():
    """Generate chat analytics data"""
    
    from django.db.models import Count, Q
    from datetime import datetime
    
    today = timezone.now().date()
    
    # Daily message count
    daily_messages = Message.objects.filter(
        created_at__date=today,
        is_deleted=False
    ).count()
    
    # Active users today
    active_users = User.objects.filter(
        Q(sent_messages__created_at__date=today) |
        Q(sent_direct_messages__created_at__date=today)
    ).distinct().count()
    
    # Most active chat rooms
    active_rooms = Message.objects.filter(
        created_at__date=today,
        is_deleted=False
    ).values('room__name').annotate(
        message_count=Count('id')
    ).order_by('-message_count')[:5]
    
    analytics_data = {
        'date': today.isoformat(),
        'daily_messages': daily_messages,
        'active_users': active_users,
        'active_rooms': list(active_rooms)
    }
    
    # Store analytics data (you can save to database or cache)
    # For now, just return the data
    return analytics_data