from copy import deepcopy


GAME_PRESETS = [
    {
        "slug": "puzzle-mundial",
        "name": "Puzzle Mundial",
        "description": "Arma la imagen del mundial pieza por pieza.",
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
                "welcome_subtitle": "Arma la imagen del mundial pieza por pieza.",
                "cta_button": "Empezar puzzle",
                "completion_title": "Golazo",
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
        "description": "Reconoce momentos y protagonistas del Mundial en una trivia visual rapida.",
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
                "welcome_subtitle": "Reconoce momentos y protagonistas del Mundial en una trivia visual rapida.",
                "cta_button": "Comenzar partido",
                "completion_title": "FINAL DEL PARTIDO",
                "completion_subtitle": "Repasa tu marcador y juga de nuevo.",
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
                "chip_bg_color": "rgba(18, 50, 74, 0.84)",
                "muted_text_color": "rgba(248, 252, 255, 0.72)",
            },
            "watermark": {
                "enabled": False,
                "color": "#8ad8ff",
                "opacity": 0.2,
                "font_size": 96,
            },
            "content": {
                "question_pack_image_url": "",
            },
        },
    },
    {
        "slug": "el-del-arquero",
        "name": "El del Arquero",
        "description": "Move al arquero y ataja todos los remates.",
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
                "welcome_subtitle": "Move al arquero de lado a lado y ataja todos los remates.",
                "cta_button": "Tocar para jugar",
                "completion_title": "FIN DEL JUEGO",
                "completion_subtitle": "Tus reflejos definieron el resultado.",
                "instructions_text": "Arrastra al portero a izquierda y derecha para parar los balones.",
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
        "prompt": "En que ano Argentina gano su tercer Mundial de Futbol?",
        "question_image_url": "",
        "sort_order": 1,
        "answers": [
            {"label": "2018", "is_correct": False, "sort_order": 1},
            {"label": "2022", "is_correct": True, "sort_order": 2},
            {"label": "2014", "is_correct": False, "sort_order": 3},
        ],
    },
    {
        "prompt": "Cuantos goles marco Messi en el Mundial de Qatar 2022?",
        "question_image_url": "",
        "sort_order": 2,
        "answers": [
            {"label": "5 goles", "is_correct": False, "sort_order": 1},
            {"label": "7 goles", "is_correct": True, "sort_order": 2},
            {"label": "8 goles", "is_correct": False, "sort_order": 3},
        ],
    },
    {
        "prompt": "Quien fue el arquero titular de Argentina en la final del Mundial 2022?",
        "question_image_url": "",
        "sort_order": 3,
        "answers": [
            {"label": "Franco Armani", "is_correct": False, "sort_order": 1},
            {"label": "Emiliano Martinez", "is_correct": True, "sort_order": 2},
            {"label": "Geronimo Rulli", "is_correct": False, "sort_order": 3},
        ],
    },
    {
        "prompt": "Contra que seleccion jugo Argentina la final del Mundial 2022?",
        "question_image_url": "",
        "sort_order": 4,
        "answers": [
            {"label": "Brasil", "is_correct": False, "sort_order": 1},
            {"label": "Francia", "is_correct": True, "sort_order": 2},
            {"label": "Alemania", "is_correct": False, "sort_order": 3},
        ],
    },
    {
        "prompt": "Cuantos Mundiales gano Argentina en total?",
        "question_image_url": "",
        "sort_order": 5,
        "answers": [
            {"label": "2", "is_correct": False, "sort_order": 1},
            {"label": "3", "is_correct": True, "sort_order": 2},
            {"label": "4", "is_correct": False, "sort_order": 3},
        ],
    },
]


GAME_PRESETS_BY_SLUG = {preset["slug"]: preset for preset in GAME_PRESETS}


def get_default_config(slug: str) -> dict:
    preset = GAME_PRESETS_BY_SLUG.get(slug)
    if not preset:
        return {
            "branding": {},
            "texts": {},
            "rules": {},
            "visual": {},
            "watermark": {},
            "content": {},
        }
    return deepcopy(preset["config"])
