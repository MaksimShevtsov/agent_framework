"""
AI API endpoints for model management and inference
"""
from ninja import Router, Schema
from typing import List, Optional, Dict, Any
from datetime import datetime
from django.shortcuts import get_object_or_404
import logging

from apps.AI.models import AIModel, Prompt

logger = logging.getLogger(__name__)
router = Router()


# Schemas
class AIModelResponse(Schema):
    id: int
    name: str
    provider: str
    model_type: str
    is_active: bool
    parameters: Dict[str, Any]
    created_at: datetime


class InferenceRequest(Schema):
    model_id: int
    prompt: str
    context: Optional[List[Dict[str, str]]] = []
    parameters: Optional[Dict[str, Any]] = {}


class InferenceResponse(Schema):
    response: str
    model_used: str
    processing_time_ms: float
    tokens_used: Optional[int] = None


class PromptResponse(Schema):
    id: int
    name: str
    content: str
    category: str
    variables: List[str]


@router.get("/models/", response=List[AIModelResponse], tags=["Models"])
def list_ai_models(request):
    """List all available AI models"""
    try:
        models = AIModel.objects.filter(is_active=True).select_related("provider")
        return [
            {
                "id": model.id,
                "name": model.name,
                "provider": model.provider.name,
                "model_type": model.model_type,
                "is_active": model.is_active,
                "parameters": model.parameters,
                "created_at": model.created_at,
            }
            for model in models
        ]
    except Exception as e:
        logger.error(f"Failed to list AI models: {e}")
        return {"error": "Failed to fetch models"}, 500


@router.get("/models/{model_id}/", response=AIModelResponse, tags=["Models"])
def get_ai_model(request, model_id: int):
    """Get details of a specific AI model"""
    try:
        model = get_object_or_404(AIModel, id=model_id)
        return {
            "id": model.id,
            "name": model.name,
            "provider": model.provider.name,
            "model_type": model.model_type,
            "is_active": model.is_active,
            "parameters": model.parameters,
            "created_at": model.created_at,
        }
    except Exception as e:
        logger.error(f"Failed to get AI model: {e}")
        return {"error": "Model not found"}, 404


@router.post("/inference/", response=InferenceResponse, tags=["Inference"])
def run_inference(request, data: InferenceRequest):
    """Run AI inference with the specified model"""
    try:
        import time

        start_time = time.time()

        model = get_object_or_404(AIModel, id=data.model_id, is_active=True)

        # For now, return a mock response
        # In production, this would integrate with actual AI models
        mock_response = f"AI response from {model.name} to: {data.prompt}"

        processing_time = (time.time() - start_time) * 1000

        return {
            "response": mock_response,
            "model_used": model.name,
            "processing_time_ms": processing_time,
            "tokens_used": len(data.prompt.split()) + len(mock_response.split()),
        }

    except Exception as e:
        logger.error(f"Failed to run inference: {e}")
        return {"error": "Inference failed"}, 500


@router.get("/prompts/", response=List[PromptResponse], tags=["Prompts"])
def list_prompts(request, category: Optional[str] = None):
    """List available prompts, optionally filtered by category"""
    try:
        prompts = Prompt.objects.all().select_related("category")

        if category:
            prompts = prompts.filter(category__name=category)

        return [
            {
                "id": prompt.id,
                "name": prompt.name,
                "content": prompt.content,
                "category": prompt.category.name
                if prompt.category
                else "uncategorized",
                "variables": prompt.variables or [],
            }
            for prompt in prompts
        ]
    except Exception as e:
        logger.error(f"Failed to list prompts: {e}")
        return {"error": "Failed to fetch prompts"}, 500


@router.get("/prompts/{prompt_id}/", response=PromptResponse, tags=["Prompts"])
def get_prompt(request, prompt_id: int):
    """Get a specific prompt"""
    try:
        prompt = get_object_or_404(Prompt, id=prompt_id)
        return {
            "id": prompt.id,
            "name": prompt.name,
            "content": prompt.content,
            "category": prompt.category.name if prompt.category else "uncategorized",
            "variables": prompt.variables or [],
        }
    except Exception as e:
        logger.error(f"Failed to get prompt: {e}")
        return {"error": "Prompt not found"}, 404


@router.post("/models/{model_id}/chat/", response=InferenceResponse, tags=["Chat"])
def chat_with_model(request, model_id: int, data: InferenceRequest):
    """Have a conversation with an AI model"""
    try:
        import time

        start_time = time.time()

        model = get_object_or_404(AIModel, id=model_id, is_active=True)

        # Build conversation context
        conversation_text = ""
        for msg in data.context:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            conversation_text += f"{role}: {content}\n"

        conversation_text += f"user: {data.prompt}\nassistant: "

        # Mock AI response based on context
        mock_response = f"Based on our conversation, I understand you're asking about '{data.prompt}'. Here's my response from {model.name}."  # noqa: E501

        processing_time = (time.time() - start_time) * 1000

        return {
            "response": mock_response,
            "model_used": model.name,
            "processing_time_ms": processing_time,
            "tokens_used": len(conversation_text.split()) + len(mock_response.split()),
        }

    except Exception as e:
        logger.error(f"Failed to chat with model: {e}")
        return {"error": "Chat failed"}, 500
