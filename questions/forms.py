from uuid import uuid4

from django import forms
from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.utils.text import slugify

from .models import Answer, Question, Tag, VoteValue


class QuestionForm(forms.ModelForm):
    title = forms.CharField(label="Заголовок", min_length=10, max_length=150)
    text = forms.CharField(
        label="Текст вопроса", min_length=20, max_length=5000,
        widget=forms.Textarea(attrs={"rows": 8}),
    )
    tags = forms.CharField(
        label="Теги",
        max_length=100,
        help_text="От 1 до 3 тегов через запятую. Например, python, django.",
    )

    class Meta:
        model = Question
        fields = ("title", "text")

    def __init__(self, *args, author, **kwargs):
        super().__init__(*args, **kwargs)
        self.author = author

    def clean_tags(self):
        names = dict.fromkeys(
            part.strip().lower()
            for part in self.cleaned_data["tags"].split(",")
            if part.strip()
        )
        if not 1 <= len(names) <= 3:
            raise forms.ValidationError("Укажите от 1 до 3 разных тегов.")
        if any(len(name) > 50 for name in names):
            raise forms.ValidationError("Каждый тег должен быть не длиннее 50 символов.")
        return list(names)

    @transaction.atomic
    def save(self):
        self.instance.author = self.author
        question = super().save()
        question.tags.set([get_or_create_tag(name) for name in self.cleaned_data["tags"]])
        return question


def get_or_create_tag(name):
    existing = Tag.objects.filter(name__iexact=name).order_by("pk").first()
    if existing:
        return existing

    slug = slugify(name)[:50] or f"tag-{uuid4().hex[:12]}"
    try:
        tag, _ = Tag.objects.get_or_create(name=name, defaults={"slug": slug})
    except IntegrityError:
        # Разные названия могут иметь одинаковый slug, например C++ и C#.
        tag, _ = Tag.objects.get_or_create(
            name=name, defaults={"slug": f"{slug}-{uuid4().hex[:12]}"},
        )
    return tag


class AnswerForm(forms.ModelForm):
    text = forms.CharField(
        label="Текст ответа", min_length=20, max_length=5000,
        widget=forms.Textarea(attrs={"rows": 5}),
    )

    class Meta:
        model = Answer
        fields = ("text",)

    def __init__(self, *args, author=None, question=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.author = author
        self.question = question

    def save(self, commit=True):
        self.instance.author = self.author
        self.instance.question = self.question
        return super().save(commit=commit)


class VoteForm(forms.Form):
    target_id = forms.ModelChoiceField(queryset=None)
    value = forms.TypedChoiceField(choices=VoteValue.choices, coerce=int)

    def __init__(self, *args, user, target_model, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["target_id"].queryset = target_model.objects.select_for_update()

    def clean(self):
        data = super().clean()
        target = data.get("target_id")
        value = data.get("value")
        if target is not None and value is not None:
            if target.likes.filter(user=self.user, value=value).exists():
                self.add_error("value", forms.ValidationError("Эта оценка уже поставлена.", code="duplicate"))
        return data

    def save(self):
        target = self.cleaned_data["target_id"]
        value = self.cleaned_data["value"]
        target.likes.update_or_create(user=self.user, defaults={"value": value})
        rating = target.likes.aggregate(total=Sum("value", default=0))["total"]
        return {"rating": rating, "my_vote": value}


class CorrectAnswerForm(forms.Form):
    question_id = forms.ModelChoiceField(queryset=Question.objects.select_for_update())
    answer_id = forms.ModelChoiceField(queryset=Answer.objects.select_for_update())
    checked = forms.TypedChoiceField(
        choices=(("1", "Отметить"), ("0", "Снять отметку")),
        coerce=lambda value: value == "1",
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean(self):
        data = super().clean()
        question = data.get("question_id")
        answer = data.get("answer_id")
        if question is not None:
            if question.author_id != self.user.pk:
                self.add_error(None, forms.ValidationError(
                    "Правильный ответ может выбрать только автор вопроса.", code="forbidden",
                ))
            elif answer is not None and answer.question_id != question.pk:
                self.add_error("answer_id", "Этот ответ относится к другому вопросу.")
        return data

    def save(self):
        question = self.cleaned_data["question_id"]
        answer = self.cleaned_data["answer_id"]
        checked = self.cleaned_data["checked"]
        if checked:
            question.answers.filter(is_correct=True).exclude(pk=answer.pk).update(is_correct=False)
        question.answers.filter(pk=answer.pk).update(is_correct=checked)
        return {
            "correct_answer_ids": list(question.answers.filter(is_correct=True).values_list("pk", flat=True)),
        }
