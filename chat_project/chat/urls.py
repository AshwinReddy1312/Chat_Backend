
from django.urls import path
from . import views

urlpatterns = [
    # Chat Rooms
    path('rooms/', views.ChatRoomListCreateView.as_view(), name='chatroom-list-create'),
    path('rooms/<int:pk>/', views.ChatRoomDetailView.as_view(), name='chatroom-detail'),
    path('rooms/<int:room_id>/members/', views.ChatRoomMembersView.as_view(), name='chatroom-members'),
    path('rooms/<int:room_id>/members/add/', views.add_room_member, name='add-room-member'),
    path('rooms/<int:room_id>/members/<int:user_id>/remove/', views.remove_room_member, name='remove-room-member'),
    path('rooms/<int:room_id>/read/', views.mark_messages_as_read, name='mark-messages-read'),
    
    # Messages
    path('rooms/<int:room_id>/messages/', views.MessageListCreateView.as_view(), name='message-list-create'),
    path('messages/<int:pk>/', views.MessageDetailView.as_view(), name='message-detail'),
    path('messages/<int:message_id>/reactions/', views.add_message_reaction, name='add-message-reaction'),
    path('messages/<int:message_id>/reactions/<str:reaction_type>/', views.remove_message_reaction, name='remove-message-reaction'),
    
    # Direct Messages
    path('conversations/', views.ConversationListView.as_view(), name='conversation-list'),
    path('conversations/create/', views.create_conversation, name='create-conversation'),
    path('conversations/<int:conversation_id>/messages/', views.DirectMessageListCreateView.as_view(), name='direct-message-list-create'),
    path('conversations/<int:conversation_id>/read/', views.mark_direct_messages_as_read, name='mark-direct-messages-read'),
    path('direct-messages/<int:pk>/', views.DirectMessageDetailView.as_view(), name='direct-message-detail'),
    
    # Search
    path('search/messages/', views.search_messages, name='search-messages'),
    path('search/rooms/', views.search_rooms, name='search-rooms'),
]