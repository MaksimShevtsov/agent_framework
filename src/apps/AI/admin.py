from django.contrib import admin, messages
from .models import Prompt, PromptCategory, AIModel, AIModelProvider


@admin.register(Prompt)
class PromptAdmin(admin.ModelAdmin):
    list_display = ("prompt", "response", "created_at", "ai_model")
    search_fields = ("prompt", "response")
    list_filter = ("ai_model",)
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    actions = ["activate_prompt", "deactivate_prompt"]

    def activate_prompt(self, request, queryset):
        for prompt in queryset:
            # Deactivate other prompts of the same type
            Prompt.objects.filter(type=prompt.type, is_active=True).exclude(
                pk=prompt.pk
            ).update(is_active=False)
            # Activate this prompt
            prompt.is_active = True
            prompt.save()

        if queryset.count() == 1:
            message = "1 prompt was activated."
        else:
            message = f"{queryset.count()} prompts were activated."

        self.message_user(request, message, messages.SUCCESS)

    activate_prompt.short_description = "Activate selected prompts"

    def deactivate_prompt(self, request, queryset):
        queryset.update(is_active=False)

        if queryset.count() == 1:
            message = "1 prompt was deactivated."
        else:
            message = f"{queryset.count()} prompts were deactivated."

        self.message_user(request, message, messages.SUCCESS)

    deactivate_prompt.short_description = "Deactivate selected prompts"


@admin.register(PromptCategory)
class PromptCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(AIModel)
class AIModelAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
    search_fields = ("name",)
    ordering = ("name",)

    actions = ["get_prompts"]

    def get_prompts(self, obj):
        return ", ".join([p.name for p in obj.prompts.all()])

    get_prompts.short_description = "Prompts"


@admin.register(AIModelProvider)
class AIModelProviderAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
    search_fields = ("name",)
    ordering = ("name",)

    actions = ["get_models"]

    def get_models(self, obj):
        return ", ".join([m.name for m in obj.models.all()])

    get_models.short_description = "Models"
