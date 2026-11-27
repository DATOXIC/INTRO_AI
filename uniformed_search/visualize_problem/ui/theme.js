(function () {
  "use strict";

  const KEY = "search-debugger-theme";
  const root = document.documentElement;

  function readSaved() {
    try { return localStorage.getItem(KEY); } catch (_) { return null; }
  }
  function save(value) {
    try { localStorage.setItem(KEY, value); } catch (_) {  }
  }
  function systemPrefersDark() {
    return !!(window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches);
  }
  function applyTheme(theme) {
    root.setAttribute("data-theme", theme);
  }

  applyTheme(readSaved() || (systemPrefersDark() ? "dark" : "light"));

  document.addEventListener("DOMContentLoaded", () => {
    const themeBtn = document.getElementById("themeBtn");
    const presentBtn = document.getElementById("presentBtn");

    if (themeBtn) {
      themeBtn.addEventListener("click", () => {
        const next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
        applyTheme(next);
        save(next);
      });
    }

    function setPresent(on) {
      document.body.classList.toggle("present", on);
      if (presentBtn) presentBtn.setAttribute("aria-pressed", String(on));
      window.dispatchEvent(new Event("resize"));
    }

    if (presentBtn) {
      presentBtn.addEventListener("click", () => setPresent(!document.body.classList.contains("present")));
    }
    window.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && document.body.classList.contains("present")) setPresent(false);
    });
  });
})();
