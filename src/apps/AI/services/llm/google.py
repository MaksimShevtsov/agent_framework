from google import genai
from .base import BaseAIService


class BaseGoogleService(BaseAIService):
    """
    Base class for Google AI services.
    This class inherits from BaseAIService
    and provides a structure for Google-specific AI services.
    """

    def __init__(self):
        super(BaseGoogleService, self).__init__()
        self.api_key = None  # TODO get from db
        self.client = genai.Client(api_key=self.api_key)
