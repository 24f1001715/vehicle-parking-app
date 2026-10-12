(function () {
  // Synchronously initialize theme to completely prevent page load flickering
  const savedTheme = localStorage.getItem("parkin_theme") || "light";
  document.documentElement.setAttribute("data-theme", savedTheme);

  const applyTheme = (theme) => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("parkin_theme", theme);

    // Sync only dark toggle switches, never other form inputs or checkboxes
    const toggles = document.querySelectorAll(".dark-mode-toggle");
    toggles.forEach((t) => {
      t.checked = theme === "dark";
    });
  };

  const toggleTheme = () => {
    const currentTheme = document.documentElement.getAttribute("data-theme") || "light";
    const newTheme = currentTheme === "dark" ? "light" : "dark";
    applyTheme(newTheme);
  };

  document.addEventListener("DOMContentLoaded", () => {
    const currentTheme = document.documentElement.getAttribute("data-theme") || "light";
    const toggles = document.querySelectorAll(".dark-mode-toggle");
    
    toggles.forEach((t) => {
      t.checked = currentTheme === "dark";
      t.addEventListener("change", toggleTheme);
    });
  });
})();
