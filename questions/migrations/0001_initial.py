import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True, verbose_name='название')),
                ('slug', models.SlugField(max_length=70, unique=True, verbose_name='адрес тега')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='дата создания')),
            ],
            options={
                'verbose_name': 'тег',
                'verbose_name_plural': 'теги',
                'ordering': ('name',),
            },
        ),
        migrations.CreateModel(
            name='Question',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200, verbose_name='заголовок')),
                ('text', models.TextField(verbose_name='текст')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='дата создания')),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='questions', to=settings.AUTH_USER_MODEL, verbose_name='автор')),
                ('tags', models.ManyToManyField(blank=True, related_name='questions', to='questions.tag', verbose_name='теги')),
            ],
            options={
                'verbose_name': 'вопрос',
                'verbose_name_plural': 'вопросы',
            },
        ),
        migrations.CreateModel(
            name='Answer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.TextField(verbose_name='текст')),
                ('is_correct', models.BooleanField(default=False, verbose_name='правильный ответ')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='дата создания')),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='answers', to=settings.AUTH_USER_MODEL, verbose_name='автор')),
                ('question', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='answers', to='questions.question', verbose_name='вопрос')),
            ],
            options={
                'verbose_name': 'ответ',
                'verbose_name_plural': 'ответы',
            },
        ),
        migrations.CreateModel(
            name='QuestionLike',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.SmallIntegerField(choices=[(1, 'Нравится'), (-1, 'Не нравится')], default=1, verbose_name='оценка')),
                ('question', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='likes', to='questions.question', verbose_name='вопрос')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='question_likes', to=settings.AUTH_USER_MODEL, verbose_name='пользователь')),
            ],
            options={
                'verbose_name': 'оценка вопроса',
                'verbose_name_plural': 'оценки вопросов',
            },
        ),
        migrations.CreateModel(
            name='AnswerLike',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.SmallIntegerField(choices=[(1, 'Нравится'), (-1, 'Не нравится')], default=1, verbose_name='оценка')),
                ('answer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='likes', to='questions.answer', verbose_name='ответ')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='answer_likes', to=settings.AUTH_USER_MODEL, verbose_name='пользователь')),
            ],
            options={
                'verbose_name': 'оценка ответа',
                'verbose_name_plural': 'оценки ответов',
                'constraints': [models.CheckConstraint(condition=models.Q(('value__in', [1, -1])), name='answer_vote_value')],
                'unique_together': {('answer', 'user')},
            },
        ),
        migrations.AddIndex(
            model_name='answer',
            index=models.Index(fields=['question', '-is_correct', 'created_at', 'id'], name='answer_order_idx'),
        ),
        migrations.AddConstraint(
            model_name='questionlike',
            constraint=models.CheckConstraint(condition=models.Q(('value__in', [1, -1])), name='question_vote_value'),
        ),
        migrations.AlterUniqueTogether(
            name='questionlike',
            unique_together={('question', 'user')},
        ),
        migrations.AddIndex(
            model_name='question',
            index=models.Index(fields=['-created_at', '-id'], name='question_newest_idx'),
        ),
    ]
