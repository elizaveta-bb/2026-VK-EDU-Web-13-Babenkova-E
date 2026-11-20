from django.conf import settings
from django.db import models
from django.db.models.functions import Coalesce
from django.urls import reverse
from django.utils import timezone


class TagQuerySet(models.QuerySet):
    def popular(self, limit=8):
        return (
            self.annotate(question_count=models.Count("questions"))
            .filter(question_count__gt=0)
            .order_by("-question_count", "name")[:limit]
        )


class Tag(models.Model):
    name = models.CharField("название", max_length=50, unique=True)
    slug = models.SlugField("адрес тега", max_length=70, unique=True)
    created_at = models.DateTimeField("дата создания", default=timezone.now)

    objects = TagQuerySet.as_manager()

    class Meta:
        verbose_name = "тег"
        verbose_name_plural = "теги"
        ordering = ("name",)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("questions:tag", args=[self.slug])


class QuestionManager(models.Manager):
    def _with_ratings(self):
        ratings = (
            QuestionLike.objects.filter(question_id=models.OuterRef("pk"))
            .order_by()
            .values("question_id")
            .annotate(total=models.Sum("value"))
            .values("total")
        )
        return self.annotate(rating=Coalesce(models.Subquery(ratings), 0))

    def for_display(self):
        # Отдельные подзапросы не перемножают строки ответов и оценок.
        answer_counts = (
            Answer.objects.filter(question_id=models.OuterRef("pk"))
            .order_by()
            .values("question_id")
            .annotate(total=models.Count("pk"))
            .values("total")
        )
        return (
            self._with_ratings()
            .select_related("author__profile")
            .prefetch_related("tags")
            .annotate(answers_count=Coalesce(models.Subquery(answer_counts), 0))
        )

    def newest(self):
        return self.order_by("-created_at", "-pk")

    def best(self):
        return self._with_ratings().order_by("-rating", "-created_at", "-pk")

    def by_tag(self, tag):
        return self.newest().filter(tags=tag)

    def cards_for_page(self, questions):
        # Загружаем связи и счётчики только для вопросов на выбранной странице.
        ids = list(questions.values_list("pk", flat=True))
        cards = self.for_display().in_bulk(ids)
        return [cards[pk] for pk in ids if pk in cards]


class Question(models.Model):
    title = models.CharField("заголовок", max_length=200)
    text = models.TextField("текст")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="questions",
        verbose_name="автор",
    )
    tags = models.ManyToManyField(Tag, related_name="questions", verbose_name="теги", blank=True)
    created_at = models.DateTimeField("дата создания", default=timezone.now)

    objects = QuestionManager()

    class Meta:
        verbose_name = "вопрос"
        verbose_name_plural = "вопросы"
        indexes = [models.Index(fields=["-created_at", "-id"], name="question_newest_idx")]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("questions:question_detail", args=[self.pk])


class AnswerManager(models.Manager):
    def for_question(self, question):
        ratings = (
            AnswerLike.objects.filter(answer_id=models.OuterRef("pk"))
            .order_by()
            .values("answer_id")
            .annotate(total=models.Sum("value"))
            .values("total")
        )
        return (
            self.filter(question=question)
            .select_related("author__profile")
            .annotate(rating=Coalesce(models.Subquery(ratings), 0))
            .order_by("-is_correct", "created_at", "pk")
        )


class Answer(models.Model):
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, related_name="answers", verbose_name="вопрос"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="answers",
        verbose_name="автор",
    )
    text = models.TextField("текст")
    is_correct = models.BooleanField("правильный ответ", default=False)
    created_at = models.DateTimeField("дата создания", default=timezone.now)

    objects = AnswerManager()

    class Meta:
        verbose_name = "ответ"
        verbose_name_plural = "ответы"
        indexes = [
            models.Index(fields=["question", "-is_correct", "created_at", "id"], name="answer_order_idx")
        ]

    def __str__(self):
        return self.text[:80]


class VoteValue(models.IntegerChoices):
    LIKE = 1, "Нравится"
    DISLIKE = -1, "Не нравится"


class QuestionLike(models.Model):
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, related_name="likes", verbose_name="вопрос"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="question_likes",
        verbose_name="пользователь",
    )
    value = models.SmallIntegerField("оценка", choices=VoteValue.choices, default=VoteValue.LIKE)

    class Meta:
        verbose_name = "оценка вопроса"
        verbose_name_plural = "оценки вопросов"
        unique_together = (("question", "user"),)
        constraints = [
            models.CheckConstraint(condition=models.Q(value__in=VoteValue.values), name="question_vote_value")
        ]

    def __str__(self):
        return f"Оценка вопроса №{self.question_id} от пользователя №{self.user_id}"


class AnswerLike(models.Model):
    answer = models.ForeignKey(
        Answer, on_delete=models.CASCADE, related_name="likes", verbose_name="ответ"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="answer_likes",
        verbose_name="пользователь",
    )
    value = models.SmallIntegerField("оценка", choices=VoteValue.choices, default=VoteValue.LIKE)

    class Meta:
        verbose_name = "оценка ответа"
        verbose_name_plural = "оценки ответов"
        unique_together = (("answer", "user"),)
        constraints = [
            models.CheckConstraint(condition=models.Q(value__in=VoteValue.values), name="answer_vote_value")
        ]

    def __str__(self):
        return f"Оценка ответа №{self.answer_id} от пользователя №{self.user_id}"