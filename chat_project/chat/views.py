
from datetime import timezone
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db.models import Q, Prefetch
from django.shortcuts import get_object_or_404
from .models import ChatRoom, ChatRoomMembership, Message, MessageReaction, DirectMessage, Conversation
from .serializers import (
    ChatRoomSerializer, ChatRoomMembershipSerializer, MessageSerializer,
    MessageReactionSerializer, DirectMessageSerializer, ConversationSerializer,
    CreateDirectMessageSerializer
)
from accounts.models import User


# Chat Room Views
class ChatRoomListCreateView(generics.ListCreateAPIView):
    """List and create chat rooms"""
    
    serializer_class = ChatRoomSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        return ChatRoom.objects.filter(
            members=user,
            is_active=True
        ).prefetch_related('members', 'created_by')


class ChatRoomDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, and delete chat rooms"""
    
    serializer_class = ChatRoomSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return ChatRoom.objects.filter(members=self.request.user)
    
    def perform_destroy(self, instance):
        # Soft delete - mark as inactive
        instance.is_active = False
        instance.save()


class ChatRoomMembersView(generics.ListAPIView):
    """List chat room members"""
    
    serializer_class = ChatRoomMembershipSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        room_id = self.kwargs['room_id']
        room = get_object_or_404(ChatRoom, id=room_id, members=self.request.user)
        return room.memberships.select_related('user', 'added_by')


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def add_room_member(request, room_id):
    """Add member to chat room"""
    
    room = get_object_or_404(ChatRoom, id=room_id, members=request.user)
    user_id = request.data.get('user_id')
    
    try:
        user_to_add = User.objects.get(id=user_id)
        membership, created = room.add_member(user_to_add, added_by=request.user)
        
        if created:
            serializer = ChatRoomMembershipSerializer(membership)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response({'error': 'User is already a member'}, status=status.HTTP_400_BAD_REQUEST)
    
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def remove_room_member(request, room_id, user_id):
    """Remove member from chat room"""
    
    room = get_object_or_404(ChatRoom, id=room_id, members=request.user)
    
    # Check if user has permission to remove members
    user_membership = room.memberships.get(user=request.user)
    if user_membership.role not in ['admin', 'moderator']:
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        user_to_remove = User.objects.get(id=user_id)
        room.remove_member(user_to_remove)
        return Response({'message': 'Member removed successfully'})
    
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)


# Message Views
class MessageListCreateView(generics.ListCreateAPIView):
    """List and create messages in a chat room"""
    
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        room_id = self.kwargs['room_id']
        room = get_object_or_404(ChatRoom, id=room_id, members=self.request.user)
        
        return Message.objects.filter(
            room=room,
            is_deleted=False
        ).select_related('sender', 'reply_to__sender').prefetch_related('reactions__user')
    
    def perform_create(self, serializer):
        room_id = self.kwargs['room_id']
        room = get_object_or_404(ChatRoom, id=room_id, members=self.request.user)
        serializer.save(room=room)


class MessageDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, and delete messages"""
    
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Message.objects.filter(sender=self.request.user, is_deleted=False)
    
    def perform_update(self, serializer):
        instance = serializer.save()
        instance.edit_message(serializer.validated_data['content'])
    
    def perform_destroy(self, instance):
        instance.delete_message()


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def add_message_reaction(request, message_id):
    """Add reaction to a message"""
    
    message = get_object_or_404(Message, id=message_id, room__members=request.user)
    reaction_type = request.data.get('reaction_type')
    
    if reaction_type not in dict(MessageReaction.REACTION_TYPES):
        return Response({'error': 'Invalid reaction type'}, status=status.HTTP_400_BAD_REQUEST)
    
    reaction, created = MessageReaction.objects.get_or_create(
        message=message,
        user=request.user,
        reaction_type=reaction_type
    )
    
    if created:
        serializer = MessageReactionSerializer(reaction)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    else:
        return Response({'error': 'Reaction already exists'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def remove_message_reaction(request, message_id, reaction_type):
    """Remove reaction from a message"""
    
    message = get_object_or_404(Message, id=message_id, room__members=request.user)
    
    try:
        reaction = MessageReaction.objects.get(
            message=message,
            user=request.user,
            reaction_type=reaction_type
        )
        reaction.delete()
        return Response({'message': 'Reaction removed successfully'})
    
    except MessageReaction.DoesNotExist:
        return Response({'error': 'Reaction not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def mark_messages_as_read(request, room_id):
    """Mark messages as read in a chat room"""
    
    room = get_object_or_404(ChatRoom, id=room_id, members=request.user)
    membership = room.memberships.get(user=request.user)
    membership.mark_as_read()
    
    return Response({'message': 'Messages marked as read'})


# Direct Message Views
class ConversationListView(generics.ListAPIView):
    """List user conversations"""
    
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Conversation.objects.filter(
            participants=self.request.user
        ).prefetch_related('participants', 'last_message__sender', 'last_message__recipient')


class DirectMessageListCreateView(generics.ListCreateAPIView):
    """List and create direct messages"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreateDirectMessageSerializer
        return DirectMessageSerializer
    
    def get_queryset(self):
        conversation_id = self.kwargs['conversation_id']
        conversation = get_object_or_404(Conversation, id=conversation_id, participants=self.request.user)
        
        other_participant = conversation.get_other_participant(self.request.user)
        
        return DirectMessage.objects.filter(
            Q(sender=self.request.user, recipient=other_participant) |
            Q(sender=other_participant, recipient=self.request.user),
            is_deleted=False
        ).select_related('sender', 'recipient')


class DirectMessageDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, and delete direct messages"""
    
    serializer_class = DirectMessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return DirectMessage.objects.filter(
            Q(sender=self.request.user) | Q(recipient=self.request.user),
            is_deleted=False
        )
    
    def perform_update(self, serializer):
        instance = serializer.save()
        if instance.sender == self.request.user:
            instance.edit_message(serializer.validated_data['content'])
    
    def perform_destroy(self, instance):
        if instance.sender == self.request.user:
            instance.delete_message()


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def mark_direct_messages_as_read(request, conversation_id):
    """Mark direct messages as read in a conversation"""
    
    conversation = get_object_or_404(Conversation, id=conversation_id, participants=request.user)
    other_participant = conversation.get_other_participant(request.user)
    
    DirectMessage.objects.filter(
        sender=other_participant,
        recipient=request.user,
        is_read=False
    ).update(is_read=True, read_at=timezone.now())
    
    return Response({'message': 'Messages marked as read'})


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_conversation(request):
    """Create or get conversation with another user"""
    
    other_user_id = request.data.get('user_id')
    
    try:
        other_user = User.objects.get(id=other_user_id)
        if other_user == request.user:
            return Response({'error': 'Cannot create conversation with yourself'}, status=status.HTTP_400_BAD_REQUEST)
        
        conversation = Conversation.get_or_create_conversation(request.user, other_user)
        serializer = ConversationSerializer(conversation, context={'request': request})
        
        return Response(serializer.data)
    
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)


# Search Views
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def search_messages(request):
    """Search messages in user's chat rooms"""
    
    query = request.GET.get('q', '')
    room_id = request.GET.get('room_id')
    
    if not query:
        return Response({'results': []})
    
    messages_qs = Message.objects.filter(
        room__members=request.user,
        content__icontains=query,
        is_deleted=False
    ).select_related('sender', 'room')
    
    if room_id:
        messages_qs = messages_qs.filter(room_id=room_id)
    
    messages = messages_qs[:20]
    serializer = MessageSerializer(messages, many=True)
    
    return Response({'results': serializer.data})


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def search_rooms(request):
    """Search chat rooms"""
    
    query = request.GET.get('q', '')
    
    if not query:
        return Response({'results': []})
    
    rooms = ChatRoom.objects.filter(
        Q(name__icontains=query) | Q(description__icontains=query),
        is_active=True
    ).exclude(room_type='private')[:10]
    
    serializer = ChatRoomSerializer(rooms, many=True, context={'request': request})
    
    return Response({'results': serializer.data})