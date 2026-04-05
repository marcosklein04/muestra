from copy import deepcopy
from dataclasses import dataclass, field as dataclass_field

from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator

from .models import Game, GameConfig
from .presets import get_default_config


SECTION_ORDER = ("branding", "texts", "rules", "visual", "watermark", "content")
SECTION_TITLES = {
    "branding": "Branding",
    "texts": "Textos",
    "rules": "Reglas",
    "visual": "Visual",
    "watermark": "Marca de agua",
    "content": "Contenido",
}
SECTION_DESCRIPTIONS = {
    "branding": "Logo, fondos, imagenes de bienvenida y colores base de la marca.",
    "texts": "Titulos, subtitulos, botones y mensajes de cierre del juego.",
    "rules": "Mecanicas y numeros del gameplay que cambian la experiencia.",
    "visual": "Colores, paneles y estilos visuales usados dentro del runner.",
    "watermark": "Configuracion opcional para mostrar texto de prueba sobre el juego.",
    "content": "Activos y contenido especifico del juego.",
}


@dataclass(frozen=True)
class FieldSpec:
    section: str
    key: str
    label: str
    field_class: type[forms.Field] = forms.CharField
    kwargs: dict = dataclass_field(default_factory=dict)

    @property
    def name(self) -> str:
        return f"{self.section}__{self.key}"

    def build_field(self) -> forms.Field:
        return self.field_class(label=self.label, **self.kwargs)


class AssetURLField(forms.CharField):
    default_validators = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._url_validator = URLValidator(schemes=["http", "https"])

    def clean(self, value):
        value = super().clean(value)
        if not value:
            return ""
        if value.startswith("/"):
            return value
        try:
            self._url_validator(value)
        except ValidationError as exc:
            raise forms.ValidationError("Introduzca una URL válida.") from exc
        return value


def text_spec(section: str, key: str, label: str, *, multiline: bool = False, help_text: str = "") -> FieldSpec:
    widget = forms.Textarea(attrs={"rows": 3}) if multiline else forms.TextInput()
    return FieldSpec(
        section=section,
        key=key,
        label=label,
        kwargs={"required": False, "help_text": help_text, "widget": widget},
    )


def url_spec(section: str, key: str, label: str, *, help_text: str = "") -> FieldSpec:
    return FieldSpec(
        section=section,
        key=key,
        label=label,
        field_class=AssetURLField,
        kwargs={"required": False, "help_text": help_text},
    )


def int_spec(section: str, key: str, label: str, *, min_value: int | None = None, max_value: int | None = None, help_text: str = "") -> FieldSpec:
    return FieldSpec(
        section=section,
        key=key,
        label=label,
        field_class=forms.IntegerField,
        kwargs={"required": False, "min_value": min_value, "max_value": max_value, "help_text": help_text},
    )


def float_spec(section: str, key: str, label: str, *, min_value: float | None = None, max_value: float | None = None, help_text: str = "") -> FieldSpec:
    return FieldSpec(
        section=section,
        key=key,
        label=label,
        field_class=forms.FloatField,
        kwargs={"required": False, "min_value": min_value, "max_value": max_value, "help_text": help_text},
    )


def bool_spec(section: str, key: str, label: str, *, help_text: str = "") -> FieldSpec:
    return FieldSpec(
        section=section,
        key=key,
        label=label,
        field_class=forms.BooleanField,
        kwargs={"required": False, "help_text": help_text},
    )


def choice_spec(section: str, key: str, label: str, *, choices: list[tuple[int, str]], help_text: str = "") -> FieldSpec:
    return FieldSpec(
        section=section,
        key=key,
        label=label,
        field_class=forms.TypedChoiceField,
        kwargs={
            "required": False,
            "choices": choices,
            "coerce": int,
            "help_text": help_text,
        },
    )


