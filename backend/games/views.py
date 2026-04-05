import json
import logging
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.utils.text import slugify
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .forms import (
    AssetURLField,
    GameConfigStructuredForm,
    build_playtek_editor_layout,
    get_merged_config,
    get_spec_lookup,
)
from .models import Game, GameConfig, PlaySession, TriviaQuestion
from .presets import TRIVIA_QUESTIONS, get_default_config

logger = logging.getLogger("games")

TRIVIA_EDITOR_MAX_QUESTIONS = 12
TRIVIA_EDITOR_ANSWER_SLOTS = 4


# ── Helper ────────────────────────────────────────────────────────────────────

def _get_game_config(game: Game) -> dict:
    """Return the operator-configured JSON, or empty dict if not set."""
    try:
        return game.config.config or {}
    except GameConfig.DoesNotExist:
        return {}


def _get_game_config_instance(game: Game) -> GameConfig | None:
    try:
        return game.config
    except GameConfig.DoesNotExist:
        return None


def _uploadable_field_names(slug: str) -> list[str]:
    names = []
    for name, spec in get_spec_lookup(slug).items():
        if issubclass(spec.field_class, AssetURLField):
            names.append(name)
    return names


def _store_uploaded_asset(game_slug: str, field_name: str, uploaded_file) -> str:
    storage = FileSystemStorage(location=settings.MEDIA_ROOT, base_url=settings.MEDIA_URL)
    suffix = Path(uploaded_file.name).suffix.lower() or ".bin"
    filename = f"customizer/{game_slug}/{slugify(field_name)}-{uuid4().hex[:8]}{suffix}"
    saved_name = storage.save(filename, uploaded_file)
    return storage.url(saved_name)


def _apply_uploaded_assets(slug: str, config: dict, files, post_data) -> dict:
    next_config = json.loads(json.dumps(config))

    for field_name in _uploadable_field_names(slug):
        section, key = field_name.split("__", 1)
        clear_flag = post_data.get(f"{field_name}__clear")
        upload = files.get(f"{field_name}__file")
        next_config.setdefault(section, {})

        if clear_flag == "1":
            next_config[section][key] = ""
            continue

        if upload:
            next_config[section][key] = _store_uploaded_asset(slug, field_name, upload)

    return next_config


def _get_trivia_questions(game: Game) -> list[dict]:
    """Return active trivia questions for the given game as API dicts."""
    questions = (
        TriviaQuestion.objects
        .filter(game=game, is_active=True)
        .prefetch_related("answers")
        .order_by("sort_order", "id")
    )
    return [q.to_api_dict() for q in questions]


def _get_trivia_editor_questions(game: Game) -> list[dict]:
    source_questions = list(
        TriviaQuestion.objects
        .filter(game=game)
        .prefetch_related("answers")
        .order_by("sort_order", "id")
    )

    editor_questions = []

    if source_questions:
        for question in source_questions:
            answers = list(question.answers.all().order_by("sort_order", "id"))
            correct_index = next((idx for idx, answer in enumerate(answers) if answer.is_correct), 0)
            answer_rows = []
            for idx, answer in enumerate(answers[:TRIVIA_EDITOR_ANSWER_SLOTS]):
                answer_rows.append({
                    "index": idx,
                    "label": answer.label,
                    "image_url": answer.image_url,
                })

            response_type = "image" if any(item["image_url"] for item in answer_rows) else "text"
            while len(answer_rows) < TRIVIA_EDITOR_ANSWER_SLOTS:
                answer_rows.append({"index": len(answer_rows), "label": "", "image_url": ""})

            editor_questions.append({
                "prompt": question.prompt,
                "question_image_url": question.question_image_url,
                "response_type": response_type,
                "correct_answer": correct_index,
                "answers": answer_rows,
            })
    else:
        for question_data in TRIVIA_QUESTIONS:
            answers = []
            raw_answers = question_data.get("answers", [])[:TRIVIA_EDITOR_ANSWER_SLOTS]
            correct_index = next((idx for idx, answer in enumerate(raw_answers) if answer.get("is_correct")), 0)
            for idx, answer in enumerate(raw_answers):
                answers.append({
                    "index": idx,
                    "label": answer.get("label", ""),
                    "image_url": answer.get("image_url", ""),
                })
            while len(answers) < TRIVIA_EDITOR_ANSWER_SLOTS:
                answers.append({"index": len(answers), "label": "", "image_url": ""})

            editor_questions.append({
                "prompt": question_data.get("prompt", ""),
                "question_image_url": question_data.get("question_image_url", ""),
                "response_type": "image" if any(item["image_url"] for item in answers) else "text",
                "correct_answer": correct_index,
                "answers": answers,
            })

    return editor_questions


