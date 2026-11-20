from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import User

from .models import Profile


class ProfileInline(admin.StackedInline):
    model = Profile
    extra = 1


admin.site.unregister(User)


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    inlines = (ProfileInline,)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "display_name", "avatar")
    search_fields = ("user__username", "user__email", "display_name")
    list_filter = ("user__is_active",)
    list_select_related = ("user",)
    raw_id_fields = ("user",)