COMMON_SPECS = {
    "branding": [
        text_spec("branding", "primary_color", "Color principal", help_text="Hex, rgb o rgba."),
        text_spec("branding", "secondary_color", "Color secundario", help_text="Hex, rgb o rgba."),
        url_spec("branding", "logo_url", "Logo", help_text="Opcional para el encabezado del juego."),
        url_spec("branding", "background_url", "Fondo general", help_text="Fondo del panel principal y de la portada."),
        url_spec("branding", "welcome_image_url", "Imagen de portada", help_text="Se usa en la pantalla inicial del juego."),
        text_spec("branding", "watermark_text", "Texto de watermark"),
    ],
    "texts": [
        text_spec("texts", "welcome_title", "Título principal"),
        text_spec("texts", "welcome_subtitle", "Subtítulo", multiline=True),
        text_spec("texts", "cta_button", "Texto del botón"),
        text_spec("texts", "completion_title", "Título de finalización"),
        text_spec("texts", "completion_subtitle", "Subtítulo de finalización", multiline=True),
    ],
    "watermark": [
        bool_spec("watermark", "enabled", "Mostrar watermark"),
        text_spec("watermark", "color", "Color del watermark", help_text="Hex, rgb o rgba."),
        float_spec("watermark", "opacity", "Opacidad", min_value=0, max_value=1),
        int_spec("watermark", "font_size", "Tamano de fuente", min_value=12, max_value=240),
    ],
    "rules": [],
    "visual": [],
    "content": [],
}


GAME_SPECIFIC_SPECS = {
    "puzzle-mundial": {
        "branding": [],
        "texts": [],
        "rules": [
            bool_spec("rules", "show_timer", "Mostrar tiempo"),
            int_spec("rules", "timer_seconds", "Tiempo objetivo (segundos)", min_value=10, max_value=3600),
            bool_spec("rules", "show_moves", "Mostrar movimientos"),
            bool_spec("rules", "show_progress", "Mostrar progreso"),
            choice_spec(
                "rules",
                "grid_size",
                "Tamano del puzzle",
                choices=[(3, "3 x 3"), (4, "4 x 4"), (5, "5 x 5")],
            ),
        ],
        "visual": [
            text_spec("visual", "screen_background_color", "Color de fondo de pantalla"),
            text_spec("visual", "panel_bg_color", "Fondo de panel"),
            text_spec("visual", "panel_border_color", "Borde de panel"),
            text_spec("visual", "text_color", "Texto principal"),
            text_spec("visual", "accent_color", "Acento de interacción"),
            text_spec("visual", "success_color", "Color de exito"),
        ],
        "content": [
            url_spec(
                "content",
                "puzzle_image_url",
                "Imagen del puzzle",
                help_text="Es la imagen real que se corta en piezas para jugar.",
            ),
        ],
    },
    "trivia-mundial-fotos": {
        "branding": [],
        "texts": [],
        "rules": [
            bool_spec("rules", "show_timer", "Mostrar tiempo"),
            int_spec("rules", "timer_seconds", "Tiempo por pregunta (segundos)", min_value=3, max_value=300),
            int_spec("rules", "points_per_correct", "Puntos por respuesta correcta", min_value=0, max_value=10000),
            int_spec("rules", "max_questions", "Preguntas por partida", min_value=1, max_value=100),
        ],
        "visual": [
            text_spec("visual", "screen_background_color", "Color de fondo de pantalla"),
            text_spec("visual", "panel_bg_color", "Color de fondo de panel"),
            text_spec("visual", "panel_border_color", "Color de borde de panel"),
            text_spec("visual", "chip_bg_color", "Color de chips"),
            text_spec("visual", "text_color", "Color de texto principal"),
            text_spec("visual", "muted_text_color", "Color de texto secundario"),
            text_spec("visual", "accent_color", "Color de acento"),
            text_spec("visual", "success_color", "Color de acierto"),
            text_spec("visual", "danger_color", "Color de error"),
        ],
        "content": [
            url_spec(
                "content",
                "question_pack_image_url",
                "Paquete de tarjetas",
                help_text="Opcional para usar una imagen fallback cuando la pregunta no tenga foto propia.",
            ),
        ],
    },
    "el-del-arquero": {
        "branding": [
            url_spec("branding", "ball_image_url", "URL de pelota principal"),
            url_spec("branding", "bonus_ball_image_url", "URL de pelota bonus"),
            url_spec("branding", "penalty_ball_image_url", "URL de pelota trampa"),
        ],
        "texts": [
            text_spec("texts", "instructions_text", "Texto de instrucciones", multiline=True),
            text_spec("texts", "play_again_button", "Texto del boton de rejugar"),
        ],
        "rules": [
            bool_spec("rules", "show_timer", "Mostrar tiempo"),
            int_spec("rules", "timer_seconds", "Duracion de la partida (segundos)", min_value=10, max_value=3600),
            bool_spec("rules", "show_score", "Mostrar puntaje"),
            bool_spec("rules", "show_saves", "Mostrar atajadas"),
            int_spec("rules", "goalkeeper_width", "Ancho del arquero", min_value=60, max_value=240),
            int_spec("rules", "points_per_save", "Puntos por atajada", min_value=0, max_value=1000),
            int_spec("rules", "ball_speed_min", "Velocidad minima de pelotas", min_value=1, max_value=50),
            int_spec("rules", "ball_speed_max", "Velocidad maxima de pelotas", min_value=1, max_value=100),
            int_spec("rules", "spawn_interval_ms", "Intervalo de aparicion (ms)", min_value=100, max_value=10000),
            bool_spec("rules", "bonus_ball_enabled", "Habilitar pelota bonus"),
            int_spec("rules", "bonus_points", "Puntos por pelota bonus", min_value=0, max_value=1000),
            int_spec("rules", "bonus_ball_spawn_chance", "Chance de bonus (%)", min_value=0, max_value=100),
            bool_spec("rules", "penalty_ball_enabled", "Habilitar pelota trampa"),
            int_spec("rules", "penalty_points", "Penalizacion por pelota trampa", min_value=0, max_value=1000),
            int_spec("rules", "penalty_ball_spawn_chance", "Chance de trampa (%)", min_value=0, max_value=100),
        ],
        "visual": [
            text_spec("visual", "screen_background_color", "Color de fondo de pantalla"),
            text_spec("visual", "field_green_color", "Color del cesped principal"),
            text_spec("visual", "field_dark_color", "Color del cesped secundario"),
            text_spec("visual", "line_color", "Color de lineas de cancha"),
            text_spec("visual", "goalkeeper_jersey_color", "Color de camiseta del arquero"),
            text_spec("visual", "goalkeeper_detail_color", "Color de detalles del arquero"),
            text_spec("visual", "goalkeeper_glove_color", "Color de guantes"),
            text_spec("visual", "accent_color", "Color de acento"),
        ],
        "content": [
            text_spec("content", "sponsor_top_left", "Patrocinador superior izquierdo"),
            text_spec("content", "sponsor_top_right", "Patrocinador superior derecho"),
            text_spec("content", "sponsor_bottom", "Patrocinador inferior"),
        ],
    },
}


