from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.db import models


def avatar_upload_path(instance, filename):
    return f"avatars/{uuid4().hex}{Path(filename).suffix.lower()}"


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name="пользователь",
    )
    display_name = models.CharField("отображаемое имя", max_length=50, blank=True)
    avatar = models.ImageField("аватар", upload_to=avatar_upload_path, blank=True)

    class Meta:
        verbose_name = "профиль"
        verbose_name_plural = "профили"

    def __str__(self):
        return self.display_name or self.user.get_username()
