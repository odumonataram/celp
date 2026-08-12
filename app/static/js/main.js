/* =========================================================================
   app/static/js/main.js
   Shared client-side behaviour: theme toggle + accessibility prefs,
   Web Speech API pronunciation playback, translator AJAX calls, and
   dictionary instant-search/autocomplete.
   ========================================================================= */

document.addEventListener("DOMContentLoaded", function () {
  initThemeToggle();
  initSpeakButtons();
  initTranslator();
  initAutocomplete();
});

/* ---------------------------------------------------------------------
   Theme / accessibility preferences (Feature 24: dark mode, large fonts,
   colour-blind mode). Stored in localStorage -- this is a real deployed
   web app served from Flask, not a sandboxed Claude artifact, so
   localStorage is the correct, standard tool here.
   --------------------------------------------------------------------- */
function applyStoredPreferences() {
  const root = document.documentElement;
  root.setAttribute("data-theme", localStorage.getItem("cnd-theme") || "light");
  root.setAttribute("data-fontsize", localStorage.getItem("cnd-fontsize") || "normal");
  root.setAttribute("data-colorblind", localStorage.getItem("cnd-colorblind") || "false");
}
applyStoredPreferences();

function initThemeToggle() {
  const toggle = document.getElementById("theme-toggle");
  if (!toggle) return;
  toggle.checked = localStorage.getItem("cnd-theme") === "dark";
  toggle.addEventListener("change", function () {
    const theme = this.checked ? "dark" : "light";
    localStorage.setItem("cnd-theme", theme);
    document.documentElement.setAttribute("data-theme", theme);
  });

  const fontToggle = document.getElementById("fontsize-toggle");
  if (fontToggle) {
    fontToggle.checked = localStorage.getItem("cnd-fontsize") === "large";
    fontToggle.addEventListener("change", function () {
      const size = this.checked ? "large" : "normal";
      localStorage.setItem("cnd-fontsize", size);
      document.documentElement.setAttribute("data-fontsize", size);
    });
  }

  const cbToggle = document.getElementById("colorblind-toggle");
  if (cbToggle) {
    cbToggle.checked = localStorage.getItem("cnd-colorblind") === "true";
    cbToggle.addEventListener("change", function () {
      const val = this.checked ? "true" : "false";
      localStorage.setItem("cnd-colorblind", val);
      document.documentElement.setAttribute("data-colorblind", val);
    });
  }
}

/* ---------------------------------------------------------------------
   Pronunciation (Feature 3). English uses the browser's Web Speech API
   directly -- no server round trip, works offline, and has a real voice
   model. Indigenous languages fall back to the server's /dictionary/audio
   endpoint, which serves a pre-recorded native-speaker clip if one has been
   uploaded by an admin, or shows a "no audio yet" message if not.
   --------------------------------------------------------------------- */
function speakWithBrowser(text, lang, rate) {
  if (!("speechSynthesis" in window)) {
    alert("Your browser does not support speech synthesis.");
    return;
  }
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = lang || "en-US";
  utterance.rate = rate || 1.0;
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(utterance);
}

function initSpeakButtons() {
  document.querySelectorAll("[data-speak]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      const text = btn.getAttribute("data-speak");
      const langCode = btn.getAttribute("data-lang-code") || "en";
      const speed = btn.getAttribute("data-speed") === "slow" ? 0.6 : 1.0;
      const wordId = btn.getAttribute("data-word-id");

      btn.classList.add("is-playing");
      setTimeout(() => btn.classList.remove("is-playing"), 800);

      if (langCode === "en" || !wordId) {
        speakWithBrowser(text, "en-US", speed);
        return;
      }

      // Indigenous language: try the server-side audio endpoint first.
      const audio = new Audio(`/dictionary/audio/${wordId}`);
      audio.play().catch(function () {
        speakWithBrowser(text, "en-US", speed); // last-resort fallback
      });
    });
  });
}

/* ---------------------------------------------------------------------
   Translator AJAX (Feature 1)
   --------------------------------------------------------------------- */
