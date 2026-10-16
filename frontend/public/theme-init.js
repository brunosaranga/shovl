// Sets the theme before React loads, so dark-mode visitors never see a white flash.
// Saved choice first, then the system setting. ThemeContext takes over from here.
// Loaded as a plain (blocking) script in index.html's <head>, so it runs before the first paint.
(function () {
    var theme = "light";
    try {
        var saved = localStorage.getItem("shovl.theme");
        if (saved === "light" || saved === "dark") {
            theme = saved;
        } else if (window.matchMedia("(prefers-color-scheme: dark)").matches) {
            theme = "dark";
        }
    } catch (e) {}
    document.documentElement.dataset.theme = theme;
})();
