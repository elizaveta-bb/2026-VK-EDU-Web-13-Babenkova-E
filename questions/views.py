from django.http import Http404
from django.shortcuts import render
from django.utils import timezone
from .utils import paginate


TAGS = ["python", "django", "html", "css"]

QUESTIONS = []

for i in range(1, 51):
    QUESTIONS.append({
        "id": i,
        "title": f"Вопрос №{i}",
        "text": f"Тестовый текст вопроса №{i}.",
        "rating": (i * 7) % 100,
        "tags": [TAGS[(i - 1) % len(TAGS)]],
        "answers_count": 30,
                "author": f"Пользователь {i}",
        "created_at": timezone.now(),
        "user_vote": (i % 3) - 1,
    })


def index(request):
    questions = sorted(
        QUESTIONS,
        key=lambda question: question["id"],
        reverse=True,
    )

    page = paginate(questions, request)

    return render(
        request,
        "questions/index.html",
        {
            "questions": page,
            "page_obj": page,
        },
    )


def hot(request):
    questions = sorted(
        QUESTIONS,
        key=lambda question: question["rating"],
        reverse=True,
    )

    page = paginate(questions, request)

    return render(
        request,
        "questions/hot.html",
        {
            "questions": page,
            "page_obj": page,
        },
    )


def tag(request, tag_name):
    questions = [
        question
        for question in QUESTIONS
        if tag_name.lower() in question["tags"]
    ]

    page = paginate(questions, request)

    return render(
        request,
        "questions/tag.html",
        {
            "questions": page,
            "page_obj": page,
            "tag_name": tag_name,
        },
    )


def question_detail(request, question_id):
    question = None

    for item in QUESTIONS:
        if item["id"] == question_id:
            question = item
            break

    if question is None:
        raise Http404("Вопрос не найден")

    answers = []

    for i in range(1, 31):
        answers.append({
            "id": i,
            "text": f"Ответ №{i} на вопрос №{question_id}.",
            "author": f"Пользователь {i}",
            "rating": i * 2,
            "user_vote": (i % 3) - 1,
            "created_at": timezone.now(),
            "is_correct": i == 1,
        })

    page = paginate(answers, request)

    return render(
        request,
        "questions/question.html",
        {
            "question": question,
            "answers": page,
            "page_obj": page,
        },
    )

def ask(request):
    return render(request, "questions/ask.html")