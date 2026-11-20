from pathlib import Path

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, UsernameField
from django.db import transaction

from .models import Profile


class LoginForm(AuthenticationForm):
    username = UsernameField(label="Логин")


class SignupForm(UserCreationForm):
    username = UsernameField(label="Логин", min_length=3, max_length=30)
    email = forms.EmailField(label="Email", max_length=254)
    first_name = forms.CharField(label="Имя", max_length=50)

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ("username", "email", "first_name")

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            Profile.objects.create(user=user, display_name=user.first_name)
        return user


class AvatarField(forms.ImageField):
    def to_python(self, data):
        if data:
            if data.size > 2 * 1024 * 1024:
                raise forms.ValidationError("Размер аватарки не должен превышать 2 МБ.")
            expected_format = {
                ".jpg": "JPEG",
                ".jpeg": "JPEG",
                ".png": "PNG",
            }.get(Path(data.name).suffix.lower())
            if expected_format is None:
                raise forms.ValidationError("Загрузите файл с расширением JPG, JPEG или PNG.")

        image = super().to_python(data)
        if image and image.image.format != expected_format:
            raise forms.ValidationError("Содержимое файла должно соответствовать его расширению.")
        return image


class ProfileForm(forms.ModelForm):
    email = forms.EmailField(label="Email", max_length=254)
    display_name = forms.CharField(label="Ник", max_length=50)
    avatar = AvatarField(
        label="Аватарка",
        required=False,
        help_text="PNG или JPEG, до 2 МБ.",
        widget=forms.ClearableFileInput(attrs={"accept": "image/png,image/jpeg"}),
    )

    class Meta:
        model = Profile
        fields = ("email", "display_name", "avatar")

    def __init__(self, *args, user, **kwargs):
        self.user = user
        profile = Profile.objects.filter(user=user).first() or Profile(user=user)
        super().__init__(*args, instance=profile, **kwargs)
        self.initial.setdefault("email", user.email)
        if not self.initial.get("display_name"):
            self.initial["display_name"] = user.get_full_name() or user.get_username()

    @transaction.atomic
    def save(self, commit=True):
        if not commit:
            return super().save(commit=False)

        self.user.email = self.cleaned_data["email"]
        self.user.save(update_fields=["email"])

        profile, _ = Profile.objects.get_or_create(user=self.user)
        profile.display_name = self.cleaned_data["display_name"]
        if "avatar" in self.changed_data:
            profile.avatar = self.cleaned_data["avatar"] or ""
        profile.save(update_fields=["display_name", "avatar"])
        self.instance = profile
        return profile
