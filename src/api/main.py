"""
Main API router for the Voice AI Platform
"""
import logging
from typing import Optional

from django.core.exceptions import ValidationError
from django.http import JsonResponse
from ninja import NinjaAPI
from ninja.security import HttpBearer

from apps.tokens.models import APIKey
from .ai import router as ai_router
from .chat import router as chat_router
from .voice import router as voice_router

logger = logging.getLogger(__name__)


class APIKeyAuth(HttpBearer):
    """API Key authentication for REST endpoints"""

    def authenticate(self, request, token: str) -> Optional[str]:
        try:
            # Use the custom manager method from APIKey model
            api_key = APIKey.objects.get_from_key(token)
            if not api_key.revoked:
                return api_key.name
        except (APIKey.DoesNotExist, AttributeError):
            pass
        return None


# Initialize the main API
api = NinjaAPI(
    title="Voice AI Platform API",
    version="1.0.0",
    description="Real-time Voice AI Platform with WebRTC and WebSocket support",
    auth=APIKeyAuth(),
    docs_url="/docs/",
)

# Register API routers
api.add_router("/chat/", chat_router, tags=["Chat"])
api.add_router("/ai/", ai_router, tags=["AI"])
api.add_router("/voice/", voice_router, tags=["Voice"])


@api.get("/health", auth=None, tags=["System"])
def health_check(request):
    """Health check endpoint"""
    return {"status": "healthy", "service": "voice-ai-platform"}


@api.get("/version", auth=None, tags=["System"])
def version_info(request):
    """Get API version information"""
    return {
        "version": "1.0.0",
        "name": "Voice AI Platform API",
        "features": ["websocket", "webrtc", "voice", "chat", "ai"],
    }


@api.exception_handler(ValidationError)
def validation_exception_handler(request, exc):
    """Handle validation errors"""
    logger.error(f"Validation error: {exc}")
    return JsonResponse({"error": "Validation failed", "details": str(exc)}, status=400)


@api.exception_handler(Exception)
def global_exception_handler(request, exc):
    """Handle unexpected errors"""
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return JsonResponse({"error": "Internal server error"}, status=500)
