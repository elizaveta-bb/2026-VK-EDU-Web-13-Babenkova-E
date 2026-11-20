from django.shortcuts import get_object_or_404, render

from .models import Answer, Question, Tag
from .utils import paginate


def question_list(request, template, questions, **context):
    page = paginate(questions, request)
    page.object_list = Question.objects.cards_for_page(page.object_list)
    return render(request, template, {**context, "page_obj": page})


def index(request):
    return question_list(request, "questions/index.html", Question.objects.newest())


def hot(request):
    return question_list(request, "questions/hot.html", Question.objects.best())


def tag(request, tag_name):
    selected_tag = get_object_or_404(Tag, slug=tag_name.lower())
    questions = Question.objects.by_tag(selected_tag)
    return question_list(request, "questions/tag.html", questions, tag_name=selected_tag.name)


def question_detail(request, question_id):
    question = get_object_or_404(Question.objects.for_display(), pk=question_id)
    page = paginate(Answer.objects.for_question(question), request)
    return render(request, "questions/question.html", {"question": question, "page_obj": page})


def ask(request):
    return render(request, "questions/ask.html")