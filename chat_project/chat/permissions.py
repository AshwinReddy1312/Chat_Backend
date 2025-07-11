
from rest_framework import permissions
from .models import ChatRoom, ChatRoomMembership


class IsRoomMember(permissions.BasePermission):
    """Permission to check if user is a member of the chat room"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        room_id = view.kwargs.get('room_id') or view.kwargs.get('pk')
        if room_id:
            try:
                room = ChatRoom.objects.get(id=room_id)
                return room.members.filter(id=request.user.id).exists()
            except ChatRoom.DoesNotExist:
                return False
        
        return True


class IsRoomAdminOrModerator(permissions.BasePermission):
    """Permission to check if user is admin or moderator of the chat room"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        room_id = view.kwargs.get('room_id') or view.kwargs.get('pk')
        if room_id:
            try:
                room = ChatRoom.objects.get(id=room_id)
                membership = room.memberships.get(user=request.user)
                return membership.role in ['admin', 'moderator']
            except (ChatRoom.DoesNotExist, ChatRoomMembership.DoesNotExist):
                return False
        
        return True


class IsMessageSender(permissions.BasePermission):
    """Permission to check if user is the sender of the message"""
    
    def has_object_permission(self, request, view, obj):
        return obj.sender == request.user


class IsDirectMessageParticipant(permissions.BasePermission):
    """Permission to check if user is participant in direct message conversation"""
    
    def has_object_permission(self, request, view, obj):
        return request.user in [obj.sender, obj.recipient]


class CanModifyMessage(permissions.BasePermission):
    """Permission to check if user can modify (edit/delete) a message"""
    
    def has_object_permission(self, request, view, obj):
        # User can modify their own messages
        if obj.sender == request.user:
            return True
        
        # Room admins/moderators can delete messages
        if hasattr(obj, 'room'):
            try:
                membership = obj.room.memberships.get(user=request.user)
                return membership.role in ['admin', 'moderator']
            except ChatRoomMembership.DoesNotExist:
                pass
        
        return False