def deep_merge(base: dict, patch: dict) -> dict:
    merged = deepcopy(base)
    for key, value in (patch or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
            continue
        merged[key] = value
    return merged


def get_specs_by_section(slug: str | None) -> dict[str, list[FieldSpec]]:
    sections = {section: list(COMMON_SPECS.get(section, [])) for section in SECTION_ORDER}
    specific = GAME_SPECIFIC_SPECS.get(slug or "", {})
    for section in SECTION_ORDER:
        sections[section].extend(specific.get(section, []))
    return sections


def get_field_names_by_section(slug: str | None) -> dict[str, list[str]]:
    return {
        section: [spec.name for spec in specs]
        for section, specs in get_specs_by_section(slug).items()
        if specs
    }


def get_merged_config(slug: str | None, current_config: dict | None) -> dict:
    return deep_merge(get_default_config(slug or ""), current_config or {})


def _empty_value_for_spec(spec: FieldSpec):
    if issubclass(spec.field_class, (forms.CharField, forms.URLField)):
        return ""
    if spec.field_class is forms.BooleanField:
        return False
    return None


def apply_specs_to_fields(target_fields: dict, slug: str, merged_config: dict) -> None:
    for section, specs in get_specs_by_section(slug).items():
        section_data = merged_config.get(section, {})
        for spec in specs:
            target_fields[spec.name] = spec.build_field()
            target_fields[spec.name].initial = section_data.get(spec.key)


def build_config_from_cleaned_data(slug: str, cleaned_data: dict, current_config: dict | None) -> dict:
    config = get_merged_config(slug, current_config)
    for section, specs in get_specs_by_section(slug).items():
        target = config.setdefault(section, {})
        for spec in specs:
            value = cleaned_data.get(spec.name)
            if value is None:
                value = _empty_value_for_spec(spec)
            target[spec.key] = value
    return config


def spec_input_kind(spec: FieldSpec) -> str:
    if spec.field_class is forms.BooleanField:
        return "checkbox"
    if spec.field_class is forms.TypedChoiceField:
        return "select"
    if spec.field_class in (forms.IntegerField, forms.FloatField):
        return "number"
    widget = spec.kwargs.get("widget")
    if isinstance(widget, forms.Textarea):
        return "textarea"
    if issubclass(spec.field_class, (forms.URLField, AssetURLField)):
        return "url"
    return "text"


def get_spec_lookup(slug: str | None) -> dict[str, FieldSpec]:
    lookup = {}
    for specs in get_specs_by_section(slug).values():
        for spec in specs:
            lookup[spec.name] = spec
    return lookup


def build_editor_sections(slug: str, current_config: dict | None) -> list[dict]:
    merged_config = get_merged_config(slug, current_config)
    sections = []
    for section in SECTION_ORDER:
        specs = get_specs_by_section(slug).get(section, [])
        if not specs:
            continue
        items = []
        for spec in specs:
            value = merged_config.get(section, {}).get(spec.key)
            items.append({
                "name": spec.name,
                "section": spec.section,
                "key": spec.key,
                "label": spec.label,
                "help_text": spec.kwargs.get("help_text", ""),
                "kind": spec_input_kind(spec),
                "value": value,
                "choices": list(spec.kwargs.get("choices", [])),
                "min_value": spec.kwargs.get("min_value"),
                "max_value": spec.kwargs.get("max_value"),
                "step": "0.01" if spec.field_class is forms.FloatField else "1",
            })
        sections.append({
            "key": section,
            "title": SECTION_TITLES[section],
            "description": SECTION_DESCRIPTIONS[section],
            "fields": items,
        })
    return sections


PLAYTEK_LAYOUTS = {
    "puzzle-mundial": [
        {
            "key": "identity",
            "title": "Identidad del puzzle",
            "description": "Definí colores y assets de Puzzle Mundial sin tocar las lógicas del juego.",
            "color_fields": [
                "branding__primary_color",
                "branding__secondary_color",
                "visual__text_color",
                "visual__panel_border_color",
                "visual__accent_color",
                "visual__panel_bg_color",
            ],
            "asset_fields": [
                "branding__logo_url",
                "branding__welcome_image_url",
                "branding__background_url",
                "content__puzzle_image_url",
            ],
        },
        {
            "key": "texts",
            "title": "Textos",
            "description": "Ajustá la narrativa del juego: portada, CTA y mensaje final.",
            "fields": [
                "texts__welcome_title",
                "texts__cta_button",
                "texts__welcome_subtitle",
                "texts__completion_title",
                "texts__completion_subtitle",
            ],
        },
        {
            "key": "rules",
            "title": "Reglas del puzzle",
            "description": "Configurá tamaño del tablero, tiempo objetivo y métricas visibles.",
            "fields": [
                "rules__grid_size",
                "rules__timer_seconds",
                "rules__show_timer",
                "rules__show_moves",
                "rules__show_progress",
            ],
        },
    ],
    "trivia-mundial-fotos": [
        {
            "key": "identity",
            "title": "Identidad de la trivia",
            "description": "Definí colores, fondos y portada tal como se verá en la plataforma.",
            "color_fields": [
                "branding__primary_color",
                "branding__secondary_color",
                "visual__text_color",
                "visual__panel_border_color",
                "visual__accent_color",
                "visual__panel_bg_color",
            ],
            "asset_fields": [
                "branding__logo_url",
                "branding__welcome_image_url",
                "branding__background_url",
                "content__question_pack_image_url",
            ],
        },
        {
            "key": "texts",
            "title": "Textos",
            "description": "Ajustá el título, CTA y cierre de la experiencia.",
            "fields": [
                "texts__welcome_title",
                "texts__cta_button",
                "texts__welcome_subtitle",
                "texts__completion_title",
                "texts__completion_subtitle",
            ],
        },
        {
            "key": "rules",
            "title": "Reglas de la trivia",
            "description": "Controlá tiempo, puntaje y cantidad máxima de preguntas.",
            "fields": [
                "rules__timer_seconds",
                "rules__points_per_correct",
                "rules__max_questions",
                "rules__show_timer",
            ],
        },
    ],
    "el-del-arquero": [
        {
            "key": "identity",
            "title": "Identidad del juego",
            "description": "Configurá paleta, fondo y assets principales del juego del arquero.",
            "color_fields": [
                "branding__primary_color",
                "branding__secondary_color",
                "visual__field_green_color",
                "visual__field_dark_color",
                "visual__line_color",
                "visual__goalkeeper_jersey_color",
            ],
            "asset_fields": [
                "branding__logo_url",
                "branding__welcome_image_url",
                "branding__background_url",
                "branding__ball_image_url",
                "branding__bonus_ball_image_url",
                "branding__penalty_ball_image_url",
            ],
        },
        {
            "key": "texts",
            "title": "Textos",
            "description": "Ajustá portada, instrucciones y copy de cierre.",
            "fields": [
                "texts__welcome_title",
                "texts__cta_button",
                "texts__welcome_subtitle",
                "texts__instructions_text",
                "texts__completion_title",
                "texts__completion_subtitle",
                "texts__play_again_button",
            ],
        },
        {
            "key": "rules",
            "title": "Reglas del juego",
            "description": "Controlá duración, bonus, trampas y métricas visibles.",
            "fields": [
                "rules__timer_seconds",
                "rules__points_per_save",
                "rules__show_timer",
                "rules__show_score",
                "rules__show_saves",
                "rules__bonus_ball_enabled",
                "rules__bonus_points",
                "rules__bonus_ball_spawn_chance",
                "rules__penalty_ball_enabled",
                "rules__penalty_points",
                "rules__penalty_ball_spawn_chance",
                "rules__goalkeeper_width",
                "rules__ball_speed_min",
                "rules__ball_speed_max",
                "rules__spawn_interval_ms",
            ],
        },
    ],
}


def build_playtek_editor_layout(slug: str, current_config: dict | None) -> dict:
    sections = build_editor_sections(slug, current_config)
    lookup = {field["name"]: field for section in sections for field in section["fields"]}
    layout = PLAYTEK_LAYOUTS.get(slug, [])
    visible_names = set()
    cards = []

    for card in layout:
        color_fields = [lookup[name] for name in card.get("color_fields", []) if name in lookup]
        asset_fields = [lookup[name] for name in card.get("asset_fields", []) if name in lookup]
        regular_fields = [lookup[name] for name in card.get("fields", []) if name in lookup]
        visible_names.update(field["name"] for field in color_fields + asset_fields + regular_fields)
        cards.append({
            "key": card["key"],
            "title": card["title"],
            "description": card["description"],
            "color_fields": color_fields,
            "asset_fields": asset_fields,
            "fields": regular_fields,
        })

    hidden_fields = [field for name, field in lookup.items() if name not in visible_names]
    return {"cards": cards, "hidden_fields": hidden_fields}


class GameConfigStructuredForm(forms.Form):
    def __init__(self, slug: str, current_config: dict | None = None, *args, **kwargs):
        self.game_slug = slug
        self.current_config = current_config or {}
        super().__init__(*args, **kwargs)
        apply_specs_to_fields(self.fields, self.game_slug, get_merged_config(self.game_slug, self.current_config))

    def build_config(self) -> dict:
        if not self.is_valid():
            raise ValueError("Cannot build config from invalid form.")
        return build_config_from_cleaned_data(self.game_slug, self.cleaned_data, self.current_config)


class GameConfigAdminForm(forms.ModelForm):
    class Meta:
        model = GameConfig
        fields = ("game", "config")
        widgets = {
            "config": forms.Textarea(attrs={"rows": 12}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.game_slug = self._resolve_game_slug()
        self.uses_structured_editor = bool(self.game_slug)

        if not self.uses_structured_editor:
            self.fields["config"].help_text = (
                "Elegi un juego y guarda para pasar al editor estructurado, "
                "o carga JSON manualmente si queres un control avanzado."
            )
            return

        self.fields["config"].required = False
        self.fields["config"].widget = forms.HiddenInput()

        apply_specs_to_fields(self.fields, self.game_slug, get_merged_config(self.game_slug, self.instance.config))

    def _resolve_game_slug(self) -> str | None:
        if getattr(self.instance, "game_id", None):
            return self.instance.game.slug

        game_id = self.data.get("game") or self.initial.get("game")
        if isinstance(game_id, Game):
            return game_id.slug
        if not game_id:
            return None
        return Game.objects.filter(pk=game_id).values_list("slug", flat=True).first()

    def clean(self):
        cleaned_data = super().clean()
        if not self.uses_structured_editor:
            return cleaned_data

        cleaned_data["config"] = build_config_from_cleaned_data(
            self.game_slug,
            cleaned_data,
            self.instance.config,
        )
        return cleaned_data
