
from datetime import timezone
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import ChatRoom, Message, DirectMessage, Conversation
from .serializers import MessageSerializer, DirectMessageSerializer

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for chat room messages"""
    
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'
        self.user = self.scope['user']
        
        # Check if user is member of the room
        if not await self.is_room_member():
            await self.close()
            return
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Update user online status
        await self.update_user_status(True)
    
    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        
        # Update user offline status
        await self.update_user_status(False)
    
    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'chat_message':
                await self.handle_chat_message(data)
            elif message_type == 'typing':
                await self.handle_typing(data)
            elif message_type == 'message_reaction':
                await self.handle_message_reaction(data)
            elif message_type == 'message_edit':
                await self.handle_message_edit(data)
            elif message_type == 'message_delete':
                await self.handle_message_delete(data)
        
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'error': 'Invalid JSON'
            }))
    
    async def handle_chat_message(self, data):
        content = data.get('content', '').strip()
        reply_to_id = data.get('reply_to')
        
        if not content:
            return
        
        # Save message to database
        message = await self.save_message(content, reply_to_id)
        
        if message:
            # Serialize message
            message_data = await self.serialize_message(message)
            
            # Send message to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message_data
                }
            )
    
    async def handle_typing(self, data):
        is_typing = data.get('is_typing', False)
        
        # Send typing indicator to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator',
                'user': self.user.username,
                'is_typing': is_typing
            }
        )
    
    async def handle_message_reaction(self, data):
        message_id = data.get('message_id')
        reaction_type = data.get('reaction_type')
        action = data.get('action', 'add')  # 'add' or 'remove'
        
        if action == 'add':
            reaction = await self.add_message_reaction(message_id, reaction_type)
        else:
            await self.remove_message_reaction(message_id, reaction_type)
            reaction = None
        
        # Send reaction update to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'message_reaction',
                'message_id': message_id,
                'reaction_type': reaction_type,
                'action': action,
                'user': self.user.username
            }
        )
    
    async def handle_message_edit(self, data):
        message_id = data.get('message_id')
        new_content = data.get('content', '').strip()
        
        if not new_content:
            return
        
        message = await self.edit_message(message_id, new_content)
        
        if message:
            message_data = await self.serialize_message(message)
            
            # Send edited message to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'message_edited',
                    'message': message_data
                }
            )
    
    async def handle_message_delete(self, data):
        message_id = data.get('message_id')
        
        message = await self.delete_message(message_id)
        
        if message:
            # Send delete notification to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'message_deleted',
                    'message_id': message_id
                }
            )
    
    # Receive message from room group
    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message']
        }))
    
    async def typing_indicator(self, event):
        # Don't send typing indicator to the sender
        if event['user'] != self.user.username:
            await self.send(text_data=json.dumps({
                'type': 'typing_indicator',
                'user': event['user'],
                'is_typing': event['is_typing']
            }))
    
    async def message_reaction(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message_reaction',
            'message_id': event['message_id'],
            'reaction_type': event['reaction_type'],
            'action': event['action'],
            'user': event['user']
        }))
    
    async def message_edited(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message_edited',
            'message': event['message']
        }))
    
    async def message_deleted(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message_deleted',
            'message_id': event['message_id']
        }))
    
    # Database operations
    @database_sync_to_async
    def is_room_member(self):
        try:
            room = ChatRoom.objects.get(id=self.room_id)
            return room.members.filter(id=self.user.id).exists()
        except ChatRoom.DoesNotExist:
            return False
    
    @database_sync_to_async
    def save_message(self, content, reply_to_id=None):
        try:
            room = ChatRoom.objects.get(id=self.room_id)
            reply_to = None
            
            if reply_to_id:
                try:
                    reply_to = Message.objects.get(id=reply_to_id, room=room)
                except Message.DoesNotExist:
                    pass
            
            message = Message.objects.create(
                room=room,
                sender=self.user,
                content=content,
                reply_to=reply_to
            )
            return message
        except ChatRoom.DoesNotExist:
            return None
    
    @database_sync_to_async
    def serialize_message(self, message):
        serializer = MessageSerializer(message)
        return serializer.data
    
    @database_sync_to_async
    def add_message_reaction(self, message_id, reaction_type):
        try:
            from .models import MessageReaction
            message = Message.objects.get(id=message_id, room_id=self.room_id)
            reaction, created = MessageReaction.objects.get_or_create(
                message=message,
                user=self.user,
                reaction_type=reaction_type
            )
            return reaction if created else None
        except Message.DoesNotExist:
            return None
    
    @database_sync_to_async
    def remove_message_reaction(self, message_id, reaction_type):
        try:
            from .models import MessageReaction
            message = Message.objects.get(id=message_id, room_id=self.room_id)
            MessageReaction.objects.filter(
                message=message,
                user=self.user,
                reaction_type=reaction_type
            ).delete()
        except Message.DoesNotExist:
            pass
    
    @database_sync_to_async
    def edit_message(self, message_id, new_content):
        try:
            message = Message.objects.get(
                id=message_id,
                room_id=self.room_id,
                sender=self.user
            )
            message.edit_message(new_content)
            return message
        except Message.DoesNotExist:
            return None
    
    @database_sync_to_async
    def delete_message(self, message_id):
        try:
            message = Message.objects.get(
                id=message_id,
                room_id=self.room_id,
                sender=self.user
            )
            message.delete_message()
            return message
        except Message.DoesNotExist:
            return None
    
    @database_sync_to_async
    def update_user_status(self, is_online):
        self.user.set_online_status(is_online)


class DirectMessageConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for direct messages"""
    
    async def connect(self):
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.room_group_name = f'direct_{self.conversation_id}'
        self.user = self.scope['user']
        
        # Check if user is participant in the conversation
        if not await self.is_conversation_participant():
            await self.close()
            return
        
        # Join conversation group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
    
    async def disconnect(self, close_code):
        # Leave conversation group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'direct_message':
                await self.handle_direct_message(data)
            elif message_type == 'typing':
                await self.handle_typing(data)
            elif message_type == 'message_read':
                await self.handle_message_read(data)
        
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'error': 'Invalid JSON'
            }))
    
    async def handle_direct_message(self, data):
        content = data.get('content', '').strip()
        
        if not content:
            return
        
        # Save direct message to database
        message = await self.save_direct_message(content)
        
        if message:
            # Serialize message
            message_data = await self.serialize_direct_message(message)
            
            # Send message to conversation group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'direct_message',
                    'message': message_data
                }
            )
    
    async def handle_typing(self, data):
        is_typing = data.get('is_typing', False)
        
        # Send typing indicator to conversation group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator',
                'user': self.user.username,
                'is_typing': is_typing
            }
        )
    
    async def handle_message_read(self, data):
        message_ids = data.get('message_ids', [])
        await self.mark_messages_as_read(message_ids)
        
        # Send read receipt to conversation group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'messages_read',
                'message_ids': message_ids,
                'user': self.user.username
            }
        )
    
    # Receive message from conversation group
    async def direct_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'direct_message',
            'message': event['message']
        }))
    
    async def typing_indicator(self, event):
        # Don't send typing indicator to the sender
        if event['user'] != self.user.username:
            await self.send(text_data=json.dumps({
                'type': 'typing_indicator',
                'user': event['user'],
                'is_typing': event['is_typing']
            }))
    
    async def messages_read(self, event):
        # Don't send read receipt to the sender
        if event['user'] != self.user.username:
            await self.send(text_data=json.dumps({
                'type': 'messages_read',
                'message_ids': event['message_ids'],
                'user': event['user']
            }))
    
    # Database operations
    @database_sync_to_async
    def is_conversation_participant(self):
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            return conversation.participants.filter(id=self.user.id).exists()
        except Conversation.DoesNotExist:
            return False
    
    @database_sync_to_async
    def save_direct_message(self, content):
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            recipient = conversation.get_other_participant(self.user)
            
            message = DirectMessage.objects.create(
                sender=self.user,
                recipient=recipient,
                content=content
            )
            
            # Update conversation last message
            conversation.last_message = message
            conversation.save()
            
            return message
        except Conversation.DoesNotExist:
            return None
    
    @database_sync_to_async
    def serialize_direct_message(self, message):
        serializer = DirectMessageSerializer(message)
        return serializer.data
    
    @database_sync_to_async
    def mark_messages_as_read(self, message_ids):
        DirectMessage.objects.filter(
            id__in=message_ids,
            recipient=self.user,
            is_read=False
        ).update(is_read=True, read_at=timezone.now())