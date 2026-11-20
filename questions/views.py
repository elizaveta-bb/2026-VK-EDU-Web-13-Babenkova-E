from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .forms import AnswerForm, CorrectAnswerForm, QuestionForm, VoteForm
from .models import Answer, Question, Tag
from .utils import paginate


def question_list(request, template, questions, **context):
    page = paginate(questions, request)
    page.object_list = Question.objects.cards_for_page(page.object_list, request.user)
    return render(request, template, {**context, "page_obj": page})


def index(request):
    return question_list(request, "questions/index.html", Question.objects.newest())


def hot(request):
    return question_list(request, "questions/hot.html", Question.objects.best())


def tag(request, tag_name):
    selected_tag = get_object_or_404(Tag, slug=tag_name.lower())
    questions = Question.objects.by_tag(selected_tag)
    return question_list(request, "questions/tag.html", questions, tag_name=selected_tag.name)


def render_question(request, question, form):
    page = paginate(Answer.objects.for_question(question, request.user), request)
    return render(request, "questions/question.html", {
        "question": question,
        "page_obj": page,
        "form": form,
    })


@require_http_methods(["GET", "POST"])
def question_detail(request, question_id):
    question = get_object_or_404(Question.objects.for_display(request.user), pk=question_id)
    if request.method == "POST":
        return add_answer(request, question)
    return render_question(request, question, AnswerForm())


@login_required
def add_answer(request, question):
    form = AnswerForm(request.POST, author=request.user, question=question)
    if form.is_valid():
        answer = form.save()
        page = Answer.objects.page_for(answer)
        return redirect(f"{question.get_absolute_url()}?page={page}#answer-{answer.pk}")
    return render_question(request, question, form)


@login_required
@require_http_methods(["GET", "POST"])
def ask(request):
    form = QuestionForm(request.POST if request.method == "POST" else None, author=request.user)
    if request.method == "POST" and form.is_valid():
        return redirect(form.save())
    return render(request, "questions/ask.html", {"form": form})


def vote_question(request):
    return process_ajax(request, VoteForm, target_model=Question)


def vote_answer(request):
    return process_ajax(request, VoteForm, target_model=Answer)


def correct_answer(request):
    return process_ajax(request, CorrectAnswerForm)


@transaction.atomic
def process_ajax(request, form_class, **kwargs):
    if request.method != "POST":
        return JsonResponse({"error": "Для этого действия нужен запрос POST."}, status=405, headers={"Allow": "POST"})
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Войдите в аккаунт."}, status=401)

    form = form_class(request.POST, user=request.user, **kwargs)
    if form.is_valid():
        return JsonResponse(form.save())

    errors = form.errors.get_json_data()
    codes = {error["code"] for field_errors in errors.values() for error in field_errors}
    status = 400
    if "forbidden" in codes:
        status = 403
    elif "duplicate" in codes:
        status = 409
    return JsonResponse({"errors": errors}, status=status)
