(function () {
  "use strict";

  const app = document.getElementById("customizerApp");
  if (!app) return;

  const gameSlug = app.dataset.gameSlug;
  const saveUrl = app.dataset.saveUrl;
  const previewUrl = app.dataset.previewUrl;

  const form = document.getElementById("customizerForm");
  const saveButton = document.getElementById("saveButton");
  const paletteButton = document.getElementById("paletteButton");
  const focusPreviewButton = document.getElementById("focusPreviewButton");
  const saveStatus = document.getElementById("saveStatus");

  const configFields = Array.from(form.querySelectorAll("[data-config-field='true']"));
  const fileInputs = Array.from(form.querySelectorAll("[data-asset-input]"));
  const clearButtons = Array.from(form.querySelectorAll("[data-asset-clear-button]"));
  const swatchButtons = Array.from(document.querySelectorAll("[data-color-trigger]"));
  const nativeColorInputs = Array.from(document.querySelectorAll("[data-color-native]"));
  const triviaEditorFields = Array.from(form.querySelectorAll("[data-trivia-editor-field='true']"));
  const triviaQuestionBlocks = Array.from(form.querySelectorAll("[data-trivia-question='true']"));
  const triviaAnswerClearButtons = Array.from(form.querySelectorAll("[data-trivia-answer-clear='true']"));
  const triviaResponseTypeInputs = Array.from(form.querySelectorAll("[data-trivia-response-type='true']"));
  const embeddedSaveButtons = Array.from(document.querySelectorAll("[data-save-trigger='questions']"));
  const triviaQuestionCountInput = document.getElementById("triviaQuestionCount");

  const preview = {
    genericExperience: document.getElementById("previewGenericExperience"),
    triviaExperience: document.getElementById("previewTriviaExperience"),
    stage: document.getElementById("previewStage"),
    logo: document.getElementById("previewLogo"),
    title: document.getElementById("previewTitle"),
    subtitle: document.getElementById("previewSubtitle"),
    heroImage: document.getElementById("previewHeroImage"),
    heroFallback: document.getElementById("previewHeroFallback"),
    button: document.getElementById("previewButton"),
    badge: document.getElementById("previewBadge"),
    watermark: document.getElementById("previewWatermark"),
    metaOne: document.getElementById("previewMetaOne"),
    metaTwo: document.getElementById("previewMetaTwo"),
    metaThree: document.getElementById("previewMetaThree"),
    metaFour: document.getElementById("previewMetaFour"),
    supportText: document.getElementById("previewSupportText"),
    triviaBadge: document.getElementById("previewTriviaBadge"),
    triviaProgress: document.getElementById("previewTriviaProgress"),
    triviaScore: document.getElementById("previewTriviaScore"),
    triviaTimer: document.getElementById("previewTriviaTimer"),
    triviaTimerFill: document.getElementById("previewTriviaTimerFill"),
    triviaImage: document.getElementById("previewTriviaImage"),
    triviaFallback: document.getElementById("previewTriviaFallback"),
    triviaQuestionText: document.getElementById("previewTriviaQuestionText"),
    triviaAnswerOne: document.getElementById("previewTriviaAnswerOne"),
    triviaAnswerTwo: document.getElementById("previewTriviaAnswerTwo"),
    triviaAnswerThree: document.getElementById("previewTriviaAnswerThree"),
    triviaAnswerFour: document.getElementById("previewTriviaAnswerFour"),
  };

  const initialConfig = parseJsonScript("initial-config");
  const defaultConfig = parseJsonScript("default-config");
  let dirty = false;

  function parseJsonScript(id) {
    const node = document.getElementById(id);
    return node ? JSON.parse(node.textContent) : {};
  }

  function clone(value) {
    if (typeof structuredClone === "function") return structuredClone(value);
    return JSON.parse(JSON.stringify(value));
  }

  function safeText(value, fallback) {
    return typeof value === "string" && value.trim() ? value.trim() : fallback;
  }

  function safeNumber(value, fallback) {
    return typeof value === "number" && Number.isFinite(value) ? value : fallback;
  }

  function isHexColor(value) {
    return typeof value === "string" && /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.test(value.trim());
  }

  function parseValue(node) {
    if (node.type === "checkbox") return node.checked;
    if (node.tagName === "SELECT") {
      return /^-?\d+(\.\d+)?$/.test(node.value) ? Number(node.value) : node.value;
    }
    if (node.type === "number") {
      if (!node.value.trim()) return null;
      return node.step && node.step !== "1"
        ? Number.parseFloat(node.value)
        : Number.parseInt(node.value, 10);
    }
    return node.value;
  }

  function readConfigFromForm() {
    const config = clone(defaultConfig);
    configFields.forEach((node) => {
      const section = node.dataset.section;
      const key = node.dataset.key;
      config[section] = config[section] || {};
      config[section][key] = parseValue(node);
    });
    return config;
  }

  function setFieldValue(fieldName, nextValue) {
    const input = form.querySelector(`[name="${fieldName}"]`);
    if (!input) return;
    if (input.type === "checkbox") {
      input.checked = Boolean(nextValue);
      return;
    }
    input.value = nextValue ?? "";
  }

  function populateForm(config) {
    configFields.forEach((node) => {
      const section = node.dataset.section;
      const key = node.dataset.key;
      const value = config?.[section]?.[key];

      if (node.type === "checkbox") {
        node.checked = Boolean(value);
        return;
      }

      node.value = value === null || value === undefined ? "" : String(value);
    });

    fileInputs.forEach((node) => {
      node.value = "";
    });
    document.querySelectorAll("[data-asset-clear]").forEach((node) => {
      node.value = "0";
    });
    refreshColorInputs();
    refreshAssetPreviews();
  }

  function refreshColorInputs() {
    swatchButtons.forEach((button) => {
      const fieldName = button.dataset.colorTrigger;
      const textInput = document.querySelector(`[data-color-text="${fieldName}"]`);
      const nativeInput = document.querySelector(`[data-color-native="${fieldName}"]`);
      const value = textInput ? textInput.value.trim() : "";
      const swatchValue = isHexColor(value) ? value : "#15263a";
      button.style.background = swatchValue;
      if (nativeInput) nativeInput.value = swatchValue;
    });
  }

  function setImagePreview(targetName, src) {
    const previewBox = document.querySelector(`[data-asset-preview="${targetName}"]`);
    if (!previewBox) return;

    previewBox.innerHTML = "";
    if (src) {
      const img = document.createElement("img");
      img.src = src;
      img.alt = targetName;
      previewBox.appendChild(img);
      return;
    }

    const empty = document.createElement("span");
    empty.textContent = "Sin archivo cargado.";
    previewBox.appendChild(empty);
  }

  function refreshAssetPreviews() {
    fileInputs.forEach((input) => {
      const fieldName = input.dataset.assetInput;
      const hiddenValue = document.querySelector(`[data-asset-value="${fieldName}"]`);
      const clearInput = document.querySelector(`[data-asset-clear="${fieldName}"]`);

      if (input.files && input.files[0]) {
        const objectUrl = URL.createObjectURL(input.files[0]);
        setImagePreview(fieldName, objectUrl);
        if (clearInput) clearInput.value = "0";
        return;
      }

      if (clearInput && clearInput.value === "1") {
        setImagePreview(fieldName, "");
        return;
      }

      setImagePreview(fieldName, hiddenValue ? hiddenValue.value : "");
    });
  }

  function getAssetPreviewUrl(fieldName, fallback) {
    const fileInput = document.querySelector(`[data-asset-input="${fieldName}"]`);
    const clearInput = document.querySelector(`[data-asset-clear="${fieldName}"]`);
    const hiddenValue = document.querySelector(`[data-asset-value="${fieldName}"]`);

    if (fileInput && fileInput.files && fileInput.files[0]) {
      return URL.createObjectURL(fileInput.files[0]);
    }
    if (clearInput && clearInput.value === "1") {
      return "";
    }
    if (hiddenValue && hiddenValue.value) {
      return hiddenValue.value;
    }
    return fallback;
  }

  function setTriviaPreviewImage(src) {
    const hasImage = Boolean(src && String(src).trim());
    preview.triviaImage.classList.toggle("hidden", !hasImage);
    preview.triviaFallback.classList.toggle("hidden", hasImage);
    if (hasImage) preview.triviaImage.src = src;
    else preview.triviaImage.removeAttribute("src");
  }

  function syncTriviaQuestionVisibility() {
    if (!triviaQuestionCountInput || triviaQuestionBlocks.length === 0) return;
    const rawValue = Number.parseInt(triviaQuestionCountInput.value || "1", 10);
    const nextCount = Math.max(1, Math.min(triviaQuestionBlocks.length, Number.isFinite(rawValue) ? rawValue : 1));
    triviaQuestionCountInput.value = String(nextCount);
    triviaQuestionBlocks.forEach((block, index) => {
      block.classList.toggle("hidden", index >= nextCount);
    });
  }

  function syncTriviaResponseModes() {
    triviaQuestionBlocks.forEach((block) => {
      const select = block.querySelector("[data-trivia-response-type='true']");
      if (!select) return;
      block.classList.toggle("is-image-mode", select.value === "image");
    });
  }

  function readTriviaEditorQuestions() {
    if (gameSlug !== "trivia-mundial-fotos") return [];

    return triviaQuestionBlocks
      .filter((block) => !block.classList.contains("hidden"))
      .map((block) => {
        const questionIndex = block.dataset.triviaQuestionIndex;
        const prompt = safeText(block.querySelector("[data-trivia-prompt='true']")?.value, "");
        const responseType = safeText(block.querySelector("[data-trivia-response-type='true']")?.value, "text");
        const imageField = `trivia_questions__${questionIndex}__question_image_url`;
        const questionImageUrl = getAssetPreviewUrl(
          imageField,
          safeText(form.querySelector(`[name="${imageField}"]`)?.value, ""),
        );
        const correctFieldName = `trivia_questions__${questionIndex}__correct_answer`;
        const checkedAnswer = block.querySelector(`input[name="${correctFieldName}"]:checked`);
        const correctIndex = Number.parseInt(checkedAnswer?.value || "0", 10);

        const answers = Array.from(block.querySelectorAll("[data-trivia-answer-row='true']"))
          .map((row) => {
            const answerIndex = Number.parseInt(row.dataset.answerIndex || "0", 10);
            const label = safeText(row.querySelector("[data-trivia-answer-label='true']")?.value, "");
            const imageUrl = getAssetPreviewUrl(
              row.dataset.answerImageField,
              safeText(form.querySelector(`[name="${row.dataset.answerImageField}"]`)?.value, ""),
            );
            return { index: answerIndex, label, imageUrl };
          })
          .filter((answer) => answer.label || answer.imageUrl);

        if (!prompt && !questionImageUrl && answers.length === 0) return null;

        return {
          prompt,
          responseType,
          questionImageUrl,
          answers,
          correctIndex,
        };
      })
      .filter(Boolean);
  }

  function populateTriviaEditor(questions, explicitCount) {
    if (gameSlug !== "trivia-mundial-fotos" || triviaQuestionBlocks.length === 0) return;

    const normalizedQuestions = Array.isArray(questions) ? questions : [];
    const nextCount = Math.max(
      1,
      Math.min(
        triviaQuestionBlocks.length,
        Number.isFinite(explicitCount) && explicitCount > 0 ? explicitCount : normalizedQuestions.length || 1,
      ),
    );

    triviaQuestionBlocks.forEach((block, blockIndex) => {
      const source = normalizedQuestions[blockIndex] || null;
      const promptInput = block.querySelector("[data-trivia-prompt='true']");
      const responseTypeInput = block.querySelector("[data-trivia-response-type='true']");
      const questionFieldName = `trivia_questions__${blockIndex}__question_image_url`;
      const questionHidden = form.querySelector(`[name="${questionFieldName}"]`);
      const questionClear = form.querySelector(`[name="${questionFieldName}__clear"]`);
      const questionFile = form.querySelector(`[name="${questionFieldName}__file"]`);

      if (promptInput) promptInput.value = source?.prompt || "";
      if (responseTypeInput) responseTypeInput.value = source?.response_type || source?.responseType || "text";
      if (questionHidden) questionHidden.value = source?.question_image_url || source?.questionImageUrl || "";
      if (questionClear) questionClear.value = "0";
      if (questionFile) questionFile.value = "";

      const correctFieldName = `trivia_questions__${blockIndex}__correct_answer`;
      const correctValue = String(source?.correct_answer ?? source?.correctIndex ?? 0);
      const radios = Array.from(block.querySelectorAll(`input[name="${correctFieldName}"]`));
      radios.forEach((radio) => {
        radio.checked = radio.value === correctValue;
      });

      const answers = Array.isArray(source?.answers) ? source.answers : [];
      Array.from(block.querySelectorAll("[data-trivia-answer-row='true']")).forEach((row, rowIndex) => {
        const answer = answers[rowIndex] || {};
        const labelInput = row.querySelector("[data-trivia-answer-label='true']");
        const imageFieldName = row.dataset.answerImageField;
        const imageHidden = form.querySelector(`[name="${imageFieldName}"]`);
        const imageClear = form.querySelector(`[name="${imageFieldName}__clear"]`);
        const imageFile = form.querySelector(`[name="${imageFieldName}__file"]`);

        if (labelInput) labelInput.value = answer.label || "";
        if (imageHidden) imageHidden.value = answer.image_url || answer.imageUrl || "";
        if (imageClear) imageClear.value = "0";
        if (imageFile) imageFile.value = "";
      });
    });

    if (triviaQuestionCountInput) {
      triviaQuestionCountInput.value = String(nextCount);
    }

    syncTriviaQuestionVisibility();
    syncTriviaResponseModes();
    refreshAssetPreviews();
  }

  function setPreviewImage(src) {
    const hasImage = Boolean(src && String(src).trim());
    preview.heroImage.classList.toggle("hidden", !hasImage);
    preview.heroFallback.classList.toggle("hidden", hasImage);
    if (hasImage) preview.heroImage.src = src;
    else preview.heroImage.removeAttribute("src");
  }

  function setLogo(src) {
    const hasImage = Boolean(src && String(src).trim());
    preview.logo.classList.toggle("hidden", !hasImage);
    if (hasImage) preview.logo.src = src;
    else preview.logo.removeAttribute("src");
  }

  function applyCommonPreview(config) {
    const branding = config.branding || {};
    const texts = config.texts || {};
    const visual = config.visual || {};
    const watermark = config.watermark || {};

    const primary = safeText(branding.primary_color, "#00f5e9");
    const accent = safeText(visual.accent_color, primary);
    const textColor = safeText(visual.text_color, "#eef4ff");
    const panelBg = safeText(visual.panel_bg_color, "#0f1624");
    const border = safeText(visual.panel_border_color, "#2d95d2");
    const backgroundUrl = getAssetPreviewUrl("branding__background_url", safeText(branding.background_url, ""));
    const backgroundColor = safeText(visual.screen_background_color, "#08111b");

    preview.stage.style.background = backgroundUrl
      ? `linear-gradient(180deg, rgba(7, 12, 20, 0.28), rgba(7, 12, 20, 0.88)), url(${backgroundUrl}) center / cover no-repeat`
      : `radial-gradient(circle at top left, ${accent}16, transparent 28%), linear-gradient(180deg, ${backgroundColor}, #09111b)`;

    preview.stage.style.borderColor = border;
    preview.title.style.color = textColor;
    preview.subtitle.style.color = "rgba(238, 244, 255, 0.58)";
    preview.button.style.background = `linear-gradient(135deg, ${primary}, ${accent})`;
    preview.button.style.color = "#09121f";
    preview.badge.style.background = `linear-gradient(135deg, ${primary}, ${accent})`;
    preview.badge.style.color = "#09121f";
    if (preview.triviaBadge) {
      preview.triviaBadge.style.background = `linear-gradient(135deg, ${primary}, ${accent})`;
      preview.triviaBadge.style.color = "#09121f";
    }
    if (preview.triviaTimerFill) {
      preview.triviaTimerFill.style.background = `linear-gradient(90deg, ${primary}, ${accent})`;
    }
    document.querySelector(".playtek-phone__screen").style.background = `linear-gradient(180deg, ${panelBg}, #0b111d)`;

    setLogo(getAssetPreviewUrl("branding__logo_url", safeText(branding.logo_url, "")));
    preview.title.textContent = safeText(texts.welcome_title, "Juego");
    preview.subtitle.textContent = safeText(texts.welcome_subtitle, "Configuración visual del juego.");
    preview.button.textContent = safeText(texts.cta_button, "Empezar");

    const watermarkEnabled = Boolean(watermark.enabled && safeText(branding.watermark_text, ""));
    preview.watermark.classList.toggle("hidden", !watermarkEnabled);
    if (watermarkEnabled) {
      preview.watermark.textContent = safeText(branding.watermark_text, "");
      preview.watermark.style.color = safeText(watermark.color, primary);
      preview.watermark.style.opacity = String(safeNumber(watermark.opacity, 0.2));
      preview.watermark.style.fontSize = `${safeNumber(watermark.font_size, 48)}px`;
    }
  }

  function applyPuzzlePreview(config) {
    const texts = config.texts || {};
    const rules = config.rules || {};
    const heroUrl = getAssetPreviewUrl(
      "branding__welcome_image_url",
      getAssetPreviewUrl("content__puzzle_image_url", ""),
    );

    preview.badge.textContent = "Puzzle Mundial";
    setPreviewImage(heroUrl);
    preview.metaOne.textContent = `${safeNumber(rules.grid_size, 3)} x ${safeNumber(rules.grid_size, 3)}`;
    preview.metaTwo.textContent = `${safeNumber(rules.timer_seconds, 180)} s`;
    preview.metaThree.textContent = "Lista";
    preview.metaFour.classList.add("hidden");
    preview.button.textContent = safeText(texts.cta_button, "Empezar puzzle");
    preview.supportText.classList.add("hidden");
  }

  function applyTriviaPreview(config) {
    const texts = config.texts || {};
    const rules = config.rules || {};
    const editorQuestions = readTriviaEditorQuestions();
    const activeQuestions = editorQuestions.length > 0 ? editorQuestions : [
      {
        prompt: "¿En qué año Argentina ganó su tercer Mundial de Fútbol?",
        questionImageUrl: getAssetPreviewUrl("content__question_pack_image_url", ""),
        answers: [
          { label: "2018", imageUrl: "" },
          { label: "2022", imageUrl: "" },
          { label: "2014", imageUrl: "" },
          { label: "Francia", imageUrl: "" },
        ],
      },
    ];
    const firstQuestion = activeQuestions[0];
    const maxQuestions = Math.max(1, safeNumber(rules.max_questions, activeQuestions.length));
    const totalQuestions = Math.max(1, Math.min(maxQuestions, activeQuestions.length));
    const fallbackQuestionImage = getAssetPreviewUrl("content__question_pack_image_url", "");

    preview.genericExperience.classList.add("hidden");
    preview.triviaExperience.classList.remove("hidden");

    preview.triviaBadge.textContent = safeText(texts.welcome_title, "TRIVIA MUNDIAL FOTOS");
    preview.triviaProgress.textContent = `1 / ${totalQuestions}`;
    preview.triviaScore.textContent = String(safeNumber(rules.points_per_correct, 100));
    preview.triviaTimer.textContent = `${safeNumber(rules.timer_seconds, 15)}s`;
    preview.triviaQuestionText.textContent = safeText(
      firstQuestion.prompt,
      "¿En qué año Argentina ganó su tercer Mundial de Fútbol?",
    );

    const timerSeconds = Math.max(3, safeNumber(rules.timer_seconds, 15));
    preview.triviaTimerFill.style.width = `${Math.max(18, Math.min(100, (timerSeconds / 20) * 100))}%`;
    setTriviaPreviewImage(safeText(firstQuestion.questionImageUrl || firstQuestion.image, fallbackQuestionImage));

    const answers = Array.isArray(firstQuestion.answers) ? firstQuestion.answers : [];
    const fallbackAnswers = ["2018", "2022", "2014", "Francia"];
    [
      preview.triviaAnswerOne,
      preview.triviaAnswerTwo,
      preview.triviaAnswerThree,
      preview.triviaAnswerFour,
    ].forEach((node, index) => {
      if (!node) return;
      const answer = answers[index];
      node.textContent = safeText(answer?.label, fallbackAnswers[index] || `Respuesta ${index + 1}`);
    });
  }

  function applyKeeperPreview(config) {
    const texts = config.texts || {};
    const rules = config.rules || {};

    preview.badge.textContent = "El del Arquero";
    setPreviewImage(getAssetPreviewUrl("branding__welcome_image_url", ""));
    preview.metaOne.textContent = `${safeNumber(rules.timer_seconds, 60)} s`;
    preview.metaTwo.textContent = `${safeNumber(rules.points_per_save, 10)} pts`;
    preview.metaThree.textContent = rules.bonus_ball_enabled ? "Bonus on" : "Bonus off";
    preview.metaFour.classList.remove("hidden");
    preview.metaFour.textContent = rules.penalty_ball_enabled ? "Trampa on" : "Trampa off";
    preview.button.textContent = safeText(texts.cta_button, "Tocar para jugar");
    preview.supportText.classList.remove("hidden");
    preview.supportText.textContent = safeText(
      texts.instructions_text,
      "Arrastrá al portero para parar los balones.",
    );
  }

  function applyPreview() {
    const config = readConfigFromForm();
    applyCommonPreview(config);

    if (preview.genericExperience && preview.triviaExperience) {
      preview.genericExperience.classList.toggle("hidden", gameSlug === "trivia-mundial-fotos");
      preview.triviaExperience.classList.toggle("hidden", gameSlug !== "trivia-mundial-fotos");
    }

    if (gameSlug === "puzzle-mundial") applyPuzzlePreview(config);
    if (gameSlug === "trivia-mundial-fotos") applyTriviaPreview(config);
    if (gameSlug === "el-del-arquero") applyKeeperPreview(config);
  }

  function markDirty(message) {
    dirty = true;
    saveStatus.textContent = message || "Hay cambios sin guardar.";
  }

  function formatErrors(errors) {
    if (!errors || typeof errors !== "object") return "";
    return Object.entries(errors)
      .map(([field, messages]) => `${field}: ${Array.isArray(messages) ? messages.join(", ") : messages}`)
      .join(" | ");
  }

  async function saveCustomization() {
    saveButton.disabled = true;
    saveButton.textContent = "Guardando...";
    saveStatus.textContent = "Guardando customización...";

    try {
      const response = await fetch(saveUrl, {
        method: "POST",
        body: new FormData(form),
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });
      const result = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(formatErrors(result.errors) || "No se pudo guardar la customización.");
      }

      dirty = false;
      saveStatus.textContent = result.message || "Customización guardada.";
      if (result.config) {
        populateForm(result.config);
        if (gameSlug === "trivia-mundial-fotos") {
          populateTriviaEditor(result.trivia_questions, result.trivia_question_count);
        }
        applyPreview();
      }
    } catch (error) {
      saveStatus.textContent = error.message || "No se pudo guardar la customización.";
    } finally {
      saveButton.disabled = false;
      saveButton.textContent = "Guardar customización";
    }
  }

  configFields.forEach((node) => {
    const eventName = node.type === "checkbox" || node.tagName === "SELECT" ? "change" : "input";
    node.addEventListener(eventName, () => {
      if (node.dataset.colorText) refreshColorInputs();
      applyPreview();
      markDirty();
    });
  });

  swatchButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const fieldName = button.dataset.colorTrigger;
      const nativeInput = document.querySelector(`[data-color-native="${fieldName}"]`);
      if (nativeInput) nativeInput.click();
    });
  });

  nativeColorInputs.forEach((input) => {
    input.addEventListener("input", () => {
      const fieldName = input.dataset.colorNative;
      const textInput = document.querySelector(`[data-color-text="${fieldName}"]`);
      if (!textInput) return;
      textInput.value = input.value;
      refreshColorInputs();
      applyPreview();
      markDirty();
    });
  });

  fileInputs.forEach((input) => {
    input.addEventListener("change", () => {
      const fieldName = input.dataset.assetInput;
      const clearInput = document.querySelector(`[data-asset-clear="${fieldName}"]`);
      if (clearInput) clearInput.value = "0";
      refreshAssetPreviews();
      applyPreview();
      markDirty("Asset listo para guardar.");
    });
  });

  clearButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const fieldName = button.dataset.assetClearButton;
      const hiddenValue = document.querySelector(`[data-asset-value="${fieldName}"]`);
      const clearInput = document.querySelector(`[data-asset-clear="${fieldName}"]`);
      const fileInput = document.querySelector(`[data-asset-input="${fieldName}"]`);
      if (hiddenValue) hiddenValue.value = "";
      if (clearInput) clearInput.value = "1";
      if (fileInput) fileInput.value = "";
      refreshAssetPreviews();
      applyPreview();
      markDirty("Asset marcado para eliminar.");
    });
  });

  triviaEditorFields.forEach((node) => {
    const eventName = node.type === "radio" || node.tagName === "SELECT" || node.type === "number" ? "change" : "input";
    node.addEventListener(eventName, () => {
      syncTriviaQuestionVisibility();
      syncTriviaResponseModes();
      applyPreview();
      markDirty("Preguntas actualizadas. Guarda para confirmar.");
    });
  });

  triviaAnswerClearButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const row = button.closest("[data-trivia-answer-row='true']");
      if (!row) return;
      const labelInput = row.querySelector("[data-trivia-answer-label='true']");
      const hiddenValue = document.querySelector(`[data-asset-value="${row.dataset.answerImageField}"]`);
      const clearInput = document.querySelector(`[data-asset-clear="${row.dataset.answerImageField}"]`);
      const fileInput = document.querySelector(`[data-asset-input="${row.dataset.answerImageField}"]`);
      if (labelInput) labelInput.value = "";
      if (hiddenValue) hiddenValue.value = "";
      if (clearInput) clearInput.value = "1";
      if (fileInput) fileInput.value = "";
      refreshAssetPreviews();
      applyPreview();
      markDirty("Respuesta limpia. Guarda para confirmar.");
    });
  });

  paletteButton.addEventListener("click", () => {
    populateForm(defaultConfig);
    applyPreview();
    markDirty("Paleta Playtek aplicada. Guarda para confirmar.");
  });

  focusPreviewButton.addEventListener("click", () => {
    document.querySelector(".playtek-preview").scrollIntoView({ behavior: "smooth", block: "start" });
  });

  preview.button.addEventListener("click", () => {
    if (!previewUrl) return;
    window.open(previewUrl, "_blank", "noopener");
  });

  saveButton.addEventListener("click", saveCustomization);
  embeddedSaveButtons.forEach((button) => {
    button.addEventListener("click", saveCustomization);
  });

  window.addEventListener("beforeunload", (event) => {
    if (!dirty) return;
    event.preventDefault();
    event.returnValue = "";
  });

  populateForm(initialConfig);
  syncTriviaQuestionVisibility();
  syncTriviaResponseModes();
  refreshColorInputs();
  refreshAssetPreviews();
  applyPreview();
})();
