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

  // Start new visits at the top. Normally browsers already do this, but when the site is
  // shown inside a frame that grows to fit the page (e.g. iOS Safari previews), the outer
  // page keeps its scroll position and the new page opens part-way down. Skipped for Back/
  // Forward and reloads (so the browser can restore the position) and for #section links.
  try {
    var nav = performance.getEntriesByType && performance.getEntriesByType("navigation")[0];
    if (!location.hash && (!nav || nav.type === "navigate")) {
      window.scrollTo(0, 0);
      var root = document.documentElement;
      if (window.top !== window && root.scrollIntoView) {
        // scroll-padding (kept for #section links under the sticky header) would stop 80px short.
        root.style.scrollPaddingTop = "0px";
        root.scrollIntoView({ block: "start", behavior: "instant" });
        root.style.scrollPaddingTop = "";
      }
    }
  } catch (e) {}

  var year = document.getElementById("year");
  if (year) year.textContent = new Date().getFullYear();
})();
