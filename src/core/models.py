from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class BaseModel(models.Model):
    """
    Base model for all models in the application
    """

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.__class__.__name__}-{self.pk}"


class Instance(BaseModel):
    """
    Model representing an instance of the application.
    """

    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = _("instance")
        verbose_name_plural = _("instances")
        db_table = "instance"

    def __str__(self):
        return self.name


# class AdminUser(AbstractBaseUser, PermissionsMixin, BaseModel):
#     email = models.EmailField(_("email address"), unique=True)
#     username = models.CharField(_("username"), max_length=150, blank=True)
#     api_key = models.CharField(_("api key"), max_length=40, blank=True)
#     is_staff = models.BooleanField(_("staff status"), default=False)
#     is_active = models.BooleanField(_("active"), default=True)
#     date_joined = models.DateTimeField(_("date joined"), auto_now_add=True)

#     USERNAME_FIELD = "email"
#     REQUIRED_FIELDS = []

#     class Meta:
#         verbose_name = _("admin_user")
#         verbose_name_plural = _("users")
#         db_table = "admin_user"

#     objects = BaseUserManager()
