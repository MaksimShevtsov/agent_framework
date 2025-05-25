"""
Django Channels configuration for WebSocket support
"""

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("127.0.0.1", 6379)],
            "capacity": 1500,
            "expiry": 10,
        },
    },
}

# ASGI application configuration
ASGI_APPLICATION = "core.asgi.application"

# WebSocket settings
WEBSOCKET_ACCEPT_ALL = True
WEBSOCKET_TOKEN_EXPIRE_SECONDS = 3600  # 1 hour
