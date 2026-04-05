(function () {
  "use strict";

  const GAME_SLUG = window.GAME_SLUG || "trivia-mundial-fotos";
  const RETURN_URL = window.RETURN_URL || "/";
  const ASSETS = window.TRIVIA_MUNDIAL_FOTOS_ASSETS || {};

  const optionLetters = ["A", "B", "C", "D"];

  const state = {
    session: null,
    config: null,
    questions: [],
    currentIndex: 0,
    timer: 15,
    timerInterval: null,
    awaitingNextQuestion: false,
    answerLocked: false,
    sessionFinished: false,
    score: 0,
    correctAnswers: 0,
    timedOutAnswers: 0,
    startedAt: null,
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

  // ── Default Config ─────────────────────────────────────────

  function defaultConfig() {
    return {
      branding: {
        primary_color: "#8ad8ff",
        secondary_color: "#081a2b",
        logo_url: "",
        background_url: "",
        welcome_image_url: "",
        watermark_text: "",
      },
      texts: {
        welcome_title: "TRIVIA MUNDIAL FOTOS",
        welcome_subtitle: "Reconocé momentos y protagonistas del Mundial en una trivia visual rápida.",
        cta_button: "Comenzar partido",
        completion_title: "FINAL DEL PARTIDO",
        completion_subtitle: "Repasá tu marcador y jugá de nuevo.",
      },
      rules: {
        show_timer: true,
        timer_seconds: 15,
        points_per_correct: 100,
        max_questions: 5,
      },
      visual: {
        screen_background_color: "#050e1a",
        panel_bg_color: "rgba(7, 20, 36, 0.82)",
        panel_border_color: "#1d5f80",
        text_color: "#f8fcff",
        accent_color: "#8ad8ff",
        success_color: "#44e3a2",
        danger_color: "#ff6b7a",
        chip_bg_color: "rgba(18, 50, 74, 0.84)",
      },
      watermark: { enabled: false },
      content: { sparkle_questions: [], question_pack_image_url: "" },
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

    const { response, data } = await fetchJSON(
      `/runner/sesiones/${state.session.id}/finalizar`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ anon_token: state.session.anon_token, ...payload }),
      }
    );

    if (!response.ok) state.sessionFinished = false;
    return data;
  }

  // ── Questions ──────────────────────────────────────────────

  function sampleQuestions() {
    return [
      {
        id: "worldcup-year",
        question: "¿En qué año Argentina ganó su tercer Mundial de Fútbol?",
        image: ASSETS.heroImage || "",
        answers: [
          { id: "a1", label: "2018", imageUrl: "" },
          { id: "a2", label: "2022", imageUrl: "" },
          { id: "a3", label: "2014", imageUrl: "" },
        ],
        correctAnswerId: "a2",
      },
      {
        id: "messi-goals",
        question: "¿Cuántos goles marcó Messi en el Mundial de Qatar 2022?",
        image: "",
        answers: [
          { id: "b1", label: "5 goles", imageUrl: "" },
          { id: "b2", label: "7 goles", imageUrl: "" },
          { id: "b3", label: "8 goles", imageUrl: "" },
        ],
        correctAnswerId: "b2",
      },
      {
        id: "keeper-final",
        question: "¿Quién fue el arquero de Argentina en la final del Mundial 2022?",
        image: "",
        answers: [
          { id: "c1", label: "Franco Armani", imageUrl: "" },
          { id: "c2", label: "Emiliano Martínez", imageUrl: "" },
          { id: "c3", label: "Gerónimo Rulli", imageUrl: "" },
        ],
        correctAnswerId: "c2",
      },
      {
        id: "final-rival",
        question: "¿Contra qué selección jugó Argentina la final del Mundial 2022?",
        image: "",
        answers: [
          { id: "d1", label: "Brasil", imageUrl: "" },
          { id: "d2", label: "Francia", imageUrl: "" },
          { id: "d3", label: "Alemania", imageUrl: "" },
        ],
        correctAnswerId: "d2",
      },
      {
        id: "total-mundiales",
        question: "¿Cuántos Mundiales ganó Argentina en total?",
        image: "",
        answers: [
          { id: "e1", label: "2", imageUrl: "" },
          { id: "e2", label: "3", imageUrl: "" },
          { id: "e3", label: "4", imageUrl: "" },
        ],
        correctAnswerId: "e2",
      },
    ];
  }

  function normalizeConfiguredQuestions(rawQuestions) {
    if (!Array.isArray(rawQuestions) || rawQuestions.length === 0) return [];

    return rawQuestions
      .map((q, qi) => {
        if (!q || typeof q !== "object") return null;
        const prompt = safeText(q.prompt, "");
        const answers = Array.isArray(q.answers)
          ? q.answers.map((a, ai) => {
              if (!a || typeof a !== "object") return null;
              const label = safeText(a.label, "");
              const imageUrl = safeText(a.imageUrl || a.image_url, "");
              if (!label && !imageUrl) return null;
              return { id: safeText(a.id, `a-${qi}-${ai}`), label, imageUrl };
            }).filter(Boolean)
          : [];

        if (!prompt || answers.length < 2) return null;

        const correctAnswerId = answers.some((a) => a.id === q.correctAnswerId)
          ? q.correctAnswerId
          : answers[0].id;

        return {
          id: safeText(q.id, `q-${qi}`),
          question: prompt,
          image: safeText(q.questionImageUrl || q.question_image_url, ""),
          answers,
          correctAnswerId,
        };
      })
      .filter(Boolean);
  }

  // ── Game Logic ─────────────────────────────────────────────

  function currentQuestion() { return state.questions[state.currentIndex] || null; }

  function showScreen(name) {
    el.startScreen.classList.toggle("hidden", name !== "start");
    el.gameScreen.classList.toggle("hidden", name !== "game");
    el.completionScreen.classList.toggle("hidden", name !== "complete");
  }

  function setFeedback(message, tone) {
    el.feedbackText.textContent = message || "";
    el.feedbackText.className = "feedback-text";
    if (tone === "success") el.feedbackText.classList.add("is-success");
    if (tone === "danger") el.feedbackText.classList.add("is-danger");
  }

  function updateHeader() {
    const total = state.questions.length || 1;
    const timerSeconds = safeNumber(state.config.rules.timer_seconds, 15);
    const timerPercent = Math.max(0, Math.min(100, (state.timer / timerSeconds) * 100));

    el.progressValue.textContent = `${state.currentIndex + 1} / ${total}`;
    el.scoreValue.textContent = String(state.score);
    el.timerValue.textContent = `${state.timer}s`;
    el.timerFill.style.width = `${timerPercent}%`;
    el.timerFill.style.background = state.timer <= 5
      ? "linear-gradient(90deg, var(--trivia-danger), #ff9a84)"
      : "linear-gradient(90deg, var(--trivia-accent), #ffec99)";
  }

  function renderQuestion() {
    const question = currentQuestion();
    if (!question) return;
    const fallbackQuestionImage = safeText(state.config.content?.question_pack_image_url, "");
    const resolvedQuestionImage = safeText(question.image, fallbackQuestionImage);

    el.questionText.textContent = question.question;

    const hasImage = Boolean(resolvedQuestionImage);
    el.questionVisual.classList.toggle("hidden", !hasImage);
    if (hasImage) {
      el.questionImage.src = resolvedQuestionImage;
      el.questionImage.alt = question.question;
    }

    el.answersGrid.innerHTML = "";
    setFeedback("", "");

    const hasImageAnswers = question.answers.some((a) => a.imageUrl);
    el.answersGrid.classList.toggle("has-image-answers", hasImageAnswers);
    el.answersGrid.classList.toggle("has-four-answers", question.answers.length >= 4);

    question.answers.forEach((answer, index) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "answer-button";
      if (answer.imageUrl) {
        button.classList.add("has-image-answer");
      } else {
        button.classList.add("text-answer-only");
      }
      button.innerHTML = `
        <span class="answer-index">${optionLetters[index] || index + 1}</span>
        ${answer.imageUrl ? `<span class="answer-media"><img src="${answer.imageUrl}" alt="${answer.label || `Respuesta ${index + 1}`}" /></span>` : ""}
        <span class="answer-label">${answer.label}</span>
      `;
      button.addEventListener("click", () => void handleAnswer(answer.id));
      el.answersGrid.appendChild(button);
    });

    updateHeader();
  }

  function lockAnswers() {
    el.answersGrid.querySelectorAll(".answer-button").forEach((b) => {
      b.classList.add("is-disabled");
      b.disabled = true;
    });
  }

  function markAnswers(selectedAnswerId, timedOut) {
    const question = currentQuestion();
    const buttons = Array.from(el.answersGrid.querySelectorAll(".answer-button"));
    buttons.forEach((button, index) => {
      const answer = question.answers[index];
      if (!answer) return;
      button.classList.remove("is-correct", "is-incorrect");
      if (answer.id === question.correctAnswerId) {
        button.classList.add("is-correct");
      } else if (!timedOut && answer.id === selectedAnswerId) {
        button.classList.add("is-incorrect");
      }
    });
  }

  function clearTimer() {
    window.clearInterval(state.timerInterval);
    state.timerInterval = null;
  }

  function startQuestionTimer() {
    clearTimer();
    state.timer = safeNumber(state.config.rules.timer_seconds, 15);
    updateHeader();
    if (!state.config.rules.show_timer) return;
    state.timerInterval = window.setInterval(() => {
      state.timer -= 1;
      updateHeader();
      if (state.timer <= 0) { clearTimer(); void handleTimeout(); }
    }, 1000);
  }

  function accuracyPercent() {
    const total = state.questions.length || 1;
    return Math.round((state.correctAnswers / total) * 100);
  }

  async function goToCompletion(outcome) {
    clearTimer();
    const elapsed = state.startedAt ? Math.max(1, Math.round((Date.now() - state.startedAt) / 1000)) : 0;

    await finishSession({
      result: {
        outcome,
        score: state.score,
        correct_answers: state.correctAnswers,
        timed_out_answers: state.timedOutAnswers,
        total_questions: state.questions.length,
        accuracy: accuracyPercent(),
        elapsed_seconds: elapsed,
      },
      estado_cliente: {
        trivia_mundial_fotos: {
          outcome,
          score: state.score,
          correct_answers: state.correctAnswers,
          timed_out_answers: state.timedOutAnswers,
          total_questions: state.questions.length,
        },
      },
    });

    el.completionTitle.textContent = safeText(state.config.texts.completion_title, "FINAL DEL PARTIDO");
    el.completionSubtitle.textContent = safeText(state.config.texts.completion_subtitle, "Repasá tu marcador y jugá de nuevo.");
    el.finalScore.textContent = String(state.score);
    el.finalCorrect.textContent = String(state.correctAnswers);
    el.finalAccuracy.textContent = `${accuracyPercent()}%`;
    el.finalTimeouts.textContent = String(state.timedOutAnswers);
    showScreen("complete");
  }

  function advanceQuestion() {
    state.awaitingNextQuestion = false;
    state.answerLocked = false;

    if (state.currentIndex >= state.questions.length - 1) {
      void goToCompletion("completed");
      return;
    }

    state.currentIndex += 1;
    renderQuestion();
    startQuestionTimer();
  }

  async function handleAnswer(answerId) {
    if (state.answerLocked || state.awaitingNextQuestion) return;
    const question = currentQuestion();
    if (!question) return;

    state.answerLocked = true;
    state.awaitingNextQuestion = true;
    clearTimer();
    lockAnswers();
    markAnswers(answerId, false);

    if (answerId === question.correctAnswerId) {
      state.correctAnswers += 1;
      state.score += safeNumber(state.config.rules.points_per_correct, 100);
      setFeedback("¡Correcto! Sumaste puntos.", "success");
    } else {
      setFeedback("No era esa. Mirá la correcta.", "danger");
    }

    updateHeader();
    window.setTimeout(advanceQuestion, 1600);
  }

  async function handleTimeout() {
    if (state.answerLocked || state.awaitingNextQuestion) return;
    state.answerLocked = true;
    state.awaitingNextQuestion = true;
    state.timedOutAnswers += 1;
    lockAnswers();
    markAnswers(-1, true);
    setFeedback("Se terminó el tiempo.", "danger");
    window.setTimeout(advanceQuestion, 1600);
  }

  function resetStateForNewGame() {
    state.currentIndex = 0;
    state.score = 0;
    state.correctAnswers = 0;
    state.timedOutAnswers = 0;
    state.sessionFinished = false;
    state.awaitingNextQuestion = false;
    state.answerLocked = false;
    state.startedAt = Date.now();
  }

  async function startGame() {
    // Always start a fresh session for each game
    const result = await startSession();
    if (result) {
      state.session = { id: result.id, anon_token: result.anon_token };
      const merged = deepMerge(defaultConfig(), result.config || {});
      state.config = merged;

      // Build question list
      const configuredQuestions = normalizeConfiguredQuestions(state.config.content?.sparkle_questions);
      const sourceQuestions = configuredQuestions.length > 0 ? configuredQuestions : sampleQuestions();
      const maxQ = Math.max(1, safeNumber(state.config.rules.max_questions, sourceQuestions.length));
      state.questions = sourceQuestions.slice(0, maxQ);

      applyCustomization();
    }

    resetStateForNewGame();
    renderQuestion();
    startQuestionTimer();
    showScreen("game");
  }

  function applyCustomization() {
    const branding = state.config.branding || {};
    const visual = state.config.visual || {};
    const watermark = state.config.watermark || {};
    const rules = state.config.rules || {};
    const questionsCount = Math.min(state.questions.length, safeNumber(rules.max_questions, state.questions.length));

    document.documentElement.style.setProperty("--trivia-primary", safeText(branding.primary_color, "#8ad8ff"));
    document.documentElement.style.setProperty("--trivia-secondary", safeText(branding.secondary_color, "#081a2b"));
    document.documentElement.style.setProperty("--trivia-accent", safeText(visual.accent_color, "#f4ca43"));
    document.documentElement.style.setProperty("--trivia-bg", safeText(visual.screen_background_color, "#050e1a"));
    document.documentElement.style.setProperty("--trivia-panel-bg", safeText(visual.panel_bg_color, "rgba(7, 20, 36, 0.82)"));
    document.documentElement.style.setProperty("--trivia-panel-border", safeText(visual.panel_border_color, "#1d5f80"));
    document.documentElement.style.setProperty("--trivia-chip-bg", safeText(visual.chip_bg_color, "rgba(18, 50, 74, 0.84)"));
    document.documentElement.style.setProperty("--trivia-text", safeText(visual.text_color, "#f8fcff"));
    document.documentElement.style.setProperty("--trivia-muted", safeText(visual.muted_text_color, "rgba(248, 252, 255, 0.72)"));
    document.documentElement.style.setProperty("--trivia-success", safeText(visual.success_color, "#44e3a2"));
    document.documentElement.style.setProperty("--trivia-danger", safeText(visual.danger_color, "#ff6b7a"));

    const screenColor = safeText(visual.screen_background_color, "#050e1a");
    document.body.style.backgroundImage = branding.background_url
      ? `radial-gradient(circle at top, rgba(138, 216, 255, 0.16), transparent 30%), linear-gradient(180deg, rgba(5, 14, 26, 0.28), rgba(5, 14, 26, 0.82)), url(${branding.background_url})`
      : `radial-gradient(circle at top, rgba(138, 216, 255, 0.15), transparent 28%), linear-gradient(180deg, ${screenColor} 0%, ${screenColor} 100%)`;

    el.title.textContent = safeText(state.config.texts.welcome_title, "TRIVIA MUNDIAL FOTOS");
    el.subtitle.textContent = safeText(state.config.texts.welcome_subtitle, "Reconocé momentos y protagonistas del Mundial en una trivia visual rápida.");
    el.btnStart.textContent = safeText(state.config.texts.cta_button, "Comenzar partido");
    el.heroImage.src = branding.welcome_image_url || ASSETS.heroImage || "";
    el.eventLogo.classList.toggle("hidden", !branding.logo_url);
    if (branding.logo_url) el.eventLogo.src = branding.logo_url;

    el.metaQuestions.textContent = String(questionsCount);
    el.metaTimer.textContent = `${safeNumber(rules.timer_seconds, 15)}s`;
    el.metaPoints.textContent = String(safeNumber(rules.points_per_correct, 100));
    el.timerBox.classList.toggle("hidden", !rules.show_timer);

    const watermarkEnabled = Boolean(watermark.enabled && branding.watermark_text);
    el.watermark.classList.toggle("hidden", !watermarkEnabled);
    if (watermarkEnabled) {
      el.watermark.textContent = safeText(branding.watermark_text, "");
      el.watermark.style.color = safeText(watermark.color, "#8ad8ff");
      el.watermark.style.opacity = String(safeNumber(watermark.opacity, 0.2));
      el.watermark.style.fontSize = `${safeNumber(watermark.font_size, 96)}px`;
    }
  }

  function cacheDom() {
    el.watermark = document.getElementById("watermark");
    el.startScreen = document.getElementById("startScreen");
    el.gameScreen = document.getElementById("gameScreen");
    el.completionScreen = document.getElementById("completionScreen");
    el.eventLogo = document.getElementById("eventLogo");
    el.title = document.getElementById("title");
    el.subtitle = document.getElementById("subtitle");
    el.metaQuestions = document.getElementById("metaQuestions");
    el.metaTimer = document.getElementById("metaTimer");
    el.metaPoints = document.getElementById("metaPoints");
    el.btnStart = document.getElementById("btnStart");
    el.heroImage = document.getElementById("heroImage");
    el.progressValue = document.getElementById("progressValue");
    el.scoreValue = document.getElementById("scoreValue");
    el.timerBox = document.getElementById("timerBox");
    el.timerValue = document.getElementById("timerValue");
    el.timerFill = document.getElementById("timerFill");
    el.questionText = document.getElementById("questionText");
    el.feedbackText = document.getElementById("feedbackText");
    el.questionVisual = document.getElementById("questionVisual");
    el.questionImage = document.getElementById("questionImage");
    el.answersGrid = document.getElementById("answersGrid");
    el.completionTitle = document.getElementById("completionTitle");
    el.completionSubtitle = document.getElementById("completionSubtitle");
    el.finalScore = document.getElementById("finalScore");
    el.finalCorrect = document.getElementById("finalCorrect");
    el.finalAccuracy = document.getElementById("finalAccuracy");
    el.finalTimeouts = document.getElementById("finalTimeouts");
    el.btnRestart = document.getElementById("btnRestart");
  }

  function bindUi() {
    el.btnStart.addEventListener("click", () => void startGame());
    el.btnRestart.addEventListener("click", () => void startGame());
  }

  async function init() {
    cacheDom();

    // Pre-load config to show correct metadata on start screen
    const result = await startSession();
    if (result) {
      state.session = { id: result.id, anon_token: result.anon_token };
      state.config = deepMerge(defaultConfig(), result.config || {});

      const configuredQuestions = normalizeConfiguredQuestions(state.config.content?.sparkle_questions);
      const sourceQuestions = configuredQuestions.length > 0 ? configuredQuestions : sampleQuestions();
      const maxQ = Math.max(1, safeNumber(state.config.rules.max_questions, sourceQuestions.length));
      state.questions = sourceQuestions.slice(0, maxQ);
    } else {
      state.config = defaultConfig();
      state.questions = sampleQuestions().slice(0, 5);
    }

    applyCustomization();
    bindUi();
    showScreen("start");
  }

  document.addEventListener("DOMContentLoaded", () => { void init(); });
})();
