/* Giao diện sáng/tối và chế độ trình chiếu. Tách riêng khỏi app.js để theme được
   áp dụng trước khi trang vẽ (không bị nháy trắng), và không đụng vào logic thuật toán. */
(function () {
  "use strict";

  const KEY = "search-debugger-theme";
  const root = document.documentElement;

  function readSaved() {
    try { return localStorage.getItem(KEY); } catch (_) { return null; }
  }
  function save(value) {
    try { localStorage.setItem(KEY, value); } catch (_) { /* trình duyệt chặn lưu: bỏ qua */ }
  }
  function systemPrefersDark() {
    return !!(window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches);
  }
  function applyTheme(theme) {
    root.setAttribute("data-theme", theme);
  }

  // Áp dụng ngay khi script chạy (trong <head>)
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
      // Bố cục đổi cỡ: báo cho phần vẽ cây co giãn lại cho vừa khung
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
