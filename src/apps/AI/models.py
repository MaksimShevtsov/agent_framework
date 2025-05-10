from django.db import models


# Create your models here.
class Prompt(models.Model):
    prompt = models.TextField()
    response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    is_active = models.BooleanField(
        default=True, help_text="Indicates if the prompt is active or not"
    )

    ai_model = models.ForeignKey(
        "AIModel",
        on_delete=models.SET_NULL,
        related_name="prompts",
        null=True,
        blank=True,
        help_text="The AI model using this prompt",
    )

    def __str__(self):
        return self.prompt

    class Meta:
        db_table = "prompt"
        verbose_name = "Prompt"
        verbose_name_plural = "Prompts"
        ordering = ["-created_at"]


class PromptCategory(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    prompts = models.ManyToManyField(Prompt, related_name="categories")

    def __str__(self):
        return self.name

    class Meta:
        db_table = "prompt_category"
        verbose_name = "Prompt Category"
        verbose_name_plural = "Prompt Categories"
        ordering = ["name"]


class PromptVersion(models.Model):
    prompt = models.ForeignKey(
        Prompt, on_delete=models.CASCADE, related_name="versions"
    )
    version = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Version of {self.prompt}"

    class Meta:
        db_table = "prompt_version"
        verbose_name = "Prompt Version"
        verbose_name_plural = "Prompt Versions"
        ordering = ["-created_at"]


class AIModel(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    version = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    token_limit = models.IntegerField(
        null=True,
        blank=True,
        help_text="Maximum number of tokens the model can process in a single request",
    )

    max_context_length = models.IntegerField(
        null=True, blank=True, help_text="Maximum context length for the model"
    )

    max_response_length = models.IntegerField(
        null=True, blank=True, help_text="Maximum response length for the model"
    )

    def __str__(self):
        return self.name

    class Meta:
        db_table = "ai_model"
        verbose_name = "AI Model"
        verbose_name_plural = "AI Models"
        ordering = ["name"]


class AIModelProvider(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    api_key = models.CharField(max_length=255)
    models = models.ManyToManyField(AIModel, related_name="providers")

    def __str__(self):
        return self.name

    class Meta:
        db_table = "ai_model_provider"
        verbose_name = "AI Model Provider"
        verbose_name_plural = "AI Model Providers"
        ordering = ["name"]
