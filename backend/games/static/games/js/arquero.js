(function () {
  "use strict";

  const GAME_SLUG = window.GAME_SLUG || "el-del-arquero";
  const RETURN_URL = window.RETURN_URL || "/";
  const GOALKEEPER_VIEWBOX_WIDTH = 120;
  const GOALKEEPER_VIEWBOX_HEIGHT = 150;

  const state = {
    session: null,
    config: null,
    score: 0,
    saves: 0,
    missed: 0,
    bonusCaught: 0,
    penaltyCaught: 0,
    timeLeft: 60,
    balls: [],
    gameState: "start",
    sessionFinished: false,
    isDragging: false,
    dragActivated: false,
    dragStartPointerX: 0,
    dragStartGoalkeeperX: 0,
    activePointerId: null,
    goalkeeperX: 0,
    nextBallId: 1,
    animationFrame: null,
    spawnInterval: null,
    timerInterval: null,
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

  function getCsrfToken() {
    const name = "csrftoken";
    const match = document.cookie.match(new RegExp("(^|;)\\s*" + name + "\\s*=\\s*([^;]+)"));
    return match ? match.pop() : "";
  }

  function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${String(secs).padStart(2, "0")}`;
  }

  // ── Default Config ─────────────────────────────────────────

  function defaultConfig() {
    return {
      branding: {
        primary_color: "#f7c948",
        secondary_color: "#0f3d26",
        logo_url: "",
        background_url: "",
        welcome_image_url: "",
        watermark_text: "",
        ball_image_url: "",
        bonus_ball_image_url: "",
        penalty_ball_image_url: "",
      },
      texts: {
        welcome_title: "EL DEL ARQUERO",
        welcome_subtitle: "Mové al arquero de lado a lado y atajá todos los remates.",
        cta_button: "Tocar para jugar",
        completion_title: "FIN DEL JUEGO",
        completion_subtitle: "Tus reflejos definieron el resultado.",
        instructions_text: "Arrastrá al portero a izquierda y derecha para parar los balones.",
        play_again_button: "Jugar de nuevo",
      },
      rules: {
        show_timer: true,
        timer_seconds: 60,
        show_score: true,
        show_saves: true,
        goalkeeper_width: 120,
        points_per_save: 10,
        ball_speed_min: 4,
        ball_speed_max: 8,
        spawn_interval_ms: 800,
        bonus_ball_enabled: true,
        bonus_points: 25,
        bonus_ball_spawn_chance: 12,
        penalty_ball_enabled: false,
        penalty_points: 10,
        penalty_ball_spawn_chance: 18,
      },
      visual: {
        screen_background_color: "#102a1a",
        field_green_color: "#2b8a3e",
        field_dark_color: "#0b3b23",
        line_color: "#f4f6f2",
        goalkeeper_jersey_color: "#2563eb",
        goalkeeper_detail_color: "#3b82f6",
        goalkeeper_glove_color: "#22c55e",
        accent_color: "#f7c948",
      },
      watermark: { enabled: false },
      content: { sponsor_top_left: "", sponsor_top_right: "", sponsor_bottom: "" },
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

    const { response } = await fetchJSON(
      `/runner/sesiones/${state.session.id}/finalizar`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ anon_token: state.session.anon_token, ...payload }),
      }
    );

    if (!response.ok) state.sessionFinished = false;
  }

  // ── Local high score ───────────────────────────────────────

  function highScoreKey() { return `el-del-arquero:highscore`; }

  function getHighScore() {
    const raw = window.localStorage.getItem(highScoreKey());
    const parsed = raw ? Number.parseInt(raw, 10) : 0;
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function setHighScore(value) {
    window.localStorage.setItem(highScoreKey(), String(value));
  }

  // ── Stage helpers ──────────────────────────────────────────

  function getStageRect() {
    return el.stage?.getBoundingClientRect() || {
      left: 0,
      width: window.innerWidth,
      height: window.innerHeight,
    };
  }

  function clampGoalkeeperX(clientX) {
    const halfWidth = safeNumber(state.config.rules.goalkeeper_width, 110) / 2;
    const { width } = getStageRect();
    const padding = Math.max(halfWidth, 50);
    return Math.max(padding, Math.min(width - padding, clientX));
  }

  // ── Goalkeeper rendering ───────────────────────────────────

  function renderGoalkeeper() {
    const jersey = safeText(state.config.visual.goalkeeper_jersey_color, "#2563eb");
    const detail = safeText(state.config.visual.goalkeeper_detail_color, "#3b82f6");
    const glove = safeText(state.config.visual.goalkeeper_glove_color, "#22c55e");
    const width = safeNumber(state.config.rules.goalkeeper_width, 110);
    const height = Math.round((width / GOALKEEPER_VIEWBOX_WIDTH) * GOALKEEPER_VIEWBOX_HEIGHT);

    el.goalkeeper.style.left = `${state.goalkeeperX}px`;
    el.goalkeeper.style.width = `${width}px`;
    el.goalkeeper.style.height = `${height}px`;
    el.goalkeeper.innerHTML = `
      <svg viewBox="0 0 ${GOALKEEPER_VIEWBOX_WIDTH} ${GOALKEEPER_VIEWBOX_HEIGHT}" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
        <ellipse cx="60" cy="100" rx="30" ry="35" fill="${jersey}" />
        <ellipse cx="60" cy="95" rx="25" ry="28" fill="${detail}" />
        <rect x="50" y="66" width="20" height="54" fill="${jersey}" />
        <ellipse cx="18" cy="84" rx="18" ry="10" fill="${detail}" />
        <circle cx="6" cy="84" r="10" fill="#F4C7A0" />
        <circle cx="6" cy="84" r="8" fill="${glove}" />
        <ellipse cx="102" cy="84" rx="18" ry="10" fill="${detail}" />
        <circle cx="114" cy="84" r="10" fill="#F4C7A0" />
        <circle cx="114" cy="84" r="8" fill="${glove}" />
        <circle cx="60" cy="46" r="25" fill="#F4C7A0" />
        <ellipse cx="60" cy="30" rx="22" ry="12" fill="#4A3728" />
        <circle cx="52" cy="42" r="3" fill="#1F2937" />
        <circle cx="68" cy="42" r="3" fill="#1F2937" />
        <ellipse cx="60" cy="53" rx="6" ry="3" fill="#E5A080" />
        <rect x="48" y="36" width="8" height="2" rx="1" fill="#4A3728" transform="rotate(-10 48 36)" />
        <rect x="64" y="36" width="8" height="2" rx="1" fill="#4A3728" transform="rotate(10 64 36)" />
        <rect x="40" y="120" width="40" height="18" rx="5" fill="#1F2937" />
        <rect x="42" y="136" width="14" height="12" rx="3" fill="#F4C7A0" />
        <rect x="64" y="136" width="14" height="12" rx="3" fill="#F4C7A0" />
        <text x="60" y="104" text-anchor="middle" fill="white" font-size="16" font-weight="bold">1</text>
      </svg>`;
  }

  // ── Balls ──────────────────────────────────────────────────

  function createBall(x, speed, type = "normal") {
    const node = document.createElement("div");
    const className = type === "penalty" ? "penalty-ball" : type === "bonus" ? "bonus-ball" : "regular-ball";
    node.className = `ball ${className}`;
    if (type === "penalty" || type === "bonus") {
      const badge = document.createElement("span");
      badge.className = "ball-badge";
      badge.textContent = type === "bonus" ? "+" : "!";
      node.appendChild(badge);
    }
    el.ballsLayer.appendChild(node);
    return { id: state.nextBallId++, type, x, y: -60, speed, rotation: 0, node };
  }

  function spawnBall() {
    const { width } = getStageRect();
    const padding = Math.min(60, Math.max(32, width * 0.14));
    const x = padding + Math.random() * Math.max(40, width - padding * 2);
    const speedMin = safeNumber(state.config.rules.ball_speed_min, 4);
    const speedMax = safeNumber(state.config.rules.ball_speed_max, 8);
    const speed = speedMin + Math.random() * Math.max(0.5, speedMax - speedMin);
    const bonusEnabled = !!state.config.rules.bonus_ball_enabled;
    const bonusChance = Math.max(0, Math.min(100, safeNumber(state.config.rules.bonus_ball_spawn_chance, 12))) / 100;
    const penaltyEnabled = !!state.config.rules.penalty_ball_enabled;
    const penaltyChance = Math.max(0, Math.min(100, safeNumber(state.config.rules.penalty_ball_spawn_chance, 18))) / 100;
    const roll = Math.random();
    let ballType = "normal";
    if (bonusEnabled && roll < bonusChance) ballType = "bonus";
    else if (penaltyEnabled && roll < bonusChance + penaltyChance) ballType = "penalty";
    state.balls.push(createBall(x, speed, ballType));
  }

  function clearBalls() {
    state.balls.forEach((b) => b.node.remove());
    state.balls = [];
  }

  function removeBall(ball) {
    ball.node.remove();
    state.balls = state.balls.filter((b) => b.id !== ball.id);
  }

  function setStatus(message) {
    el.statusLine.textContent = message || "";
  }

  function handleBallReachedGoal(ball) {
    const keeperWidth = safeNumber(state.config.rules.goalkeeper_width, 110);
    const distance = Math.abs(ball.x - state.goalkeeperX);
    const saved = distance < keeperWidth / 2 + 25;
    removeBall(ball);

    if (saved) {
      if (ball.type === "bonus") {
        const savePoints = Math.max(0, safeNumber(state.config.rules.points_per_save, 10));
        const bonusPoints = Math.max(0, safeNumber(state.config.rules.bonus_points, 25));
        state.score += savePoints + bonusPoints;
        state.saves += 1;
        state.bonusCaught += 1;
        setStatus(`¡Bonus! +${bonusPoints} pts extra`);
      } else if (ball.type === "penalty") {
        const penaltyPoints = Math.max(0, safeNumber(state.config.rules.penalty_points, 10));
        state.score = Math.max(0, state.score - penaltyPoints);
        state.penaltyCaught += 1;
        setStatus(`Trampa: -${penaltyPoints} pts`);
      } else {
        state.score += safeNumber(state.config.rules.points_per_save, 10);
        state.saves += 1;
        setStatus("¡Atajada!");
      }
    } else {
      if (ball.type === "penalty") {
        setStatus("Bien esquivada");
      } else if (ball.type === "bonus") {
        state.missed += 1;
        setStatus("Se escapó la bonus");
      } else {
        state.missed += 1;
        setStatus("Gol recibido");
      }
    }

    updateScoreUi();
  }

  function updateScoreUi() {
    el.scoreValue.textContent = String(state.score);
    el.savesValue.textContent = String(state.saves);
    el.timerValue.textContent = formatTime(state.timeLeft);
    el.scoreBox.classList.toggle("hidden", !state.config.rules.show_score);
    el.savesBox.classList.toggle("hidden", !state.config.rules.show_saves);
  }

  function animate() {
    if (state.gameState !== "game") return;
    const { height } = getStageRect();
    const bottomLimit = Math.max(160, height - 130);
    state.balls.slice().forEach((ball) => {
      ball.y += ball.speed;
      ball.rotation += ball.speed * 2;
      ball.node.style.left = `${ball.x}px`;
      ball.node.style.top = `${ball.y}px`;
      ball.node.style.transform = `translate(-50%, -50%) rotate(${ball.rotation}deg)`;
      if (ball.y > bottomLimit) handleBallReachedGoal(ball);
    });
    state.animationFrame = window.requestAnimationFrame(animate);
  }

  function startSpawning() {
    const interval = Math.max(300, safeNumber(state.config.rules.spawn_interval_ms, 800));
    window.clearInterval(state.spawnInterval);
    spawnBall();
    state.spawnInterval = window.setInterval(() => {
      const elapsed = safeNumber(state.config.rules.timer_seconds, 60) - state.timeLeft;
      const spawnChance = Math.min(0.8, 0.3 + elapsed * 0.01);
      if (Math.random() < spawnChance) spawnBall();
    }, interval);
  }

  function showScreen(name) {
    el.startScreen.classList.toggle("hidden", name !== "start");
    el.gameScreen.classList.toggle("hidden", name !== "game");
    el.gameOverScreen.classList.toggle("hidden", name !== "gameover");
    state.gameState = name;
  }

  async function endGame(reason) {
    window.clearInterval(state.timerInterval);
    window.clearInterval(state.spawnInterval);
    window.cancelAnimationFrame(state.animationFrame);

    const highScore = getHighScore();
    const isNewHighScore = state.score > highScore;
    if (isNewHighScore) setHighScore(state.score);

    await finishSession({
      result: {
        outcome: reason,
        score: state.score,
        saves: state.saves,
        missed: state.missed,
        bonus_caught: state.bonusCaught,
        penalty_caught: state.penaltyCaught,
        duration_seconds: safeNumber(state.config.rules.timer_seconds, 60),
      },
      estado_cliente: {
        el_del_arquero: {
          outcome: reason,
          score: state.score,
          saves: state.saves,
          missed: state.missed,
        },
      },
    });

    el.finalScore.textContent = String(state.score);
    el.finalSaves.textContent = String(state.saves);
    el.finalBonusCaught.textContent = String(state.bonusCaught);
    el.finalMissed.textContent = String(state.missed);
    el.finalPenaltyCaught.textContent = String(state.penaltyCaught);
    el.newRecordBadge.classList.toggle("hidden", !isNewHighScore);
    el.completionTitle.textContent = safeText(state.config.texts.completion_title, "FIN DEL JUEGO");
    el.completionSubtitle.textContent = safeText(state.config.texts.completion_subtitle, "Tus reflejos definieron el resultado.");
    el.btnRestart.textContent = safeText(state.config.texts.play_again_button, "Jugar de nuevo");
    showScreen("gameover");
  }

  async function startGame() {
    // Fresh session for each game
    const result = await startSession();
    if (result) {
      state.session = { id: result.id, anon_token: result.anon_token };
      state.config = deepMerge(defaultConfig(), result.config || {});
      applyCustomization();
    }

    state.score = 0;
    state.saves = 0;
    state.missed = 0;
    state.bonusCaught = 0;
    state.penaltyCaught = 0;
    state.timeLeft = safeNumber(state.config.rules.timer_seconds, 60);
    state.sessionFinished = false;
    state.goalkeeperX = getStageRect().width / 2;
    clearBalls();
    renderGoalkeeper();
    updateScoreUi();
    setStatus("¡Atajá todo lo que puedas!");
    showScreen("game");

    startSpawning();
    state.animationFrame = window.requestAnimationFrame(animate);
    state.timerInterval = window.setInterval(() => {
      state.timeLeft -= 1;
      updateScoreUi();
      if (state.timeLeft <= 0) void endGame("timeout");
    }, 1000);
  }

  function bindPointerControls() {
    const DRAG_THRESHOLD_PX = 12;

    const moveKeeper = (clientX) => {
      if (state.gameState !== "game") return;
      state.goalkeeperX = clampGoalkeeperX(clientX);
      renderGoalkeeper();
    };

    const pointerPositionInStage = (event) => event.clientX - getStageRect().left;

    const stopDragging = (event) => {
      if (state.activePointerId !== null && event.pointerId !== state.activePointerId) return;
      state.isDragging = false;
      state.dragActivated = false;
      state.activePointerId = null;
      state.dragStartPointerX = 0;
      state.dragStartGoalkeeperX = state.goalkeeperX;
      try { el.goalkeeper.releasePointerCapture(event.pointerId); } catch { /**/ }
    };

    el.goalkeeper.addEventListener("pointerdown", (event) => {
      if (state.gameState !== "game") return;
      event.preventDefault();
      state.isDragging = true;
      state.dragActivated = false;
      state.activePointerId = event.pointerId;
      state.dragStartPointerX = pointerPositionInStage(event);
      state.dragStartGoalkeeperX = state.goalkeeperX;
      try { el.goalkeeper.setPointerCapture(event.pointerId); } catch { /**/ }
    });

    window.addEventListener("pointermove", (event) => {
      if (!state.isDragging || event.pointerId !== state.activePointerId) return;
      const deltaX = pointerPositionInStage(event) - state.dragStartPointerX;
      if (!state.dragActivated && Math.abs(deltaX) < DRAG_THRESHOLD_PX) return;
      state.dragActivated = true;
      event.preventDefault();
      moveKeeper(state.dragStartGoalkeeperX + deltaX);
    });

    window.addEventListener("pointerup", stopDragging);
    window.addEventListener("pointercancel", stopDragging);
    el.goalkeeper.addEventListener("lostpointercapture", stopDragging);

    window.addEventListener("resize", () => {
      const stageWidth = getStageRect().width;
      state.goalkeeperX = clampGoalkeeperX(state.goalkeeperX || stageWidth / 2);
      renderGoalkeeper();
    });
  }

  function applyCustomization() {
    const branding = state.config.branding;
    const texts = state.config.texts;
    const visual = state.config.visual;
    const rules = state.config.rules;
    const content = state.config.content || {};
    const watermark = state.config.watermark || {};

    document.documentElement.style.setProperty("--keeper-primary", safeText(branding.primary_color, "#f7c948"));
    document.documentElement.style.setProperty("--keeper-secondary", safeText(branding.secondary_color, "#0f3d26"));
    document.documentElement.style.setProperty("--keeper-field-green", safeText(visual.field_green_color, "#2b8a3e"));
    document.documentElement.style.setProperty("--keeper-field-dark", safeText(visual.field_dark_color, "#0b3b23"));
    document.documentElement.style.setProperty("--keeper-line", safeText(visual.line_color, "#f4f6f2"));
    document.documentElement.style.setProperty("--keeper-jersey", safeText(visual.goalkeeper_jersey_color, "#2563eb"));
    document.documentElement.style.setProperty("--keeper-jersey-detail", safeText(visual.goalkeeper_detail_color, "#3b82f6"));
    document.documentElement.style.setProperty("--keeper-glove", safeText(visual.goalkeeper_glove_color, "#22c55e"));

    if (branding.ball_image_url) {
      document.documentElement.style.setProperty("--keeper-ball-image", `url(${branding.ball_image_url})`);
      document.documentElement.classList.add("has-custom-ball");
    } else {
      document.documentElement.style.removeProperty("--keeper-ball-image");
      document.documentElement.classList.remove("has-custom-ball");
    }

    if (branding.bonus_ball_image_url) {
      document.documentElement.style.setProperty("--keeper-bonus-ball-image", `url(${branding.bonus_ball_image_url})`);
      document.documentElement.classList.add("has-custom-bonus-ball");
    } else {
      document.documentElement.style.removeProperty("--keeper-bonus-ball-image");
      document.documentElement.classList.remove("has-custom-bonus-ball");
    }

    if (branding.penalty_ball_image_url) {
      document.documentElement.style.setProperty("--keeper-penalty-ball-image", `url(${branding.penalty_ball_image_url})`);
      document.documentElement.classList.add("has-custom-penalty-ball");
    } else {
      document.documentElement.style.removeProperty("--keeper-penalty-ball-image");
      document.documentElement.classList.remove("has-custom-penalty-ball");
    }

    document.body.style.backgroundImage = branding.background_url
      ? `linear-gradient(180deg, rgba(11, 59, 35, 0.28), rgba(11, 59, 35, 0.52)), url(${branding.background_url})`
      : `linear-gradient(180deg, ${safeText(visual.screen_background_color, "#102a1a")}, ${safeText(visual.screen_background_color, "#102a1a")})`;

    el.logo.classList.toggle("hidden", !branding.logo_url);
    if (branding.logo_url) el.logo.src = branding.logo_url;

    el.heroImage.classList.toggle("hidden", !branding.welcome_image_url);
    if (branding.welcome_image_url) el.heroImage.src = branding.welcome_image_url;

    el.title.textContent = safeText(texts.welcome_title, "EL DEL ARQUERO");
    el.subtitle.textContent = safeText(texts.welcome_subtitle, "Mové al arquero de lado a lado y atajá todos los remates.");

    const defaultInstructions = "Arrastrá al portero a izquierda y derecha para parar los balones.";
    const bonusInstructions = rules.bonus_ball_enabled
      ? ` Agarrá la pelota bonus para sumar ${safeNumber(rules.bonus_points, 25)} pts extra.`
      : "";
    const penaltyInstructions = rules.penalty_ball_enabled
      ? ` Evitá la pelota trampa: si la atajás te descuenta ${safeNumber(rules.penalty_points, 10)} pts.`
      : "";
    el.instructions.textContent = `${safeText(texts.instructions_text, defaultInstructions)}${bonusInstructions}${penaltyInstructions}`;

    el.btnStart.textContent = safeText(texts.cta_button, "Tocar para jugar");
    el.metaDuration.textContent = `${safeNumber(rules.timer_seconds, 60)}s`;
    el.metaPoints.textContent = String(safeNumber(rules.points_per_save, 10));
    el.metaHighScore.textContent = String(getHighScore());
    el.metaBonus.textContent = rules.bonus_ball_enabled ? `+${safeNumber(rules.bonus_points, 25)} pts` : "Off";
    el.metaPenalty.textContent = rules.penalty_ball_enabled ? `-${safeNumber(rules.penalty_points, 10)} pts` : "Off";

    // Sponsors
    const sponsorLeft = safeText(content.sponsor_top_left, "");
    const sponsorRight = safeText(content.sponsor_top_right, "");
    const sponsorBottom = safeText(content.sponsor_bottom, "");
    el.sponsorLeft.textContent = sponsorLeft;
    el.sponsorRight.textContent = sponsorRight;
    el.sponsorBottom.textContent = sponsorBottom;
    el.sponsorLeft.closest(".sponsor-slot").classList.toggle("hidden", !sponsorLeft);
    el.sponsorRight.closest(".sponsor-slot").classList.toggle("hidden", !sponsorRight);
    el.sponsorBottom.closest(".sponsor-slot").classList.toggle("hidden", !sponsorBottom);

    const watermarkEnabled = Boolean(watermark.enabled && branding.watermark_text);
    el.watermark.classList.toggle("hidden", !watermarkEnabled);
    if (watermarkEnabled) {
      el.watermark.textContent = safeText(branding.watermark_text, "");
      el.watermark.style.color = safeText(watermark.color, branding.primary_color || "#f7c948");
      el.watermark.style.opacity = String(safeNumber(watermark.opacity, 0.18));
      el.watermark.style.fontSize = `${safeNumber(watermark.font_size, 96)}px`;
    }

    updateScoreUi();
    renderGoalkeeper();
  }

  function cacheDom() {
    el.stage = document.getElementById("stage");
    el.watermark = document.getElementById("watermark");
    el.startScreen = document.getElementById("startScreen");
    el.gameScreen = document.getElementById("gameScreen");
    el.gameOverScreen = document.getElementById("gameOverScreen");
    el.logo = document.getElementById("logo");
    el.heroImage = document.getElementById("heroImage");
    el.title = document.getElementById("title");
    el.subtitle = document.getElementById("subtitle");
    el.instructions = document.getElementById("instructions");
    el.metaDuration = document.getElementById("metaDuration");
    el.metaPoints = document.getElementById("metaPoints");
    el.metaHighScore = document.getElementById("metaHighScore");
    el.metaBonus = document.getElementById("metaBonus");
    el.metaPenalty = document.getElementById("metaPenalty");
    el.btnStart = document.getElementById("btnStart");
    el.scoreBox = document.getElementById("scoreBox");
    el.savesBox = document.getElementById("savesBox");
    el.scoreValue = document.getElementById("scoreValue");
    el.timerValue = document.getElementById("timerValue");
    el.savesValue = document.getElementById("savesValue");
    el.sponsorLeft = document.getElementById("sponsorLeft");
    el.sponsorRight = document.getElementById("sponsorRight");
    el.sponsorBottom = document.getElementById("sponsorBottom");
    el.statusLine = document.getElementById("statusLine");
    el.ballsLayer = document.getElementById("ballsLayer");
    el.goalkeeper = document.getElementById("goalkeeper");
    el.newRecordBadge = document.getElementById("newRecordBadge");
    el.completionTitle = document.getElementById("completionTitle");
    el.completionSubtitle = document.getElementById("completionSubtitle");
    el.finalScore = document.getElementById("finalScore");
    el.finalSaves = document.getElementById("finalSaves");
    el.finalBonusCaught = document.getElementById("finalBonusCaught");
    el.finalMissed = document.getElementById("finalMissed");
    el.finalPenaltyCaught = document.getElementById("finalPenaltyCaught");
    el.btnRestart = document.getElementById("btnRestart");
  }

  function bindUi() {
    el.btnStart.addEventListener("click", () => void startGame());
    el.btnRestart.addEventListener("click", () => void startGame());
    bindPointerControls();
  }

  async function init() {
    cacheDom();

    const result = await startSession();
    if (result) {
      state.session = { id: result.id, anon_token: result.anon_token };
      state.config = deepMerge(defaultConfig(), result.config || {});
    } else {
      state.config = defaultConfig();
    }

    state.timeLeft = safeNumber(state.config.rules.timer_seconds, 60);
    state.goalkeeperX = getStageRect().width / 2;

    applyCustomization();
    bindUi();
    showScreen("start");
  }

  document.addEventListener("DOMContentLoaded", () => { void init(); });
})();
