
from rest_framework import serializers
from django.db.models import Q

from chat_project.accounts import models
from .models import ChatRoom, ChatRoomMembership, Message, MessageReaction, DirectMessage, Conversation
from accounts.serializers import UserListSerializer


class ChatRoomSerializer(serializers.ModelSerializer):
    """Serializer for chat rooms"""
    
    created_by = UserListSerializer(read_only=True)
    member_count = serializers.ReadOnlyField()
    last_message = serializers.SerializerMethodField()
    user_role = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatRoom
        fields = (
            'id', 'name', 'description', 'room_type', 'created_by',
            'member_count', 'last_message', 'user_role', 'is_active',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_by', 'created_at', 'updated_at')
    
    def get_last_message(self, obj):
        last_message = obj.get_last_message()
        if last_message:
            return {
                'id': last_message.id,
                'content': last_message.content,
                'sender': last_message.sender.username,
                'created_at': last_message.created_at,
                'message_type': last_message.message_type
            }
        return None
    
    def get_user_role(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            membership = obj.memberships.filter(user=request.user).first()
            return membership.role if membership else None
        return None
    
    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['created_by'] = request.user
        room = super().create(validated_data)
        
        # Add creator as admin
        room.add_member(request.user, added_by=request.user)
        membership = room.memberships.get(user=request.user)
        membership.role = 'admin'
        membership.save()
        
        return room


class ChatRoomMembershipSerializer(serializers.ModelSerializer):
    """Serializer for chat room memberships"""
    
    user = UserListSerializer(read_only=True)
    added_by = UserListSerializer(read_only=True)
    unread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatRoomMembership
        fields = (
            'id', 'user', 'role', 'added_by', 'joined_at',
            'last_read_at', 'is_muted', 'unread_count'
        )
        read_only_fields = ('id', 'joined_at')
    
    def get_unread_count(self, obj):
        return obj.room.messages.filter(
            created_at__gt=obj.last_read_at,
            is_deleted=False
        ).exclude(sender=obj.user).count()


class MessageReactionSerializer(serializers.ModelSerializer):
    """Serializer for message reactions"""
    
    user = UserListSerializer(read_only=True)
    
    class Meta:
        model = MessageReaction
        fields = ('id', 'user', 'reaction_type', 'created_at')
        read_only_fields = ('id', 'created_at')


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for messages"""
    
    sender = UserListSerializer(read_only=True)
    reply_to = serializers.SerializerMethodField()
    reactions = MessageReactionSerializer(many=True, read_only=True)
    reaction_counts = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = (
            'id', 'content', 'sender', 'message_type', 'file_attachment',
            'reply_to', 'reactions', 'reaction_counts', 'is_edited',
            'edited_at', 'is_deleted', 'created_at', 'updated_at'
        )
        read_only_fields = (
            'id', 'sender', 'is_edited', 'edited_at', 'is_deleted',
            'created_at', 'updated_at'
        )
    
    def get_reply_to(self, obj):
        if obj.reply_to:
            return {
                'id': obj.reply_to.id,
                'content': obj.reply_to.content,
                'sender': obj.reply_to.sender.username,
                'created_at': obj.reply_to.created_at
            }
        return None
    
    def get_reaction_counts(self, obj):
        reactions = obj.reactions.values('reaction_type').annotate(
            count=models.Count('reaction_type')
        )
        return {reaction['reaction_type']: reaction['count'] for reaction in reactions}
    
    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['sender'] = request.user
        return super().create(validated_data)


class DirectMessageSerializer(serializers.ModelSerializer):
    """Serializer for direct messages"""
    
    sender = UserListSerializer(read_only=True)
    recipient = UserListSerializer(read_only=True)
    
    class Meta:
        model = DirectMessage
        fields = (
            'id', 'sender', 'recipient', 'content', 'message_type',
            'file_attachment', 'is_read', 'read_at', 'is_edited',
            'edited_at', 'is_deleted', 'created_at', 'updated_at'
        )
        read_only_fields = (
            'id', 'sender', 'is_read', 'read_at', 'is_edited',
            'edited_at', 'is_deleted', 'created_at', 'updated_at'
        )
    
    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['sender'] = request.user
        return super().create(validated_data)


class ConversationSerializer(serializers.ModelSerializer):
    """Serializer for conversations"""
    
    participants = UserListSerializer(many=True, read_only=True)
    last_message = DirectMessageSerializer(read_only=True)
    other_participant = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = (
            'id', 'participants', 'last_message', 'other_participant',
            'unread_count', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    def get_other_participant(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            other_user = obj.get_other_participant(request.user)
            return UserListSerializer(other_user).data if other_user else None
        return None
    
    def get_unread_count(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.get_unread_count(request.user)
        return 0


class CreateDirectMessageSerializer(serializers.Serializer):
    """Serializer for creating direct messages"""
    
    recipient_id = serializers.IntegerField()
    content = serializers.CharField()
    message_type = serializers.ChoiceField(choices=DirectMessage.MESSAGE_TYPES, default='text')
    file_attachment = serializers.FileField(required=False)
    
    def validate_recipient_id(self, value):
        from accounts.models import User
        try:
            recipient = User.objects.get(id=value)
            if recipient == self.context['request'].user:
                raise serializers.ValidationError("Cannot send message to yourself")
            return recipient
        except User.DoesNotExist:
            raise serializers.ValidationError("Recipient not found")
    
    def create(self, validated_data):
        request = self.context['request']
        recipient = validated_data.pop('recipient_id')
        
        # Get or create conversation
        conversation = Conversation.get_or_create_conversation(request.user, recipient)
        
        # Create direct message
        message = DirectMessage.objects.create(
            sender=request.user,
            recipient=recipient,
            **validated_data
        )
        
        # Update conversation last message
        conversation.last_message = message
        conversation.save()
        
        return message