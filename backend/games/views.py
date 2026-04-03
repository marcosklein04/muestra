import json
import logging
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .models import Game, GameConfig, PlaySession, TriviaQuestion

logger = logging.getLogger("games")


# ── Helper ────────────────────────────────────────────────────────────────────

def _get_game_config(game: Game) -> dict:
    """Return the operator-configured JSON, or empty dict if not set."""
    try:
        return game.config.config or {}
    except GameConfig.DoesNotExist:
        return {}


def _get_trivia_questions(game: Game) -> list[dict]:
    """Return active trivia questions for the given game as API dicts."""
    questions = (
        TriviaQuestion.objects
        .filter(game=game, is_active=True)
        .prefetch_related("answers")
        .order_by("sort_order", "id")
    )
    return [q.to_api_dict() for q in questions]


def _token_ok(stored: str, provided: str) -> bool:
    import secrets
    if not stored or not provided:
        return False
    return secrets.compare_digest(stored, provided)


def _err(msg: str, status: int = 400) -> JsonResponse:
    return JsonResponse({"error": msg}, status=status)


# ── Public Pages ──────────────────────────────────────────────────────────────

@require_GET
def home(request):
    games = (
        Game.objects
        .filter(is_enabled=True)
        .order_by("sort_order", "name")
    )
    return render(request, "games/home.html", {"games": games})


@require_GET
def runner_page(request, slug: str):
    game = get_object_or_404(Game, slug=slug, is_enabled=True)
    template_map = {
        Game.SLUG_PUZZLE_MUNDIAL: "runner/puzzle_mundial/index.html",
        Game.SLUG_TRIVIA_MUNDIAL_FOTOS: "runner/trivia_mundial_fotos/index.html",
        Game.SLUG_ARQUERO: "runner/arquero/index.html",
    }
    template_name = template_map.get(slug)
    if not template_name:
        from django.http import Http404
        raise Http404("Juego no disponible")
    return render(request, template_name, {"game": game})


# ── Session API (called by the game JS) ───────────────────────────────────────

@csrf_exempt
@require_POST
def api_iniciar_sesion(request, slug: str):
    """
    Start an anonymous play session. Returns session_id, anon_token, and game config.
    No auth required.
    """
    game = get_object_or_404(Game, slug=slug, is_enabled=True)
    token = PlaySession.generate_token()
    session = PlaySession.objects.create(game=game, anon_token=token)

    config = _get_game_config(game)

    # Inject trivia questions into config for trivia game
    if slug == Game.SLUG_TRIVIA_MUNDIAL_FOTOS:
        questions = _get_trivia_questions(game)
        if questions:
            config = dict(config)
            content = dict(config.get("content", {}))
            content["sparkle_questions"] = questions
            config["content"] = content

    return JsonResponse({
        "session_id": str(session.id),
        "anon_token": token,
        "config": config,
    }, status=201)


@require_GET
def runner_obtener_sesion(request, session_id):
    """
    GET /runner/sesiones/<uuid>?anon_token=<token>
    Returns session state including customization config for the game runner.
    """
    token = (request.GET.get("anon_token") or "").strip()

    try:
        session = PlaySession.objects.select_related("game").get(id=session_id)
    except PlaySession.DoesNotExist:
        return _err("sesion_no_encontrada", 404)

    if not _token_ok(session.anon_token, token):
        return _err("token_invalido", 401)

    config = _get_game_config(session.game)

    # Inject trivia questions for trivia game
    if session.game.slug == Game.SLUG_TRIVIA_MUNDIAL_FOTOS:
        questions = _get_trivia_questions(session.game)
        if questions:
            config = dict(config)
            content = dict(config.get("content", {}))
            content["sparkle_questions"] = questions
            config["content"] = content

    return JsonResponse({
        "sesion": {
            "id": str(session.id),
            "estado": session.status,
            "estado_cliente": {
                "customization": config,
                "preview_mode": False,
            },
        }
    })


@csrf_exempt
@require_POST
def runner_finalizar_sesion(request, session_id):
    """
    POST /runner/sesiones/<uuid>/finalizar
    Body: { anon_token, result, estado_cliente }
    """
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return _err("json_invalido")

    token = (body.get("anon_token") or "").strip()

    try:
        session = PlaySession.objects.get(id=session_id)
    except PlaySession.DoesNotExist:
        return _err("sesion_no_encontrada", 404)

    if not _token_ok(session.anon_token, token):
        return _err("token_invalido", 401)

    if session.status != PlaySession.Status.ACTIVE:
        return JsonResponse({
            "sesion": {"id": str(session.id), "estado": session.status}
        })

    session.status = PlaySession.Status.FINISHED
    session.ended_at = timezone.now()
    session.result = body.get("result") or {}
    session.client_state = body.get("estado_cliente") or {}
    session.save(update_fields=["status", "ended_at", "result", "client_state"])

    logger.info("Sesión finalizada: %s game=%s", session.id, session.game.slug)

    return JsonResponse({
        "sesion": {"id": str(session.id), "estado": session.status}
    })
