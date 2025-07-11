
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/chat/(?P<room_id>\d+)/$', consumers.ChatConsumer.as_asgi()),
    re_path(r'ws/direct/(?P<conversation_id>\d+)/$', consumers.DirectMessageConsumer.as_asgi()),
]