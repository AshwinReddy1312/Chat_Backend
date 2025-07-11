
from django.db import models
from django.conf import settings
from django.utils import timezone


class ChatRoom(models.Model):
    """Chat room model for group conversations"""
    
    ROOM_TYPES = [
        ('private', 'Private'),
        ('group', 'Group'),
        ('public', 'Public'),
    ]
    
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    room_type = models.CharField(max_length=10, choices=ROOM_TYPES, default='group')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_rooms')
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, through='ChatRoomMembership', related_name='chat_rooms')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'chat_rooms'
        ordering = ['-updated_at']
    
    def __str__(self):
        return self.name
    
    @property
    def member_count(self):
        return self.members.count()
    
    def add_member(self, user, added_by=None):
        """Add a member to the chat room"""
        membership, created = ChatRoomMembership.objects.get_or_create(
            room=self,
            user=user,
            defaults={'added_by': added_by}
        )
        return membership, created
    
    def remove_member(self, user):
        """Remove a member from the chat room"""
        ChatRoomMembership.objects.filter(room=self, user=user).delete()
    
    def get_last_message(self):
        """Get the last message in the room"""
        return self.messages.first()


class ChatRoomMembership(models.Model):
    """Membership model for chat room members"""
    
    ROLES = [
        ('admin', 'Admin'),
        ('moderator', 'Moderator'),
        ('member', 'Member'),
    ]
    
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='room_memberships')
    role = models.CharField(max_length=10, choices=ROLES, default='member')
    added_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='added_members')
    joined_at = models.DateTimeField(auto_now_add=True)
    last_read_at = models.DateTimeField(default=timezone.now)
    is_muted = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'chat_room_memberships'
        unique_together = ['room', 'user']
    
    def __str__(self):
        return f"{self.user.username} in {self.room.name}"
    
    def mark_as_read(self):
        """Mark messages as read up to current time"""
        self.last_read_at = timezone.now()
        self.save(update_fields=['last_read_at'])


class Message(models.Model):
    """Message model for chat messages"""
    
    MESSAGE_TYPES = [
        ('text', 'Text'),
        ('image', 'Image'),
        ('file', 'File'),
        ('system', 'System'),
    ]
    
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField()
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES, default='text')
    file_attachment = models.FileField(upload_to='chat_files/', null=True, blank=True)
    reply_to = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    is_edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'messages'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.sender.username}: {self.content[:50]}"
    
    def edit_message(self, new_content):
        """Edit message content"""
        self.content = new_content
        self.is_edited = True
        self.edited_at = timezone.now()
        self.save()
    
    def delete_message(self):
        """Soft delete message"""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.content = "This message was deleted"
        self.save()
    
    @property
    def is_reply(self):
        return self.reply_to is not None


class MessageReaction(models.Model):
    """Message reaction model"""
    
    REACTION_TYPES = [
        ('like', '👍'),
        ('love', '❤️'),
        ('laugh', '😂'),
        ('wow', '😮'),
        ('sad', '😢'),
        ('angry', '😠'),
    ]
    
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='message_reactions')
    reaction_type = models.CharField(max_length=10, choices=REACTION_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'message_reactions'
        unique_together = ['message', 'user', 'reaction_type']
    
    def __str__(self):
        return f"{self.user.username} {self.get_reaction_type_display()} on message {self.message.id}"


class DirectMessage(models.Model):
    """Direct message model for private conversations"""
    
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_direct_messages')
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_direct_messages')
    content = models.TextField()
    message_type = models.CharField(max_length=10, choices=Message.MESSAGE_TYPES, default='text')
    file_attachment = models.FileField(upload_to='direct_message_files/', null=True, blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    is_edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'direct_messages'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.sender.username} to {self.recipient.username}: {self.content[:50]}"
    
    def mark_as_read(self):
        """Mark message as read"""
        self.is_read = True
        self.read_at = timezone.now()
        self.save(update_fields=['is_read', 'read_at'])
    
    def edit_message(self, new_content):
        """Edit message content"""
        self.content = new_content
        self.is_edited = True
        self.edited_at = timezone.now()
        self.save()
    
    def delete_message(self):
        """Soft delete message"""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.content = "This message was deleted"
        self.save()


class Conversation(models.Model):
    """Conversation model to track direct message threads"""
    
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='conversations')
    last_message = models.ForeignKey(DirectMessage, on_delete=models.SET_NULL, null=True, blank=True, related_name='conversation_last')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'conversations'
        ordering = ['-updated_at']
    
    def __str__(self):
        participants = ", ".join([user.username for user in self.participants.all()])
        return f"Conversation: {participants}"
    
    @classmethod
    def get_or_create_conversation(cls, user1, user2):
        """Get or create conversation between two users"""
        conversation = cls.objects.filter(
            participants=user1
        ).filter(
            participants=user2
        ).filter(
            participants__count=2
        ).first()
        
        if not conversation:
            conversation = cls.objects.create()
            conversation.participants.add(user1, user2)
        
        return conversation
    
    def get_other_participant(self, user):
        """Get the other participant in the conversation"""
        return self.participants.exclude(id=user.id).first()
    
    def get_unread_count(self, user):
        """Get unread message count for a user"""
        return DirectMessage.objects.filter(
            sender__in=self.participants.exclude(id=user.id),
            recipient=user,
            is_read=False,
            is_deleted=False
        ).count()