from datetime import timedelta
from itertools import islice
from random import Random
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.test.utils import override_settings
from django.utils import timezone
from faker import Faker

from core.models import Profile
from questions.models import Answer, AnswerLike, Question, QuestionLike, Tag, VoteValue


BATCH_SIZE = 2000
QUESTION_BATCH_SIZE = 1000
TOPICS = (
    "Python", "Django", "HTML", "CSS", "JavaScript", "PostgreSQL",
    "Docker", "Git", "Bootstrap", "HTTP", "SQL", "API",
)
QUESTION_TITLES = (
    "С чего начать изучение {topic}?",
    "Как настроить {topic} для учебного проекта?",
    "Как тестировать проект с {topic}?",
    "Какие ошибки стоит проверить при работе с {topic}?",
)


def bulk_insert(model, rows):
    rows = iter(rows)
    while batch := list(islice(rows, BATCH_SIZE)):
        yield from model.objects.bulk_create(batch)


def insert_votes(model, target_field, targets, counts, voter_ids, rng):
    rows = (
        model(
            **{target_field: target.pk},
            user_id=user_id,
            value=VoteValue.LIKE if rng.random() < 0.75 else VoteValue.DISLIKE,
        )
        for index, target in enumerate(targets)
        for user_id in rng.sample(voter_ids, counts[index % len(counts)])
    )
    for _ in bulk_insert(model, rows):
        pass


class Command(BaseCommand):
    help = "Добавляет тестовые данные. Коэффициент ratio задаёт число новых пользователей."

    def add_arguments(self, parser):
        parser.add_argument("ratio", type=int)

    # Django в режиме DEBUG сохраняет полные SQL-запросы с данными пакетов в памяти.
    @override_settings(DEBUG=False)
    @transaction.atomic
    def handle(self, *args, ratio, **options):
        if ratio < 1:
            raise CommandError("ratio должно быть положительным целым числом.")

        user_model = get_user_model()
        voter_ids = []
        if ratio == 1:
            existing_user = (
                user_model.objects.select_for_update().order_by("pk")
                .values_list("pk", flat=True).first()
            )
            if existing_user is None:
                raise CommandError(
                    "В пустой базе используйте ratio от 2: один пользователь может "
                    "оставить максимум 110 оценок на 10 вопросах и 100 ответах."
                )
            voter_ids.append(existing_user)

        fake = Faker("ru_RU")
        rng = Random()
        run_id = uuid4().hex[:16]
        password = make_password(None)
        users = list(bulk_insert(
            user_model,
            (
                user_model(
                    username=f"demo_{run_id}_{index}",
                    first_name=fake.first_name()[:150],
                    last_name=fake.last_name()[:150],
                    email=f"demo_{run_id}_{index}@example.com",
                    password=password,
                )
                for index in range(ratio)
            ),
        ))
        user_ids = [user.pk for user in users]
        voter_ids.extend(user_ids)
        for _ in bulk_insert(
            Profile,
            (Profile(user_id=user.pk, display_name=user.get_full_name()[:50]) for user in users),
        ):
            pass

        tags = (
            Tag(
                name=f"{TOPICS[index % len(TOPICS)]} {index + 1} ({run_id})",
                slug=f"{TOPICS[index % len(TOPICS)].lower()}-{run_id}-{index + 1}",
            )
            for index in range(ratio)
        )
        tag_ids = [tag.pk for tag in bulk_insert(Tag, tags)]
        question_tag = Question.tags.through
        tag_count = min(2, ratio)

        # Переиспользуем рыбу, чтобы миллионы вставок не требовали миллионов вызовов Faker.
        descriptions = [fake.paragraph(nb_sentences=3) for _ in range(1000)]
        replies = [fake.paragraph(nb_sentences=2) for _ in range(1000)]
        now = timezone.now()
        total_questions = ratio * 10

        # В каждом блоке из 10 вопросов и 100 ответов ровно 200 оценок.
        question_votes = (0, 1, 2, 3, 4) if len(voter_ids) >= 4 else (2,)
        answer_votes = (
            (0, 0, 1, 1, 2, 2, 2, 3, 3, 4)
            if len(voter_ids) >= 4
            else (1, 1, 2, 2, 2, 2, 2, 2, 2, 2)
        )

        for start in range(0, total_questions, QUESTION_BATCH_SIZE):
            stop = min(start + QUESTION_BATCH_SIZE, total_questions)
            questions = Question.objects.bulk_create([
                Question(
                    title=rng.choice(QUESTION_TITLES).format(topic=rng.choice(TOPICS)),
                    text=rng.choice(descriptions),
                    author_id=rng.choice(user_ids),
                    created_at=now - timedelta(seconds=rng.randrange(3600, 365 * 86400)),
                )
                for _ in range(start, stop)
            ])
            for _ in bulk_insert(
                question_tag,
                (
                    question_tag(question_id=question.pk, tag_id=tag_id)
                    for question in questions
                    for tag_id in rng.sample(tag_ids, tag_count)
                ),
            ):
                pass

            # Чередуем 6 и 14 ответов, чтобы на части вопросов была вторая страница.
            answers = list(bulk_insert(
                Answer,
                (
                    Answer(
                        question_id=question.pk,
                        author_id=rng.choice(user_ids),
                        text=rng.choice(replies),
                        is_correct=position == 0 and index % 3 == 0,
                        created_at=question.created_at + timedelta(seconds=rng.randrange(3600)),
                    )
                    for index, question in enumerate(questions, start)
                    for position in range(6 if index % 2 == 0 else 14)
                ),
            ))
            insert_votes(QuestionLike, "question_id", questions, question_votes, voter_ids, rng)
            insert_votes(AnswerLike, "answer_id", answers, answer_votes, voter_ids, rng)
            if stop % 10000 == 0 and options["verbosity"]:
                self.stdout.write(f"Обработано вопросов: {stop} из {total_questions}.")

        return self.style.SUCCESS(
            f"Добавлено: {ratio} пользователей и профилей, {ratio} тегов, "
            f"{total_questions} вопросов, {ratio * 100} ответов, {ratio * 200} оценок."
        )