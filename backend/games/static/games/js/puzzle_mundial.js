(function () {
  "use strict";

  const GAME_SLUG = window.GAME_SLUG || "puzzle-mundial";
  const RETURN_URL = window.RETURN_URL || "/";
  const ASSETS = window.PUZZLE_MUNDIAL_ASSETS || {};

  const state = {
    session: null,     // { id, anon_token }
    config: null,
    gridSize: 3,
    positions: [],
    selectedIndex: null,
    dragSourceIndex: null,
    moves: 0,
    timerInterval: null,
    startedAt: 0,
    elapsedSeconds: 0,
    sessionFinished: false,
    started: false,
  };

  const el = {};

  // ── Utils ──────────────────────────────────────────────────

  async function fetchJSON(url, options) {
    const response = await fetch(url, options);
    const data = await response.json().catch(() => ({}));
    return { response, data };
  }

  function safeText(value, fallback) {
    return typeof value === "string" && value.trim() ? value.trim() : fallback;
  }

  function safeNumber(value, fallback) {
    return typeof value === "number" && Number.isFinite(value) ? value : fallback;
  }

  function deepMerge(base, patch) {
    const output = structuredClone(base);
    Object.entries(patch || {}).forEach(([key, value]) => {
      if (value && typeof value === "object" && !Array.isArray(value) && output[key] && typeof output[key] === "object") {
        output[key] = deepMerge(output[key], value);
        return;
      }
      output[key] = value;
    });
    return output;
  }

  function clampGridSize(value) {
    if (value === 4 || value === 5) return value;
    return 3;
  }

  function formatTime(totalSeconds) {
    const minutes = Math.floor(totalSeconds / 60).toString().padStart(2, "0");
    const seconds = Math.floor(totalSeconds % 60).toString().padStart(2, "0");
    return `${minutes}:${seconds}`;
  }

  // ── Default Config ─────────────────────────────────────────

  function defaultConfig() {
    return {
      branding: {
        primary_color: "#00f5e9",
        secondary_color: "#081a2b",
        logo_url: "",
        background_url: "",
        welcome_image_url: "",
        watermark_text: "",
      },
      texts: {
        welcome_title: "PUZZLE MUNDIAL",
        welcome_subtitle: "Armá la imagen del mundial pieza por pieza.",
        cta_button: "Empezar puzzle",
        completion_title: "¡Golazo!",
        completion_subtitle: "Completaste el puzzle y cerraste la jugada.",
      },
      rules: {
        show_timer: true,
        timer_seconds: 180,
        show_moves: true,
        show_progress: true,
        grid_size: 3,
      },
      visual: {
        screen_background_color: "#04121f",
        panel_bg_color: "rgba(8, 26, 43, 0.84)",
        panel_border_color: "#1b6888",
        text_color: "#f4fbff",
        accent_color: "#00f5e9",
        success_color: "#8ee05f",
      },
      watermark: { enabled: false },
      content: { puzzle_image_url: "" },
    };
  }

  // ── Session API ────────────────────────────────────────────

  async function startSession() {
    const { response, data } = await fetchJSON(`/api/sesion/iniciar/${GAME_SLUG}/`, {
      method: "POST",
      headers: { "X-CSRFToken": getCsrfToken() },
    });
    if (!response.ok) return null;
    return { id: data.session_id, anon_token: data.anon_token, config: data.config || {} };
  }

  async function finishSession(payload) {
    if (state.sessionFinished || !state.session) return null;
    state.sessionFinished = true;

    const url = `/runner/sesiones/${state.session.id}/finalizar`;
    const body = {
      anon_token: state.session.anon_token,
      ...payload,
    };

    const { response, data } = await fetchJSON(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    if (!response.ok) state.sessionFinished = false;
    return data;
  }

  function getCsrfToken() {
    const name = "csrftoken";
    const match = document.cookie.match(new RegExp("(^|;)\\s*" + name + "\\s*=\\s*([^;]+)"));
    return match ? match.pop() : "";
  }

  // ── Puzzle logic ───────────────────────────────────────────

  function totalPieces() { return state.gridSize * state.gridSize; }

  function countCorrectPieces() {
    return state.positions.filter((pieceIndex, cellIndex) => pieceIndex === cellIndex).length;
  }

  function progressPercent() {
    return Math.round((countCorrectPieces() / totalPieces()) * 100);
  }

  function shuffledPositions(size) {
    const total = size * size;
    const indices = Array.from({ length: total }, (_, i) => i);
    do {
      for (let i = indices.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [indices[i], indices[j]] = [indices[j], indices[i]];
      }
    } while (indices.every((v, i) => v === i));
    return indices.slice();
  }

  function setStatus(message, tone) {
    el.gameStatus.textContent = message || "";
    el.gameStatus.className = "status-line";
    if (tone === "success") el.gameStatus.classList.add("is-success");
    if (tone === "error") el.gameStatus.classList.add("is-error");
  }

  function showScreen(screen) {
    el.startScreen.classList.toggle("hidden", screen !== "start");
    el.gameScreen.classList.toggle("hidden", screen !== "game");
    el.completionScreen.classList.toggle("hidden", screen !== "complete");
  }

  function renderStats() {
    const elapsed = state.startedAt ? Math.floor((Date.now() - state.startedAt) / 1000) : state.elapsedSeconds;
    state.elapsedSeconds = elapsed;

    el.timerValue.textContent = state.config.rules.show_timer ? formatTime(elapsed) : "—";
    el.movesValue.textContent = state.config.rules.show_moves ? String(state.moves) : "—";
    el.progressValue.textContent = state.config.rules.show_progress ? `${progressPercent()}%` : "—";
  }

  function piecePosition(pieceIndex) {
    const row = Math.floor(pieceIndex / state.gridSize);
    const col = pieceIndex % state.gridSize;
    const denominator = Math.max(state.gridSize - 1, 1);
    return { x: `${(col * 100) / denominator}%`, y: `${(row * 100) / denominator}%` };
  }

  function swapPieces(sourceIndex, targetIndex) {
    if (sourceIndex === null || targetIndex === null || sourceIndex === targetIndex) {
      state.selectedIndex = null;
      renderBoard();
      return;
    }
    const next = state.positions.slice();
    [next[sourceIndex], next[targetIndex]] = [next[targetIndex], next[sourceIndex]];
    state.positions = next;
    state.moves += 1;
    state.selectedIndex = null;
    renderBoard();
    renderStats();
    if (countCorrectPieces() === totalPieces()) completePuzzle();
  }

  function bindPieceEvents(tile, cellIndex) {
    tile.addEventListener("click", () => {
      if (state.selectedIndex === null) {
        state.selectedIndex = cellIndex;
        renderBoard();
        return;
      }
      swapPieces(state.selectedIndex, cellIndex);
    });

    tile.draggable = true;

    tile.addEventListener("dragstart", () => {
      state.dragSourceIndex = cellIndex;
      state.selectedIndex = cellIndex;
      renderBoard();
    });

    tile.addEventListener("dragover", (e) => { e.preventDefault(); });

    tile.addEventListener("drop", (e) => {
      e.preventDefault();
      swapPieces(state.dragSourceIndex, cellIndex);
      state.dragSourceIndex = null;
    });

    tile.addEventListener("dragend", () => {
      state.dragSourceIndex = null;
      state.selectedIndex = null;
      renderBoard();
    });
  }

  function getPuzzleImage() {
    return safeText(
      state.config?.content?.puzzle_image_url,
      safeText(state.config?.branding?.welcome_image_url, ASSETS.fallbackPuzzleImage || ""),
    );
  }

  function renderBoard() {
    const imageUrl = getPuzzleImage();
    el.board.innerHTML = "";
    el.board.style.setProperty("--grid-size", String(state.gridSize));

    state.positions.forEach((pieceIndex, cellIndex) => {
      const tile = document.createElement("button");
      tile.type = "button";
      tile.className = "puzzle-tile";
      if (cellIndex === state.selectedIndex) tile.classList.add("is-selected");
      if (pieceIndex === cellIndex) tile.classList.add("is-correct");

      const { x, y } = piecePosition(pieceIndex);
      tile.style.backgroundImage = `url(${imageUrl})`;
      tile.style.backgroundPosition = `${x} ${y}`;
      tile.style.setProperty("--grid-size", String(state.gridSize));
      tile.setAttribute("aria-label", `Pieza ${pieceIndex + 1}`);
      bindPieceEvents(tile, cellIndex);
      el.board.appendChild(tile);
    });
  }

  function startTimer() {
    clearInterval(state.timerInterval);
    state.startedAt = Date.now();
    state.elapsedSeconds = 0;
    state.timerInterval = window.setInterval(renderStats, 250);
  }

  function resetPuzzle() {
    state.positions = shuffledPositions(state.gridSize);
    state.moves = 0;
    state.selectedIndex = null;
    state.dragSourceIndex = null;
    state.sessionFinished = false;
    setStatus("Reordená las piezas hasta completar la imagen.");
    renderBoard();
    startTimer();
    renderStats();
  }

  async function completePuzzle() {
    clearInterval(state.timerInterval);
    renderStats();
    setStatus("Puzzle completado.", "success");

    await finishSession({
      result: {
        outcome: "completed",
        elapsed_seconds: state.elapsedSeconds,
        moves: state.moves,
        grid_size: state.gridSize,
        progress: progressPercent(),
      },
      estado_cliente: {
        puzzle_mundial: {
          outcome: "completed",
          elapsed_seconds: state.elapsedSeconds,
          moves: state.moves,
          grid_size: state.gridSize,
        },
      },
    });

    el.completionTitle.textContent = safeText(state.config.texts.completion_title, "¡Golazo!");
    el.completionSubtitle.textContent = safeText(state.config.texts.completion_subtitle, "Completaste el puzzle y cerraste la jugada.");
    el.completionTime.textContent = formatTime(state.elapsedSeconds);
    el.completionMoves.textContent = String(state.moves);
    el.completionGrid.textContent = `${state.gridSize} × ${state.gridSize}`;
    showScreen("complete");
  }

  async function handleExit() {
    if (!state.sessionFinished && state.started) {
      clearInterval(state.timerInterval);
      await finishSession({
        result: {
          outcome: "abandoned",
          elapsed_seconds: state.elapsedSeconds,
          moves: state.moves,
          grid_size: state.gridSize,
          progress: progressPercent(),
        },
        estado_cliente: {
          puzzle_mundial: {
            outcome: "abandoned",
            elapsed_seconds: state.elapsedSeconds,
            moves: state.moves,
          },
        },
      });
    }
    window.location.href = RETURN_URL;
  }

  function applyCustomization() {
    const branding = state.config.branding || {};
    const visual = state.config.visual || {};
    const watermark = state.config.watermark || {};

    document.documentElement.style.setProperty("--puzzle-primary", safeText(branding.primary_color, "#00f5e9"));
    document.documentElement.style.setProperty("--puzzle-secondary", safeText(branding.secondary_color, "#081a2b"));
    document.documentElement.style.setProperty("--puzzle-text", safeText(visual.text_color || visual.question_text_color, "#f4fbff"));
    document.documentElement.style.setProperty("--puzzle-panel-bg", safeText(visual.panel_bg_color, "rgba(8, 26, 43, 0.84)"));
    document.documentElement.style.setProperty("--puzzle-panel-border", safeText(visual.panel_border_color, "#1b6888"));
    document.documentElement.style.setProperty("--puzzle-accent", safeText(visual.accent_color || branding.primary_color, "#00f5e9"));
    document.documentElement.style.setProperty("--puzzle-success", safeText(visual.success_color, "#8ee05f"));
    document.documentElement.style.setProperty("--puzzle-bg-color", safeText(visual.screen_background_color, "#04121f"));

    const backgroundImage = safeText(branding.background_url, "");
    const screenColor = safeText(visual.screen_background_color, "#04121f");
    document.body.style.backgroundImage = backgroundImage
      ? `linear-gradient(180deg, rgba(4,18,31,0.52), rgba(4,18,31,0.82)), url(${backgroundImage})`
      : `linear-gradient(180deg, ${screenColor}, ${screenColor})`;

    el.title.textContent = safeText(state.config.texts.welcome_title, "PUZZLE MUNDIAL");
    el.subtitle.textContent = safeText(state.config.texts.welcome_subtitle, "Armá la imagen del mundial pieza por pieza.");
    el.btnStart.textContent = safeText(state.config.texts.cta_button, "Empezar puzzle");
    el.gameTitle.textContent = safeText(state.config.texts.welcome_title, "Puzzle Mundial");

    const heroSrc = safeText(branding.welcome_image_url, "") || getPuzzleImage();
    if (heroSrc) el.heroImage.src = heroSrc;
    el.referenceImage.src = getPuzzleImage();

    el.logo.classList.toggle("hidden", !branding.logo_url);
    if (branding.logo_url) el.logo.src = branding.logo_url;

    el.metaGrid.textContent = `${state.gridSize} × ${state.gridSize}`;
    el.metaTarget.textContent = `Objetivo ${safeNumber(state.config.rules.timer_seconds, 180)}s`;

    const watermarkEnabled = Boolean(watermark.enabled && branding.watermark_text);
    el.watermark.classList.toggle("hidden", !watermarkEnabled);
    if (watermarkEnabled) {
      el.watermark.textContent = safeText(branding.watermark_text, "");
      el.watermark.style.color = safeText(watermark.color, "#00f5e9");
      el.watermark.style.opacity = String(safeNumber(watermark.opacity, 0.2));
      el.watermark.style.fontSize = `${safeNumber(watermark.font_size, 96)}px`;
    }
  }

  function cacheDom() {
    el.watermark = document.getElementById("watermark");
    el.startScreen = document.getElementById("startScreen");
    el.gameScreen = document.getElementById("gameScreen");
    el.completionScreen = document.getElementById("completionScreen");
    el.logo = document.getElementById("logo");
    el.title = document.getElementById("title");
    el.subtitle = document.getElementById("subtitle");
    el.metaGrid = document.getElementById("metaGrid");
    el.metaTarget = document.getElementById("metaTarget");
    el.btnStart = document.getElementById("btnStart");
    el.heroImage = document.getElementById("heroImage");
    el.gameTitle = document.getElementById("gameTitle");
    el.btnReset = document.getElementById("btnReset");
    el.btnExitGame = document.getElementById("btnExitGame");
    el.gameStatus = document.getElementById("gameStatus");
    el.board = document.getElementById("board");
    el.timerValue = document.getElementById("timerValue");
    el.movesValue = document.getElementById("movesValue");
    el.progressValue = document.getElementById("progressValue");
    el.referenceImage = document.getElementById("referenceImage");
    el.completionTitle = document.getElementById("completionTitle");
    el.completionSubtitle = document.getElementById("completionSubtitle");
    el.completionTime = document.getElementById("completionTime");
    el.completionMoves = document.getElementById("completionMoves");
    el.completionGrid = document.getElementById("completionGrid");
    el.btnPlayAgain = document.getElementById("btnPlayAgain");
  }

  function bindUi() {
    el.btnStart.addEventListener("click", async () => {
      if (!state.session) {
        // Try to create session if not yet done
        const result = await startSession();
        if (result) {
          state.session = { id: result.id, anon_token: result.anon_token };
          state.config = deepMerge(defaultConfig(), result.config || {});
          state.gridSize = clampGridSize(safeNumber(result.config?.rules?.grid_size, 3));
        }
      }
      state.started = true;
      showScreen("game");
      resetPuzzle();
    });

    el.btnReset.addEventListener("click", resetPuzzle);

    if (el.btnExitGame) {
      el.btnExitGame.addEventListener("click", handleExit);
    }

    if (el.btnPlayAgain) {
      el.btnPlayAgain.addEventListener("click", async () => {
        // Create a new session for replay
        const result = await startSession();
        if (result) {
          state.session = { id: result.id, anon_token: result.anon_token };
          state.config = deepMerge(defaultConfig(), result.config || {});
          state.gridSize = clampGridSize(safeNumber(result.config?.rules?.grid_size, 3));
          state.sessionFinished = false;
          state.started = true;
        }
        showScreen("game");
        resetPuzzle();
      });
    }
  }

  async function init() {
    cacheDom();

    // Start session eagerly
    const result = await startSession();
    if (result) {
      state.session = { id: result.id, anon_token: result.anon_token };
      state.config = deepMerge(defaultConfig(), result.config || {});
      state.gridSize = clampGridSize(safeNumber(result.config?.rules?.grid_size, 3));
    } else {
      state.config = defaultConfig();
    }

    applyCustomization();
    bindUi();
    renderStats();
    showScreen("start");
  }

  document.addEventListener("DOMContentLoaded", () => { void init(); });
})();
