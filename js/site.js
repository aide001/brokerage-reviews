// Shared page chrome for pages other than the homepage: theme toggle,
// mobile menu and footer year.
(function () {
  "use strict";
  var root = document.documentElement;

  function currentTheme() {
    var attr = root.getAttribute("data-theme");
    if (attr) return attr;
    return window.matchMedia && matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  var toggle = document.getElementById("theme-toggle");
  if (toggle) {
    toggle.addEventListener("click", function () {
      var next = currentTheme() === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      try { localStorage.setItem("br-theme", next); } catch (e) {}
    });
  }

  var nav = document.getElementById("main-nav");
  var menuBtn = document.getElementById("menu-toggle");
  if (nav && menuBtn) {
    menuBtn.addEventListener("click", function () {
      var open = nav.classList.toggle("open");
      menuBtn.setAttribute("aria-expanded", String(open));
    });
  }

  // Market News filters: All / Analysis / Official data.
  var filterBtns = document.querySelectorAll(".filter-btn");
  Array.prototype.forEach.call(filterBtns, function (btn) {
    btn.addEventListener("click", function () {
      var want = btn.getAttribute("data-filter");
      Array.prototype.forEach.call(filterBtns, function (b) {
        b.setAttribute("aria-pressed", String(b === btn));
      });
      Array.prototype.forEach.call(document.querySelectorAll("#post-grid .post-card"), function (card) {
        card.hidden = want !== "all" && card.getAttribute("data-kind") !== want;
      });
    });
  });

  var year = document.getElementById("year");
  if (year) year.textContent = new Date().getFullYear();
})();
