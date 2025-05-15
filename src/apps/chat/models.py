from django.db import models
from apps.AI.models import AIModel


class ChatUser(models.Model):
    """
    Model representing a user in a chat session.
    """

    is_verified = models.BooleanField(default=False)
    settings = models.JSONField(default=dict)

    class Meta:
        verbose_name = "Chat User"
        verbose_name_plural = "Chat Users"
        db_table = "chat_user"


class Chat(models.Model):
    """
    Model representing a chat session.
    """

    user = models.ForeignKey(
        "auth.User", related_name="chats", on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Chat {self.pk} for User {self.user.id}"

    class Meta:
        verbose_name = "Chat"
        verbose_name_plural = "Chats"
        ordering = ["-created_at"]


class Message(models.Model):
    """
    Model representing a message in a chat session.
    """

    SENDER_CHOICES = [
        ("user", "User"),
        ("assistant", "Assistant"),
        ("system", "System"),
    ]

    conversation = models.ForeignKey(
        "Conversation",
        related_name="messages",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    thread = models.ForeignKey(
        "Thread",
        related_name="messages",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    content = models.TextField()
    sender = models.CharField(max_length=50, choices=SENDER_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message {self.pk} in Thread {self.thread.pk}"

    class Meta:
        verbose_name = "Message"
        verbose_name_plural = "Messages"
        ordering = ["-created_at"]


class Conversation(models.Model):
    """
    Model representing a conversation in a chat session.
    """

    chat = models.ForeignKey(
        Chat, related_name="conversations", on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)

    ai_model = models.ForeignKey(
        AIModel,
        related_name="conversations",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(default=True)
    is_archived = models.BooleanField(default=False)

    def __str__(self):
        return f"Conversation {self.pk} in Chat {self.chat.pk}"

    class Meta:
        verbose_name = "Conversation"
        verbose_name_plural = "Conversations"
        ordering = ["-created_at"]


class Thread(models.Model):
    """
    Model representing a thread in a chat session.
    """

    conversation = models.ForeignKey(
        "Conversation",
        related_name="threads",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Thread {self.pk} in Conversation {self.conversation.pk}"

    class Meta:
        verbose_name = "Thread"
        verbose_name_plural = "Threads"
        ordering = ["-created_at"]
