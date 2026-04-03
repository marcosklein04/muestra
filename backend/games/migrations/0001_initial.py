import uuid
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Game",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(unique=True)),
                ("name", models.CharField(max_length=100)),
                ("description", models.TextField(blank=True)),
                ("cover_image_url", models.URLField(blank=True, default="")),
                ("is_enabled", models.BooleanField(default=True)),
                ("is_featured", models.BooleanField(default=False)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Juego",
                "verbose_name_plural": "Juegos",
                "db_table": "games_game",
                "ordering": ["sort_order", "name"],
            },
        ),
        migrations.CreateModel(
            name="GameConfig",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "game",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="config",
                        to="games.game",
                    ),
                ),
                (
                    "config",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Configuración completa del juego en formato JSON.",
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Configuración de juego",
                "verbose_name_plural": "Configuraciones de juegos",
                "db_table": "games_gameconfig",
            },
        ),
        migrations.CreateModel(
            name="TriviaQuestion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "game",
                    models.ForeignKey(
                        limit_choices_to={"slug": "trivia-mundial-fotos"},
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="trivia_questions",
                        to="games.game",
                    ),
                ),
                ("prompt", models.CharField(max_length=500, verbose_name="Pregunta")),
                ("question_image_url", models.URLField(blank=True, verbose_name="URL de imagen de la pregunta")),
                ("sort_order", models.PositiveIntegerField(default=0, verbose_name="Orden")),
                ("is_active", models.BooleanField(default=True, verbose_name="Activa")),
            ],
            options={
                "verbose_name": "Pregunta de trivia",
                "verbose_name_plural": "Preguntas de trivia",
                "db_table": "games_triviaquestion",
                "ordering": ["sort_order", "id"],
            },
        ),
        migrations.CreateModel(
            name="TriviaAnswer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "question",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="answers",
                        to="games.triviaquestion",
                    ),
                ),
                ("label", models.CharField(max_length=200, verbose_name="Texto de la respuesta")),
                ("image_url", models.URLField(blank=True, verbose_name="URL de imagen (opcional)")),
                ("is_correct", models.BooleanField(default=False, verbose_name="Es la correcta")),
                ("sort_order", models.PositiveIntegerField(default=0, verbose_name="Orden")),
            ],
            options={
                "verbose_name": "Respuesta",
                "verbose_name_plural": "Respuestas",
                "db_table": "games_triviaanswer",
                "ordering": ["sort_order", "id"],
            },
        ),
        migrations.CreateModel(
            name="PlaySession",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "game",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sessions",
                        to="games.game",
                    ),
                ),
                ("anon_token", models.CharField(db_index=True, max_length=64)),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("ended_at", models.DateTimeField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[("active", "Activa"), ("finished", "Finalizada"), ("error", "Error")],
                        default="active",
                        max_length=16,
                    ),
                ),
                ("result", models.JSONField(blank=True, default=dict)),
                ("client_state", models.JSONField(blank=True, default=dict)),
            ],
            options={
                "verbose_name": "Sesión de juego",
                "verbose_name_plural": "Sesiones de juego",
                "db_table": "games_playsession",
                "ordering": ["-started_at"],
            },
        ),
    ]
