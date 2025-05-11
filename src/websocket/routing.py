from django.urls import re_path
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from .consumers import ChatConsumer

application = ProtocolTypeRouter(
    {
        "websocket": AllowedHostsOriginValidator(
            URLRouter(
                [
                    re_path(r"ws/connect/(?P<token>[^/]+)/$", ChatConsumer.as_asgi()),
                ]
            )
        ),
    }
)
