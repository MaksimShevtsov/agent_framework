import logging
from ..models import Prompt


class BaseAIService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def get_response(self, prompt: str) -> str:
        """
        This method should be overridden
        by subclasses to provide the actual AI response.
        """
        raise NotImplementedError("Subclasses should implement this method.")

    def get_model_token_limit(self) -> int:
        """
        This method should be overridden
        by subclasses to provide the model's token limit.
        """
        raise NotImplementedError("Subclasses should implement this method.")

    def num_tokens_from_messages(self, messages: list) -> int:
        """
        This method should be overridden
        by subclasses to calculate the number of tokens from messages.
        """
        raise NotImplementedError("Subclasses should implement this method.")

    def truncate_messages(self, messages: list, max_tokens: int) -> list:
        """
        This method should be overridden
        by subclasses to truncate messages to fit within the token limit.
        """
        raise NotImplementedError("Subclasses should implement this method.")

    def truncate_prompt(self, prompt: str, max_tokens: int) -> str:
        """
        This method should be overridden
        by subclasses to truncate the prompt to fit within the token limit.
        """
        raise NotImplementedError("Subclasses should implement this method.")

    def get_context(self) -> str:
        """
        This method should be overridden
        by subclasses to provide the context for the AI model.
        """
        raise NotImplementedError("Subclasses should implement this method.")

    def generate_summary(self, text: str) -> str:
        """
        This method should be overridden
        by subclasses to generate a summary of the given text.
        """
        raise NotImplementedError("Subclasses should implement this method.")

    def _get_active_prompt(self) -> str | None:
        """
        This method should be overridden
        by subclasses to get the active prompt.
        """
        try:
            # Assuming there's a Prompt model with an is_active field
            prompt = Prompt.objects.get(is_active=True)
            return prompt.prompt
        except Prompt.DoesNotExist:
            self.logger.error("No active prompt found.")
            return None
        except Exception as e:
            self.logger.error(f"Error retrieving active prompt: {e}")
            return None

    def log(self, message: str):
        """
        Log a message using the logger.
        """
        self.logger.info(message)
        self.log(message)
