import tempfile

from django import forms
from django.core.management import call_command
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test.utils import override_settings

from .forms import GameConfigAdminForm, GameConfigStructuredForm
from .models import Game, GameConfig, TriviaAnswer, TriviaQuestion
from .presets import get_default_config


def build_form_data(form: GameConfigAdminForm) -> dict:
    data = {}
    for name, field in form.fields.items():
        initial = form.initial.get(name, field.initial)
        if name == "game":
            value = initial.pk if isinstance(initial, Game) else initial
            if value:
                data[name] = value
            continue

        if isinstance(field, forms.BooleanField):
            if initial:
                data[name] = "on"
            continue

        data[name] = "" if initial is None else initial
    return data


class GameConfigAdminFormTests(TestCase):
    def create_game_config(self, slug: str, name: str) -> GameConfig:
        game = Game.objects.create(slug=slug, name=name)
        return GameConfig.objects.create(game=game, config=get_default_config(slug))

    def test_puzzle_form_exposes_structured_fields_and_preserves_unknown_keys(self):
        config = self.create_game_config(Game.SLUG_PUZZLE_MUNDIAL, "Puzzle Mundial")
        config.config["advanced"] = {"keep_me": True}
        config.save(update_fields=["config"])

        form = GameConfigAdminForm(instance=config)

        self.assertTrue(form.uses_structured_editor)
        self.assertIn("branding__logo_url", form.fields)
        self.assertIn("content__puzzle_image_url", form.fields)
        self.assertTrue(form.fields["config"].widget.is_hidden)

        data = build_form_data(form)
        data["visual__accent_color"] = "#ff0055"
        data["content__puzzle_image_url"] = "https://example.com/puzzle.jpg"

        bound_form = GameConfigAdminForm(data=data, instance=config)
        self.assertTrue(bound_form.is_valid(), bound_form.errors)

        saved = bound_form.save()
        self.assertEqual(saved.config["visual"]["accent_color"], "#ff0055")
        self.assertEqual(saved.config["content"]["puzzle_image_url"], "https://example.com/puzzle.jpg")
        self.assertEqual(saved.config["advanced"]["keep_me"], True)

    def test_trivia_form_uses_trivia_specific_fields(self):
        config = self.create_game_config(Game.SLUG_TRIVIA_MUNDIAL_FOTOS, "Trivia")
        form = GameConfigAdminForm(instance=config)

        self.assertIn("rules__points_per_correct", form.fields)
        self.assertIn("rules__max_questions", form.fields)
        self.assertNotIn("content__puzzle_image_url", form.fields)
        self.assertNotIn("texts__play_again_button", form.fields)


class SeedGamesCommandTests(TestCase):
    def test_seed_games_can_run_twice_without_duplication(self):
        call_command("seed_games")
        call_command("seed_games")

        self.assertEqual(Game.objects.count(), 3)
        self.assertEqual(GameConfig.objects.count(), 3)
        self.assertEqual(TriviaQuestion.objects.count(), 5)
        self.assertEqual(TriviaAnswer.objects.count(), 15)


