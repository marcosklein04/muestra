"""
Seed command: creates the 3 games with default configs and sample trivia questions.
Run: python manage.py seed_games
"""
from django.core.management.base import BaseCommand
from games.models import Game, GameConfig, TriviaQuestion, TriviaAnswer


GAMES = [
    {
        "slug": "puzzle-mundial",
        "name": "Puzzle Mundial",
        "description": "Armá la imagen del mundial pieza por pieza.",
        "sort_order": 1,
        "is_featured": True,
        "config": {
            "branding": {
                "primary_color": "#00f5e9",
                "secondary_color": "#081a2b",
                "logo_url": "",
                "background_url": "",
                "welcome_image_url": "",
                "watermark_text": "MUESTRA",
            },
            "texts": {
                "welcome_title": "PUZZLE MUNDIAL",
                "welcome_subtitle": "Armá la imagen del mundial pieza por pieza.",
                "cta_button": "Empezar puzzle",
                "completion_title": "¡Golazo!",
                "completion_subtitle": "Completaste el puzzle y cerraste la jugada.",
            },
            "rules": {
                "show_timer": True,
                "timer_seconds": 180,
                "show_moves": True,
                "show_progress": True,
                "grid_size": 3,
            },
            "visual": {
                "screen_background_color": "#04121f",
                "panel_bg_color": "rgba(8, 26, 43, 0.84)",
                "panel_border_color": "#1b6888",
                "text_color": "#f4fbff",
                "accent_color": "#00f5e9",
                "success_color": "#8ee05f",
            },
            "watermark": {
                "enabled": False,
                "color": "#00f5e9",
                "opacity": 0.2,
                "font_size": 96,
            },
            "content": {
                "puzzle_image_url": "",
            },
        },
    },
    {
        "slug": "trivia-mundial-fotos",
        "name": "Trivia Mundial Fotos",
        "description": "Reconocé momentos y protagonistas del Mundial en una trivia visual rápida.",
        "sort_order": 2,
        "is_featured": True,
        "config": {
            "branding": {
                "primary_color": "#8ad8ff",
                "secondary_color": "#081a2b",
                "logo_url": "",
                "background_url": "",
                "welcome_image_url": "",
                "watermark_text": "MUESTRA",
            },
            "texts": {
                "welcome_title": "TRIVIA MUNDIAL FOTOS",
                "welcome_subtitle": "Reconocé momentos y protagonistas del Mundial en una trivia visual rápida.",
                "cta_button": "Comenzar partido",
                "completion_title": "FINAL DEL PARTIDO",
                "completion_subtitle": "Repasá tu marcador y jugá de nuevo.",
            },
            "rules": {
                "show_timer": True,
                "timer_seconds": 15,
                "points_per_correct": 100,
                "max_questions": 5,
            },
            "visual": {
                "screen_background_color": "#050e1a",
                "panel_bg_color": "rgba(7, 20, 36, 0.82)",
                "panel_border_color": "#1d5f80",
                "text_color": "#f8fcff",
                "accent_color": "#8ad8ff",
                "success_color": "#44e3a2",
                "danger_color": "#ff6b7a",
            },
            "watermark": {
                "enabled": False,
                "color": "#8ad8ff",
                "opacity": 0.2,
                "font_size": 96,
            },
            "content": {},
        },
    },
    {
        "slug": "el-del-arquero",
        "name": "El del Arquero",
        "description": "Mové al arquero y atajá todos los remates.",
        "sort_order": 3,
        "is_featured": True,
        "config": {
            "branding": {
                "primary_color": "#f7c948",
                "secondary_color": "#0f3d26",
                "logo_url": "",
                "background_url": "",
                "welcome_image_url": "",
                "watermark_text": "MUESTRA",
                "ball_image_url": "",
                "bonus_ball_image_url": "",
                "penalty_ball_image_url": "",
            },
            "texts": {
                "welcome_title": "EL DEL ARQUERO",
                "welcome_subtitle": "Mové al arquero de lado a lado y atajá todos los remates.",
                "cta_button": "Tocar para jugar",
                "completion_title": "FIN DEL JUEGO",
                "completion_subtitle": "Tus reflejos definieron el resultado.",
                "instructions_text": "Arrastrá al portero a izquierda y derecha para parar los balones.",
                "play_again_button": "Jugar de nuevo",
            },
            "rules": {
                "show_timer": True,
                "timer_seconds": 60,
                "show_score": True,
                "show_saves": True,
                "goalkeeper_width": 120,
                "points_per_save": 10,
                "ball_speed_min": 4,
                "ball_speed_max": 8,
                "spawn_interval_ms": 800,
                "bonus_ball_enabled": True,
                "bonus_points": 25,
                "bonus_ball_spawn_chance": 12,
                "penalty_ball_enabled": False,
                "penalty_points": 10,
                "penalty_ball_spawn_chance": 18,
            },
            "visual": {
                "screen_background_color": "#102a1a",
                "field_green_color": "#2b8a3e",
                "field_dark_color": "#0b3b23",
                "line_color": "#f4f6f2",
                "goalkeeper_jersey_color": "#2563eb",
                "goalkeeper_detail_color": "#3b82f6",
                "goalkeeper_glove_color": "#22c55e",
                "accent_color": "#f7c948",
            },
            "watermark": {
                "enabled": False,
                "color": "#f7c948",
                "opacity": 0.18,
                "font_size": 96,
            },
            "content": {
                "sponsor_top_left": "",
                "sponsor_top_right": "",
                "sponsor_bottom": "",
            },
        },
    },
]

