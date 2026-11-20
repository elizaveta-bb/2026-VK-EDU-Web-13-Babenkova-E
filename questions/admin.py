from django.contrib import admin
from django.contrib.admin.widgets import ForeignKeyRawIdWidget

from .models import Answer, AnswerLike, Question, QuestionLike, Tag


class InlineAuthorWidget(ForeignKeyRawIdWidget):
    def label_and_url_for_value(self, value):
        # Имя автора уже загружено в readonly-поле, повторный запрос не нужен.
        return "", ""


class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 0
    fields = ("text", "author", "author_username", "is_correct", "created_at")
    readonly_fields = ("author_username",)
    raw_id_fields = ("author",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("author")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "author":
            kwargs["widget"] = InlineAuthorWidget(
                db_field.remote_field, self.admin_site, using=kwargs.get("using")
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    @admin.display(description="Имя пользователя")
    def author_username(self, answer):
        return answer.author.get_username() if answer and answer.author_id else ""


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "created_at")
    search_fields = ("title", "text", "author__username")
    list_filter = ("created_at",)
    list_select_related = ("author",)
    raw_id_fields = ("author",)
    autocomplete_fields = ("tags",)
    inlines = (AnswerInline,)
    show_full_result_count = False
    show_facets = admin.ShowFacets.NEVER


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ("short_text", "question", "author", "is_correct", "created_at")
    search_fields = ("text", "question__title", "author__username")
    list_filter = ("is_correct", "created_at")
    list_select_related = ("question", "author")
    raw_id_fields = ("question", "author")
    show_full_result_count = False
    show_facets = admin.ShowFacets.NEVER

    @admin.display(description="Текст")
    def short_text(self, answer):
        return str(answer)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "created_at")
    search_fields = ("name", "slug")
    list_filter = ("created_at",)
    prepopulated_fields = {"slug": ("name",)}


class VoteAdmin(admin.ModelAdmin):
    list_filter = ("value",)
    show_full_result_count = False
    show_facets = admin.ShowFacets.NEVER


@admin.register(QuestionLike)
class QuestionLikeAdmin(VoteAdmin):
    list_display = ("question", "user", "value")
    search_fields = ("question__title", "user__username")
    list_select_related = ("question", "user")
    raw_id_fields = ("question", "user")


@admin.register(AnswerLike)
class AnswerLikeAdmin(VoteAdmin):
    list_display = ("answer", "user", "value")
    search_fields = ("answer__text", "user__username")
    list_select_related = ("answer", "user")
    raw_id_fields = ("answer", "user")
