import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

# Initialize Django ASGI application early to ensure the AppRegistry
# is populated before importing code that may import ORM models.
django_asgi_app = get_asgi_application()


def get_websocket_application():
    """Get WebSocket application after Django is initialized"""
    # Import WebSocket routing after Django is set up to avoid circular imports
    from websocket.routing import websocket_urlpatterns

    return AuthMiddlewareStack(URLRouter(websocket_urlpatterns))


application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": get_websocket_application(),
    }
)
