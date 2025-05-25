"""
WebSocket URL routing for the Voice AI Platform
"""
from django.urls import re_path
from .consumers import ChatConsumer

websocket_urlpatterns = [
    re_path(
        r"ws/chat/(?P<conversation_id>\w+)/(?P<token>[^/]+)/$", ChatConsumer.as_asgi()
    ),
    re_path(r"ws/chat/(?P<token>[^/]+)/$", ChatConsumer.as_asgi()),
]