function initTranslator() {
  const form = document.getElementById("translator-form");
  if (!form) return;

  const textInput = document.getElementById("translator-text");
  const sourceSelect = document.getElementById("source-lang");
  const targetSelect = document.getElementById("target-lang");
  const resultsBox = document.getElementById("translator-results");
  const swapBtn = document.getElementById("swap-languages");
  const csrfToken = document.querySelector('meta[name="csrf-token"]').content;

  async function runTranslate() {
    const text = textInput.value.trim();
    if (!text) {
      resultsBox.innerHTML = "";
      return;
    }
    resultsBox.innerHTML = '<p class="text-muted">Translating...</p>';

    try {
      const res = await fetch("/translate/api", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken },
        body: JSON.stringify({
          text: text,
          source_lang: sourceSelect.value,
          target_lang: targetSelect.value,
        }),
      });
      const data = await res.json();
      renderResults(data);
    } catch (err) {
      resultsBox.innerHTML = '<p class="text-danger">Something went wrong. Please try again.</p>';
    }
  }

  function renderResults(data) {
    if (!data.suggestions || data.suggestions.length === 0) {
      resultsBox.innerHTML = '<p class="text-muted">No translation found yet for this word/phrase. ' +
        "It may not be in the dictionary yet.</p>";
      return;
    }

    resultsBox.innerHTML = data.suggestions.map(function (s, idx) {
      const confidencePct = Math.round(s.confidence * 100);
      const wordIdAttr = s.word_id ? `data-word-id="${s.word_id}"` : "";
      return `
        <div class="cnd-card p-3 mb-3 ${idx === 0 ? "border-2" : ""}">
          <div class="d-flex justify-content-between align-items-start">
            <div>
              <div class="fs-4 display-font">${escapeHtml(s.target_text)}</div>
              ${s.pronunciation ? `<div class="text-muted small">/${escapeHtml(s.pronunciation)}/</div>` : ""}
            </div>
            <button class="btn btn-play btn-sm" data-speak="${escapeHtml(s.target_text)}"
                    data-lang-code="${targetSelect.value}" ${wordIdAttr} title="Play pronunciation">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>
            </button>
          </div>
          ${s.meaning ? `<p class="mt-2 mb-1">${escapeHtml(s.meaning)}</p>` : ""}
          ${s.example_sentence ? `<p class="text-muted small mb-0"><em>${escapeHtml(s.example_sentence)}</em></p>` : ""}
          <div class="mt-2 d-flex align-items-center gap-2">
            <div class="confidence-bar flex-grow-1" style="max-width:140px;">
              <div class="confidence-bar-fill" style="width:${confidencePct}%;"></div>
            </div>
            <span class="small text-muted">${confidencePct}% confidence</span>
            ${s.method === "word_by_word_fallback" ? '<span class="badge text-bg-warning">word-by-word</span>' : ""}
          </div>
        </div>`;
    }).join("");

    initSpeakButtons(); // re-bind for newly inserted buttons
  }

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    runTranslate();
  });

  let debounceTimer;
  textInput.addEventListener("input", function () {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(runTranslate, 500);
  });

  if (swapBtn) {
    swapBtn.addEventListener("click", function () {
      const tmp = sourceSelect.value;
      sourceSelect.value = targetSelect.value;
      targetSelect.value = tmp;
      runTranslate();
    });
  }
}

/* ---------------------------------------------------------------------
   Dictionary instant search / autocomplete (Feature 22)
   --------------------------------------------------------------------- */
function initAutocomplete() {
  const input = document.getElementById("dictionary-search-input");
  const langSelect = document.getElementById("dictionary-search-lang");
  const dropdown = document.getElementById("autocomplete-dropdown");
  if (!input || !dropdown) return;

  let debounceTimer;
  input.addEventListener("input", function () {
    clearTimeout(debounceTimer);
    const q = input.value.trim();
    if (q.length < 2) {
      dropdown.innerHTML = "";
      dropdown.classList.add("d-none");
      return;
    }
    debounceTimer = setTimeout(async function () {
      const lang = langSelect ? langSelect.value : "en";
      const res = await fetch(`/dictionary/autocomplete?q=${encodeURIComponent(q)}&lang=${lang}`);
      const items = await res.json();
      if (items.length === 0) {
        dropdown.classList.add("d-none");
        return;
      }
      dropdown.innerHTML = items.map(function (item) {
        return `<a class="list-group-item list-group-item-action" href="/dictionary/word/${item.id}">
                  <strong>${escapeHtml(item.text)}</strong>
                  ${item.meaning ? `<span class="text-muted"> -- ${escapeHtml(item.meaning)}</span>` : ""}
                </a>`;
      }).join("");
      dropdown.classList.remove("d-none");
    }, 250);
  });

  document.addEventListener("click", function (e) {
    if (!dropdown.contains(e.target) && e.target !== input) {
      dropdown.classList.add("d-none");
    }
  });
}

function escapeHtml(str) {
  if (!str) return "";
  return str.replace(/[&<>"']/g, function (c) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
  });
}