class CustomizerViewsTests(TestCase):
    def create_game_config(self, slug: str, name: str) -> GameConfig:
        game = Game.objects.create(slug=slug, name=name)
        return GameConfig.objects.create(game=game, config=get_default_config(slug))

    def build_structured_payload(self, slug: str, current_config: dict) -> dict:
        form = GameConfigStructuredForm(slug, current_config=current_config)
        payload = {}
        for name, field in form.fields.items():
            initial = form.initial.get(name, field.initial)
            if isinstance(field, forms.BooleanField):
                if initial:
                    payload[name] = "on"
                continue
            payload[name] = "" if initial is None else initial
        return payload

    def test_customizer_save_updates_game_config(self):
        config = self.create_game_config(Game.SLUG_PUZZLE_MUNDIAL, "Puzzle Mundial")
        payload = self.build_structured_payload(config.game.slug, config.config)
        payload["texts__welcome_title"] = "MI PUZZLE"
        payload["rules__grid_size"] = "5"
        payload["content__puzzle_image_url"] = "https://example.com/custom.jpg"

        response = self.client.post(
            f"/api/personalizacion/{config.game.slug}/guardar/",
            data=payload,
        )

        self.assertEqual(response.status_code, 200)
        config.refresh_from_db()
        self.assertEqual(config.config["texts"]["welcome_title"], "MI PUZZLE")
        self.assertEqual(config.config["rules"]["grid_size"], 5)
        self.assertEqual(config.config["content"]["puzzle_image_url"], "https://example.com/custom.jpg")

    def test_customizer_save_accepts_existing_media_paths_and_new_uploads(self):
        config = self.create_game_config(Game.SLUG_PUZZLE_MUNDIAL, "Puzzle Mundial")
        config.config["content"]["puzzle_image_url"] = "/media/customizer/puzzle-mundial/existing.heic"
        config.save(update_fields=["config"])

        payload = self.build_structured_payload(config.game.slug, config.config)
        payload["texts__welcome_title"] = "PUZZLE CON FOTO"

        upload = SimpleUploadedFile(
            "cover.png",
            b"fake-image-bytes",
            content_type="image/png",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            with override_settings(MEDIA_ROOT=tmpdir, MEDIA_URL="/media/"):
                response = self.client.post(
                    f"/api/personalizacion/{config.game.slug}/guardar/",
                    data={**payload, "branding__welcome_image_url__file": upload},
                )

        self.assertEqual(response.status_code, 200, response.content)
        config.refresh_from_db()
        self.assertEqual(config.config["texts"]["welcome_title"], "PUZZLE CON FOTO")
        self.assertEqual(
            config.config["content"]["puzzle_image_url"],
            "/media/customizer/puzzle-mundial/existing.heic",
        )
        self.assertTrue(config.config["branding"]["welcome_image_url"].startswith("/media/customizer/puzzle-mundial/"))

    def test_trivia_customizer_save_updates_question_bank(self):
        config = self.create_game_config(Game.SLUG_TRIVIA_MUNDIAL_FOTOS, "Trivia Mundial Fotos")
        payload = self.build_structured_payload(config.game.slug, config.config)
        payload["texts__welcome_title"] = "TRIVIA EDITADA"
        payload["rules__max_questions"] = "2"
        payload["trivia_question_count"] = "2"

        payload["trivia_questions__0__prompt"] = "¿Quién levantó la copa en 2022?"
        payload["trivia_questions__0__response_type"] = "text"
        payload["trivia_questions__0__correct_answer"] = "1"
        payload["trivia_questions__0__answers__0__label"] = "Mbappé"
        payload["trivia_questions__0__answers__1__label"] = "Messi"
        payload["trivia_questions__0__answers__2__label"] = "Modric"
        payload["trivia_questions__0__answers__3__label"] = "Neymar"

        payload["trivia_questions__1__prompt"] = "¿Cuántos mundiales tiene Argentina?"
        payload["trivia_questions__1__response_type"] = "text"
        payload["trivia_questions__1__correct_answer"] = "2"
        payload["trivia_questions__1__answers__0__label"] = "2"
        payload["trivia_questions__1__answers__1__label"] = "4"
        payload["trivia_questions__1__answers__2__label"] = "3"
        payload["trivia_questions__1__answers__3__label"] = "5"

        response = self.client.post(
            f"/api/personalizacion/{config.game.slug}/guardar/",
            data=payload,
        )

        self.assertEqual(response.status_code, 200, response.content)
        config.refresh_from_db()
        self.assertEqual(config.config["texts"]["welcome_title"], "TRIVIA EDITADA")
        self.assertEqual(config.config["rules"]["max_questions"], 2)

        questions = list(
            TriviaQuestion.objects
            .filter(game=config.game)
            .prefetch_related("answers")
            .order_by("sort_order", "id")
        )
        self.assertEqual(len(questions), 2)
        self.assertEqual(questions[0].prompt, "¿Quién levantó la copa en 2022?")
        self.assertEqual(questions[0].answers.count(), 4)
        self.assertEqual(
            questions[0].answers.get(is_correct=True).label,
            "Messi",
        )
        self.assertEqual(
            questions[1].answers.get(is_correct=True).label,
            "3",
        )
