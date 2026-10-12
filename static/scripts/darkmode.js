(function () {
  // Synchronously initialize theme to completely prevent page load flickering
  const savedTheme = localStorage.getItem("parkin_theme") || "light";
  document.documentElement.setAttribute("data-theme", savedTheme);

  const updateToggleElements = (theme) => {
    // 1. Sync any checkbox switch toggles
    const switches = document.querySelectorAll(".dark-mode-toggle, input[name='dark-mode-toggle']");
    switches.forEach((el) => {
      if (el.type === "checkbox") {
        el.checked = theme === "dark";
      }
    });

    // 2. Sync icon states in button-style toggles
    const icons = document.querySelectorAll(".dark-mode-icon");
    icons.forEach((icon) => {
      if (theme === "dark") {
        icon.classList.remove("bi-moon-stars", "bi-moon");
        icon.classList.add("bi-sun-fill");
      } else {
        icon.classList.remove("bi-sun-fill", "bi-sun");
        icon.classList.add("bi-moon-stars");
      }
    });
  };

  const applyTheme = (theme) => {
    document.documentElement.setAttribute("data-theme", theme);
    try {
      localStorage.setItem("parkin_theme", theme);
    } catch (e) {
      console.warn("Could not save theme preference to localStorage", e);
    }
    updateToggleElements(theme);
    window.dispatchEvent(new CustomEvent("themeChanged", { detail: { theme } }));
  };

  const toggleTheme = (e) => {
    if (e && e.preventDefault && e.target.tagName !== "INPUT") {
      e.preventDefault();
    }
    const currentTheme = document.documentElement.getAttribute("data-theme") || "light";
    const newTheme = currentTheme === "dark" ? "light" : "dark";
    applyTheme(newTheme);
  };

  window.toggleParkInTheme = toggleTheme;

  document.addEventListener("DOMContentLoaded", () => {
    const currentTheme = document.documentElement.getAttribute("data-theme") || "light";
    updateToggleElements(currentTheme);

    // Bind event listeners to switches and toggle buttons
    const toggles = document.querySelectorAll(".dark-mode-toggle, .dark-mode-btn");
    toggles.forEach((el) => {
      if (el.type === "checkbox") {
        el.addEventListener("change", (e) => {
          const desired = e.target.checked ? "dark" : "light";
          applyTheme(desired);
        });
      } else {
        el.addEventListener("click", toggleTheme);
      }
    });
  });

  // Keep all tabs in sync
  window.addEventListener("storage", (event) => {
    if (event.key === "parkin_theme" && event.newValue) {
      document.documentElement.setAttribute("data-theme", event.newValue);
      updateToggleElements(event.newValue);
    }
  });
})();

