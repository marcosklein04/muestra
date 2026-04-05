"""
Seed command: creates the 3 games with default configs and sample trivia questions.
Run: python manage.py seed_games
"""
from copy import deepcopy

from django.core.management.base import BaseCommand

from games.models import Game, GameConfig, TriviaQuestion, TriviaAnswer
from games.presets import GAME_PRESETS, TRIVIA_QUESTIONS


class Command(BaseCommand):
    help = "Seed the 3 games with default configs and sample trivia questions"

    def handle(self, *args, **options):
        for preset in GAME_PRESETS:
            game_data = deepcopy(preset)
            config_data = game_data.pop("config")
            game, created = Game.objects.update_or_create(
                slug=game_data["slug"],
                defaults=game_data,
            )
            GameConfig.objects.update_or_create(
                game=game,
                defaults={"config": config_data},
            )
            status = "creado" if created else "actualizado"
            self.stdout.write(self.style.SUCCESS(f"Juego {status}: {game.name}"))

        trivia_game = Game.objects.filter(slug=Game.SLUG_TRIVIA_MUNDIAL_FOTOS).first()
        if trivia_game and not TriviaQuestion.objects.filter(game=trivia_game).exists():
            for preset in TRIVIA_QUESTIONS:
                question_data = deepcopy(preset)
                answers_data = question_data.pop("answers")
                question = TriviaQuestion.objects.create(game=trivia_game, **question_data)
                for answer_data in answers_data:
                    TriviaAnswer.objects.create(question=question, **answer_data)
            self.stdout.write(self.style.SUCCESS(
                f"Preguntas de trivia creadas: {len(TRIVIA_QUESTIONS)}"
            ))
        else:
            self.stdout.write("Preguntas de trivia: ya existen, sin cambios.")

        self.stdout.write(self.style.SUCCESS("Seed completado."))
