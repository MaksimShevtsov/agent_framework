# Generated by Django 5.2 on 2025-05-15 21:54

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("chat", "0002_chatuser"),
        ("core", "__first__"),
    ]

    operations = [
        migrations.CreateModel(
            name="APIKey",
            fields=[
                (
                    "id",
                    models.CharField(
                        editable=False,
                        max_length=150,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                    ),
                ),
                ("prefix", models.CharField(editable=False, max_length=8, unique=True)),
                ("hashed_key", models.CharField(editable=False, max_length=150)),
                ("created", models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    "name",
                    models.CharField(
                        default=None,
                        help_text="A free-form name for the API key. Need not be unique. 50 characters max.",  # noqa: E501
                        max_length=50,
                    ),
                ),
                (
                    "revoked",
                    models.BooleanField(
                        blank=True,
                        default=False,
                        help_text="If the API key is revoked, clients cannot use it anymore. (This cannot be undone.)",  # noqa: E501
                    ),
                ),
                (
                    "expiry_date",
                    models.DateTimeField(
                        blank=True,
                        help_text="Once API key expires, clients cannot use it anymore.",  # noqa: E501
                        null=True,
                        verbose_name="Expires",
                    ),
                ),
            ],
            options={
                "verbose_name": "API key",
                "verbose_name_plural": "API keys",
                "ordering": ("-created",),
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="WebSocketToken",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("token", models.CharField(max_length=150, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("used", models.BooleanField(default=False)),
                (
                    "instance",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="core.instance"
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="chat.chatuser"
                    ),
                ),
            ],
            options={
                "verbose_name": "WebSocket token",
                "verbose_name_plural": "WebSocket tokens",
                "db_table": "websocket_tokens",
                "ordering": ("-created_at",),
            },
        ),
    ]