def _build_trivia_editor_context(game: Game, current_config: dict | None) -> dict:
    existing_questions = _get_trivia_editor_questions(game)
    desired_slots = TRIVIA_EDITOR_MAX_QUESTIONS

    padded_questions = list(existing_questions[:TRIVIA_EDITOR_MAX_QUESTIONS])
    while len(padded_questions) < desired_slots:
        padded_questions.append({
            "prompt": "",
            "question_image_url": "",
            "response_type": "text",
            "correct_answer": 0,
            "answers": [
                {"index": index, "label": "", "image_url": ""}
                for index in range(TRIVIA_EDITOR_ANSWER_SLOTS)
            ],
        })

    questions = []
    for index, question in enumerate(padded_questions):
        answers = question.get("answers", [])
        normalized_answers = []
        for answer_index in range(TRIVIA_EDITOR_ANSWER_SLOTS):
            answer = answers[answer_index] if answer_index < len(answers) else {}
            normalized_answers.append({
                "index": answer_index,
                "label": answer.get("label", ""),
                "image_url": answer.get("image_url", ""),
            })

        questions.append({
            "index": index,
            "visible": index < max(1, len(existing_questions)),
            "prompt": question.get("prompt", ""),
            "question_image_url": question.get("question_image_url", ""),
            "response_type": question.get("response_type", "text"),
            "correct_answer": question.get("correct_answer", 0),
            "answers": normalized_answers,
        })

    return {
        "count": max(1, len(existing_questions)),
        "max_count": TRIVIA_EDITOR_MAX_QUESTIONS,
        "questions": questions,
    }


def _read_trivia_questions_from_request(game_slug: str, post_data, files) -> tuple[list[dict], dict]:
    try:
        question_count = int(post_data.get("trivia_question_count") or "1")
    except (TypeError, ValueError):
        question_count = 1
    question_count = max(1, min(TRIVIA_EDITOR_MAX_QUESTIONS, question_count))

    questions = []
    errors = {}

    for question_index in range(question_count):
        prefix = f"trivia_questions__{question_index}"
        prompt = (post_data.get(f"{prefix}__prompt") or "").strip()
        response_type = (post_data.get(f"{prefix}__response_type") or "text").strip().lower()
        if response_type not in {"text", "image"}:
            response_type = "text"

        question_image_url = (post_data.get(f"{prefix}__question_image_url") or "").strip()
        question_clear = post_data.get(f"{prefix}__question_image_url__clear")
        question_upload = files.get(f"{prefix}__question_image_url__file")
        if question_clear == "1":
            question_image_url = ""
        elif question_upload:
            question_image_url = _store_uploaded_asset(game_slug, f"{prefix}__question_image_url", question_upload)

        try:
            correct_answer_index = int(post_data.get(f"{prefix}__correct_answer") or "0")
        except (TypeError, ValueError):
            correct_answer_index = 0

        answers = []
        for answer_index in range(TRIVIA_EDITOR_ANSWER_SLOTS):
            answer_prefix = f"{prefix}__answers__{answer_index}"
            label = (post_data.get(f"{answer_prefix}__label") or "").strip()
            image_url = (post_data.get(f"{answer_prefix}__image_url") or "").strip()
            clear_flag = post_data.get(f"{answer_prefix}__image_url__clear")
            upload = files.get(f"{answer_prefix}__image_url__file")

            if clear_flag == "1":
                image_url = ""
            elif upload:
                image_url = _store_uploaded_asset(game_slug, f"{answer_prefix}__image_url", upload)

            if response_type == "image":
                if label or image_url:
                    answers.append({
                        "index": answer_index,
                        "label": label,
                        "image_url": image_url,
                    })
            elif label:
                answers.append({
                    "index": answer_index,
                    "label": label,
                    "image_url": image_url,
                })

        if not prompt and not answers and not question_image_url:
            continue

        if not prompt:
            errors[f"{prefix}__prompt"] = ["Escribí el enunciado de la pregunta."]
            continue

        if len(answers) < 2:
            errors[f"{prefix}__answers"] = ["Agregá al menos dos respuestas para esta pregunta."]
            continue

        if response_type == "image" and not all(item["image_url"] for item in answers):
            errors[f"{prefix}__response_type"] = ["Si elegís respuesta por imagen, cada respuesta debe tener su imagen."]
            continue

        correct_answer = next((item for item in answers if item["index"] == correct_answer_index), answers[0])
        questions.append({
            "prompt": prompt,
            "question_image_url": question_image_url,
            "answers": answers,
            "correct_index": correct_answer["index"],
            "response_type": response_type,
        })

    if not questions:
        errors["trivia_questions"] = ["Agregá al menos una pregunta completa para guardar la trivia."]

    return questions, errors


