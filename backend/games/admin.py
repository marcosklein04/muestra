import json
from urllib.parse import urlencode

from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .forms import (
    GameConfigAdminForm,
    SECTION_DESCRIPTIONS,
    SECTION_ORDER,
    SECTION_TITLES,
    get_field_names_by_section,
)
from .models import Game, GameConfig, TriviaQuestion, TriviaAnswer, PlaySession

admin.site.site_header = "Muestra - Panel de gestion"
admin.site.site_title = "Muestra Admin"
admin.site.index_title = "Gestion de juegos y configuraciones"


def resolve_game_slug_from_request(request):
    game_id = request.POST.get("game") or request.GET.get("game")
    if not game_id:
        return None
    return Game.objects.filter(pk=game_id).values_list("slug", flat=True).first()


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "is_enabled",
        "is_featured",
        "sort_order",
        "customization_link",
        "preview_link",
    )
    list_editable = ("is_enabled", "is_featured", "sort_order")
    list_filter = ("is_enabled", "is_featured")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("customization_link",)
    fieldsets = (
        (None, {
            "fields": ("name", "slug", "description", "cover_image_url"),
        }),
        ("Estado", {
            "fields": ("is_enabled", "is_featured", "sort_order"),
        }),
        ("Personalizacion", {
            "fields": ("customization_link",),
            "description": "Abri el editor guiado para personalizar branding, textos, reglas y contenido.",
        }),
    )

    def preview_link(self, obj):
        url = obj.runner_path()
        return format_html('<a href="{}" target="_blank">Abrir juego</a>', url)

    preview_link.short_description = "Juego"

    def customization_link(self, obj):
        if not obj or not obj.pk:
            return "Guarda el juego para habilitar la personalizacion."

        try:
            config = obj.config
        except GameConfig.DoesNotExist:
            add_url = reverse("admin:games_gameconfig_add")
            url = f"{add_url}?{urlencode({'game': obj.pk})}"
            return format_html(
                '<a class="button" href="{}">Crear personalizacion</a>',
                url,
            )

        change_url = reverse("admin:games_gameconfig_change", args=[config.pk])
        return format_html(
            '<a class="button" href="{}">Editar personalizacion</a>',
            change_url,
        )

    customization_link.short_description = "Personalizacion"


@admin.register(GameConfig)
class GameConfigAdmin(admin.ModelAdmin):
    form = GameConfigAdminForm
    list_display = ("game", "updated_at", "preview_link")
    readonly_fields = ("preview_link", "updated_at", "config_json_preview", "question_bank_link")

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        game_id = request.GET.get("game")
        if game_id:
            initial["game"] = game_id
        return initial

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        if obj:
            fields.append("game")
        return fields

    def get_fieldsets(self, request, obj=None):
        slug = obj.game.slug if obj and obj.game_id else resolve_game_slug_from_request(request)

        if not slug:
            return (
                ("General", {
                    "fields": ("game", "preview_link"),
                    "description": "Elegi un juego y guarda para pasar al editor guiado. Tambien podes cargar JSON manualmente.",
                }),
                ("Configuracion JSON", {
                    "fields": ("config",),
                }),
                ("Metadata", {
                    "fields": ("updated_at",),
                }),
            )

        fieldsets = [
            ("General", {
                "fields": ("game", "preview_link"),
                "description": "Personaliza este juego como en Playtek: cambia look and feel, textos, reglas y activos sin tocar codigo.",
            }),
        ]

        names_by_section = get_field_names_by_section(slug)
        for section in SECTION_ORDER:
            names = names_by_section.get(section)
            if not names:
                continue
            fieldsets.append(
                (SECTION_TITLES[section], {
                    "fields": tuple(names),
                    "description": SECTION_DESCRIPTIONS[section],
                })
            )

        if slug == Game.SLUG_TRIVIA_MUNDIAL_FOTOS:
            fieldsets.append(
                ("Banco de preguntas", {
                    "fields": ("question_bank_link",),
                    "description": "Las preguntas de trivia se administran por separado para que el contenido quede ordenado y reusable.",
                })
            )

        fieldsets.append(
            ("JSON final", {
                "fields": ("config_json_preview",),
                "classes": ("collapse",),
                "description": "Vista de solo lectura del JSON que consumen los runners.",
            })
        )
        fieldsets.append(
            ("Metadata", {
                "fields": ("updated_at",),
            })
        )
        return fieldsets

    def preview_link(self, obj):
        if not obj or not obj.game_id:
            return "Disponible despues de elegir un juego."
        return format_html(
            '<a href="{}" target="_blank">Abrir preview</a>',
            obj.game.runner_path(),
        )

    preview_link.short_description = "Preview"

    def question_bank_link(self, obj):
        if not obj or not obj.game_id:
            return "Disponible despues de guardar la configuracion."
        url = reverse("admin:games_triviaquestion_changelist")
        filtered_url = f"{url}?{urlencode({'game__id__exact': obj.game_id})}"
        return format_html(
            '<a href="{}">Editar preguntas de esta trivia</a>',
            filtered_url,
        )

    question_bank_link.short_description = "Preguntas"

    def config_json_preview(self, obj):
        if not obj:
            return "Todavia no se genero JSON."
        rendered = json.dumps(obj.config or {}, indent=2, ensure_ascii=False)
        return format_html("<pre>{}</pre>", rendered)

    config_json_preview.short_description = "JSON"


class TriviaAnswerInline(admin.TabularInline):
    model = TriviaAnswer
    extra = 3
    fields = ("label", "image_url", "is_correct", "sort_order")
    ordering = ("sort_order", "id")


@admin.register(TriviaQuestion)
class TriviaQuestionAdmin(admin.ModelAdmin):
    list_display = ("prompt", "game", "is_active", "sort_order", "answer_count")
    list_editable = ("is_active", "sort_order")
    list_filter = ("game", "is_active")
    search_fields = ("prompt",)
    inlines = [TriviaAnswerInline]
    fieldsets = (
        (None, {
            "fields": ("game", "prompt", "question_image_url"),
        }),
        ("Estado", {
            "fields": ("is_active", "sort_order"),
        }),
    )

    def answer_count(self, obj):
        return obj.answers.count()

    answer_count.short_description = "Respuestas"


@admin.register(PlaySession)
class PlaySessionAdmin(admin.ModelAdmin):
    list_display = ("id", "game", "status", "started_at", "ended_at")
    list_filter = ("game", "status")
    readonly_fields = ("id", "game", "anon_token", "started_at", "ended_at", "status", "result", "client_state")
    search_fields = ("id",)
    date_hierarchy = "started_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
