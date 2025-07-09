(function () {
  const applyDarkMode = () => {
    document.documentElement.style.filter = "invert(1) hue-rotate(180deg)";
    document.body.style.backgroundColor = "#fff";
  };

  const removeDarkMode = () => {
    document.documentElement.style.filter = "";
    document.body.style.backgroundColor = "";
  };

  const toggleDark = () => {
    const isDark = document.documentElement.style.filter.includes("invert");
    if (isDark) {
      removeDarkMode();
      localStorage.setItem("darkMode", "off");
    } else {
      applyDarkMode();
      localStorage.setItem("darkMode", "on");
    }

    const toggles = document.querySelectorAll(".form-check-input");
    toggles.forEach((t) => (t.checked = !isDark));
  };

  document.addEventListener("DOMContentLoaded", () => {
    const toggles = document.querySelectorAll(".form-check-input");
    toggles.forEach((t) => t.addEventListener("change", toggleDark));

    if (localStorage.getItem("darkMode") === "on") {
      applyDarkMode();
      toggles.forEach((t) => (t.checked = true));
    }
  });
})();
