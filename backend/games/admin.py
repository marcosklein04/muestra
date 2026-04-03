from django.contrib import admin
from django.utils.html import format_html
from .models import Game, GameConfig, TriviaQuestion, TriviaAnswer, PlaySession

admin.site.site_header = "Muestra — Panel de gestión"
admin.site.site_title = "Muestra Admin"
admin.site.index_title = "Gestión de juegos y configuraciones"


class GameConfigInline(admin.StackedInline):
    model = GameConfig
    extra = 0
    fields = ("config",)
    readonly_fields = ()

    def get_fields(self, request, obj=None):
        return ("config",)


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_enabled", "is_featured", "sort_order", "preview_link")
    list_editable = ("is_enabled", "is_featured", "sort_order")
    list_filter = ("is_enabled", "is_featured")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [GameConfigInline]
    fieldsets = (
        (None, {
            "fields": ("name", "slug", "description", "cover_image_url"),
        }),
        ("Estado", {
            "fields": ("is_enabled", "is_featured", "sort_order"),
        }),
    )

    def preview_link(self, obj):
        url = obj.runner_path()
        return format_html('<a href="{}" target="_blank">Abrir juego</a>', url)
    preview_link.short_description = "Juego"


@admin.register(GameConfig)
class GameConfigAdmin(admin.ModelAdmin):
    list_display = ("game", "updated_at")
    readonly_fields = ("updated_at",)
    fieldsets = (
        (None, {
            "fields": ("game",),
        }),
        ("Configuración JSON", {
            "fields": ("config",),
            "description": (
                "<strong>Estructura del JSON de configuración:</strong><br>"
                "<pre>"
                "{\n"
                '  "branding": {\n'
                '    "primary_color": "#00f5e9",\n'
                '    "secondary_color": "#081a2b",\n'
                '    "logo_url": "",\n'
                '    "background_url": "",\n'
                '    "welcome_image_url": "",\n'
                '    "watermark_text": "MODO PRUEBA"\n'
                "  },\n"
                '  "texts": {\n'
                '    "welcome_title": "PUZZLE MUNDIAL",\n'
                '    "welcome_subtitle": "Armá la imagen pieza por pieza.",\n'
                '    "cta_button": "Empezar puzzle",\n'
                '    "completion_title": "¡Golazo!",\n'
                '    "completion_subtitle": "Completaste el puzzle."\n'
                "  },\n"
                '  "rules": { "grid_size": 3, "show_timer": true, "timer_seconds": 180 },\n'
                '  "visual": { "screen_background_color": "#04121f", "accent_color": "#00f5e9" },\n'
                '  "content": { "puzzle_image_url": "" }\n'
                "}"
                "</pre>"
            ),
        }),
        ("Metadata", {
            "fields": ("updated_at",),
        }),
    )


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
