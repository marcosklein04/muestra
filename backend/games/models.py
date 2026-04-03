import uuid
import secrets
from django.db import models


class Game(models.Model):
    SLUG_PUZZLE_MUNDIAL = "puzzle-mundial"
    SLUG_TRIVIA_MUNDIAL_FOTOS = "trivia-mundial-fotos"
    SLUG_ARQUERO = "el-del-arquero"

    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    cover_image = models.ImageField(upload_to="games/covers/", blank=True)
    is_enabled = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "games_game"
        verbose_name = "Juego"
        verbose_name_plural = "Juegos"
        ordering = ["sort_order", "name"]

    def __str__(self) -> str:
        return self.name

    def runner_path(self) -> str:
        return f"/jugar/{self.slug}/"


class GameConfig(models.Model):
    """
    JSON configuration for a game: branding, texts, rules, visual, content.
    One record per game — edited by the operator via Django admin.
    """
    game = models.OneToOneField(
        Game,
        on_delete=models.CASCADE,
        related_name="config",
    )
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Configuración completa del juego en formato JSON. "
            "Secciones: branding, texts, rules, visual, watermark, content."
        ),
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "games_gameconfig"
        verbose_name = "Configuración de juego"
        verbose_name_plural = "Configuraciones de juegos"

    def __str__(self) -> str:
        return f"Config → {self.game.name}"


class TriviaQuestion(models.Model):
    """
    Question for Trivia Mundial Fotos. Managed via Django admin.
    """
    game = models.ForeignKey(
        Game,
        on_delete=models.CASCADE,
        related_name="trivia_questions",
        limit_choices_to={"slug": Game.SLUG_TRIVIA_MUNDIAL_FOTOS},
    )
    prompt = models.CharField(max_length=500, verbose_name="Pregunta")
    question_image_url = models.URLField(
        blank=True,
        verbose_name="URL de imagen de la pregunta",
        help_text="Imagen que se muestra junto a la pregunta (opcional)",
    )
    sort_order = models.PositiveIntegerField(default=0, verbose_name="Orden")
    is_active = models.BooleanField(default=True, verbose_name="Activa")

    class Meta:
        db_table = "games_triviaquestion"
        verbose_name = "Pregunta de trivia"
        verbose_name_plural = "Preguntas de trivia"
        ordering = ["sort_order", "id"]

    def __str__(self) -> str:
        return self.prompt[:80]

    def to_api_dict(self) -> dict:
        answers = list(self.answers.all().order_by("sort_order", "id"))
        correct = next((a for a in answers if a.is_correct), answers[0] if answers else None)
        return {
            "id": f"q-{self.pk}",
            "prompt": self.prompt,
            "questionImageUrl": self.question_image_url,
            "answers": [a.to_api_dict() for a in answers],
            "correctAnswerId": f"a-{correct.pk}" if correct else "",
        }


class TriviaAnswer(models.Model):
    question = models.ForeignKey(
        TriviaQuestion,
        on_delete=models.CASCADE,
        related_name="answers",
    )
    label = models.CharField(max_length=200, verbose_name="Texto de la respuesta")
    image_url = models.URLField(
        blank=True,
        verbose_name="URL de imagen (opcional)",
    )
    is_correct = models.BooleanField(default=False, verbose_name="Es la correcta")
    sort_order = models.PositiveIntegerField(default=0, verbose_name="Orden")

    class Meta:
        db_table = "games_triviaanswer"
        verbose_name = "Respuesta"
        verbose_name_plural = "Respuestas"
        ordering = ["sort_order", "id"]

    def __str__(self) -> str:
        marker = " ✓" if self.is_correct else ""
        return f"{self.label}{marker}"

    def to_api_dict(self) -> dict:
        return {
            "id": f"a-{self.pk}",
            "label": self.label,
            "imageUrl": self.image_url,
        }


class PlaySession(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Activa"
        FINISHED = "finished", "Finalizada"
        ERROR = "error", "Error"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="sessions")
    anon_token = models.CharField(max_length=64, db_index=True)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    result = models.JSONField(default=dict, blank=True)
    client_state = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "games_playsession"
        verbose_name = "Sesión de juego"
        verbose_name_plural = "Sesiones de juego"
        ordering = ["-started_at"]

    def __str__(self) -> str:
        return f"{self.game.slug} — {self.status} — {self.started_at:%Y-%m-%d %H:%M}"

    @staticmethod
    def generate_token() -> str:
        return secrets.token_hex(32)