def _replace_trivia_questions(game: Game, questions_payload: list[dict]) -> None:
    TriviaQuestion.objects.filter(game=game).delete()

    for question_index, question_data in enumerate(questions_payload, start=1):
        question = TriviaQuestion.objects.create(
            game=game,
            prompt=question_data["prompt"],
            question_image_url=question_data["question_image_url"],
            is_active=True,
            sort_order=question_index,
        )

        for answer_sort_order, answer_data in enumerate(question_data["answers"], start=1):
            question.answers.create(
                label=answer_data["label"],
                image_url=answer_data["image_url"],
                is_correct=answer_data["index"] == question_data["correct_index"],
                sort_order=answer_sort_order,
            )


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
def customizer_home(request):
    games = Game.objects.order_by("sort_order", "name")
    return render(request, "games/customizer_home.html", {"games": games})


@require_GET
def customizer_page(request, slug: str):
    game = get_object_or_404(Game, slug=slug)
    current_config = _get_game_config(game)
    editor_layout = build_playtek_editor_layout(game.slug, current_config)
    trivia_editor = _build_trivia_editor_context(game, current_config) if game.slug == Game.SLUG_TRIVIA_MUNDIAL_FOTOS else None
    return render(
        request,
        "games/customizer_detail.html",
        {
            "game": game,
            "cards": editor_layout["cards"],
            "hidden_fields": editor_layout["hidden_fields"],
            "initial_config": get_merged_config(game.slug, current_config),
            "default_config": get_default_config(game.slug),
            "trivia_editor": trivia_editor,
        },
    )


@require_POST
def api_guardar_personalizacion(request, slug: str):
    game = get_object_or_404(Game, slug=slug)
    current_instance = _get_game_config_instance(game)
    current_config = current_instance.config if current_instance else {}

    form = GameConfigStructuredForm(game.slug, current_config=current_config, data=request.POST)
    if not form.is_valid():
        return JsonResponse({"ok": False, "errors": form.errors}, status=400)

    trivia_questions = []
    if game.slug == Game.SLUG_TRIVIA_MUNDIAL_FOTOS:
        trivia_questions, trivia_errors = _read_trivia_questions_from_request(game.slug, request.POST, request.FILES)
        if trivia_errors:
            return JsonResponse({"ok": False, "errors": trivia_errors}, status=400)

    with transaction.atomic():
        config_instance, _ = GameConfig.objects.get_or_create(
            game=game,
            defaults={"config": get_default_config(game.slug)},
        )
        config_instance.config = _apply_uploaded_assets(
            game.slug,
            form.build_config(),
            request.FILES,
            request.POST,
        )
        config_instance.save(update_fields=["config", "updated_at"])

        if game.slug == Game.SLUG_TRIVIA_MUNDIAL_FOTOS:
            _replace_trivia_questions(game, trivia_questions)

    return JsonResponse({
        "ok": True,
        "message": "Personalizacion guardada.",
        "config": config_instance.config,
        "trivia_questions": _build_trivia_editor_context(game, config_instance.config)["questions"] if game.slug == Game.SLUG_TRIVIA_MUNDIAL_FOTOS else [],
        "trivia_question_count": len(trivia_questions) if game.slug == Game.SLUG_TRIVIA_MUNDIAL_FOTOS else 0,
    })


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