TRIVIA_QUESTIONS = [
    {
        "prompt": "¿En qué año Argentina ganó su tercer Mundial de Fútbol?",
        "question_image_url": "",
        "sort_order": 1,
        "answers": [
            {"label": "2018", "is_correct": False, "sort_order": 1},
            {"label": "2022", "is_correct": True, "sort_order": 2},
            {"label": "2014", "is_correct": False, "sort_order": 3},
        ],
    },
    {
        "prompt": "¿Cuántos goles marcó Messi en el Mundial de Qatar 2022?",
        "question_image_url": "",
        "sort_order": 2,
        "answers": [
            {"label": "5 goles", "is_correct": False, "sort_order": 1},
            {"label": "7 goles", "is_correct": True, "sort_order": 2},
            {"label": "8 goles", "is_correct": False, "sort_order": 3},
        ],
    },
    {
        "prompt": "¿Quién fue el arquero titular de Argentina en la final del Mundial 2022?",
        "question_image_url": "",
        "sort_order": 3,
        "answers": [
            {"label": "Franco Armani", "is_correct": False, "sort_order": 1},
            {"label": "Emiliano Martínez", "is_correct": True, "sort_order": 2},
            {"label": "Gerónimo Rulli", "is_correct": False, "sort_order": 3},
        ],
    },
    {
        "prompt": "¿Contra qué selección jugó Argentina la final del Mundial 2022?",
        "question_image_url": "",
        "sort_order": 4,
        "answers": [
            {"label": "Brasil", "is_correct": False, "sort_order": 1},
            {"label": "Francia", "is_correct": True, "sort_order": 2},
            {"label": "Alemania", "is_correct": False, "sort_order": 3},
        ],
    },
    {
        "prompt": "¿Cuántos Mundiales ganó Argentina en total?",
        "question_image_url": "",
        "sort_order": 5,
        "answers": [
            {"label": "2", "is_correct": False, "sort_order": 1},
            {"label": "3", "is_correct": True, "sort_order": 2},
            {"label": "4", "is_correct": False, "sort_order": 3},
        ],
    },
]


class Command(BaseCommand):
    help = "Seed the 3 games with default configs and sample trivia questions"

    def handle(self, *args, **options):
        for game_data in GAMES:
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

        # Seed trivia questions (only if none exist yet)
        trivia_game = Game.objects.filter(slug="trivia-mundial-fotos").first()
        if trivia_game and not TriviaQuestion.objects.filter(game=trivia_game).exists():
            for q_data in TRIVIA_QUESTIONS:
                answers_data = q_data.pop("answers")
                question = TriviaQuestion.objects.create(game=trivia_game, **q_data)
                for a_data in answers_data:
                    TriviaAnswer.objects.create(question=question, **a_data)
            self.stdout.write(self.style.SUCCESS(
                f"Preguntas de trivia creadas: {len(TRIVIA_QUESTIONS)}"
            ))
        else:
            self.stdout.write("Preguntas de trivia: ya existen, sin cambios.")

        self.stdout.write(self.style.SUCCESS("Seed completado."))
