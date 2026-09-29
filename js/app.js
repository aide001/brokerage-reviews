(function () {
  "use strict";

  var BROKERS = window.BROKERS || [];
  var TIER1 = window.TIER1_REGULATORS || [];
  var MAX_COMPARE = 3;
  var PIP_VALUE = 10; // USD per pip per standard lot on EUR/USD

  var AFFILIATE = window.AFFILIATE_LINKS || {};
  // Rating categories come from content/brokers.json via js/data.js; this list is a fallback.
  var CATEGORIES = window.RATING_CATEGORIES || [
    { key: "fees", label: "Fees & costs", weight: 0.3, desc: "Spreads, commissions, swaps and non-trading fees such as inactivity and withdrawal charges." },
    { key: "trust", label: "Trust & regulation", weight: 0.25, desc: "Number and quality of licences, track record, listed status and client-fund protections." },
    { key: "platforms", label: "Platforms & tools", weight: 0.2, desc: "Platform choice, charting, execution quality, mobile apps and automated trading support." },
    { key: "education", label: "Research & education", weight: 0.15, desc: "Market analysis, tutorials, webinars and tools that help traders improve." },
    { key: "support", label: "Customer support", weight: 0.1, desc: "Availability, speed and quality of help via live chat, phone and email." }
  ];

  // ---------- Derived data ----------
  BROKERS.forEach(function (b) {
    b.overall = round1(CATEGORIES.reduce(function (sum, c) {
      return sum + b.ratings[c.key] * c.weight;
    }, 0));
    b.cost = round2(b.spread * PIP_VALUE + b.commission);
    b.tier1 = b.regulators.some(function (r) { return TIER1.indexOf(r) !== -1; });
  });

  var byId = {};
  BROKERS.forEach(function (b) { byId[b.id] = b; });

  var state = {
    search: "",
    regulator: "",
    platform: "",
    maxDeposit: 200,
    sort: "rating",
    tier1: false,
    compare: []
  };

  // ---------- Helpers ----------
  function $(sel) { return document.querySelector(sel); }
  function round1(n) { return Math.round(n * 10) / 10; }
  function round2(n) { return Math.round(n * 100) / 100; }
  function money(n, digits) {
    return "$" + n.toLocaleString("en-US", {
      minimumFractionDigits: digits || 0,
      maximumFractionDigits: digits || 0
    });
  }
  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (ch) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch];
    });
  }
  function initials(name) {
    var parts = name.replace(/[^A-Za-z0-9 ]/g, " ").trim().split(/\s+/);
    return (parts.length > 1 ? parts[0][0] + parts[1][0] : name.slice(0, 2)).toUpperCase();
  }
  function textOn(hex) {
    var c = hex.replace("#", "");
    var r = parseInt(c.substr(0, 2), 16), g = parseInt(c.substr(2, 2), 16), b = parseInt(c.substr(4, 2), 16);
    return (r * 299 + g * 587 + b * 114) / 1000 > 160 ? "#111" : "#fff";
  }
  // Logo files are looked up as assets/logos/<id>.svg, then .png. Brokers
  // without a file (or whose file fails to load) fall back to initials.
  var LOGO_EXTS = ["svg", "png"];
  var logoMissing = {};
  function logo(b, size) {
    var cls = "broker-logo" + (size ? " broker-logo-" + size : "");
    var initialsHtml = '<span class="broker-logo-text">' + esc(initials(b.name)) + "</span>";
    if (logoMissing[b.id] || b.logoExt === "") {
      return '<span class="' + cls + '" style="background:' + b.color + ";color:" + textOn(b.color) +
        '" aria-hidden="true">' + initialsHtml + "</span>";
    }
    var ext = b.logoExt || LOGO_EXTS[0];
    return '<span class="' + cls + ' has-img" data-color="' + b.color + '" aria-hidden="true">' +
      '<img src="assets/logos/' + b.id + "." + ext + '" alt="" data-logo="' + b.id + '" />' +
      initialsHtml + "</span>";
  }
  function onLogoError(img) {
    var b = byId[img.dataset.logo];
    var current = img.getAttribute("src").split(".").pop();
    var next = LOGO_EXTS[LOGO_EXTS.indexOf(current) + 1];
    if (next) {
      b.logoExt = next;
      img.src = "assets/logos/" + b.id + "." + next;
      return;
    }
    logoMissing[b.id] = true;
    document.querySelectorAll('img[data-logo="' + b.id + '"]').forEach(function (el) {
      var box = el.parentNode;
      box.classList.remove("has-img");
      box.style.background = b.color;
      box.style.color = textOn(b.color);
      el.remove();
    });
  }
  document.addEventListener("error", function (e) {
    if (e.target.tagName === "IMG" && e.target.dataset.logo) onLogoError(e.target);
  }, true);
  function stars(score) {
    var pct = (score / 5) * 100;
    return '<span class="stars" role="img" aria-label="' + score.toFixed(1) + ' out of 5">' +
      '<span class="stars-fill" style="width:' + pct + '%"></span></span>';
  }
  function fmtInstruments(n) {
    return n >= 1000000 ? (n / 1000000) + "M+" : n.toLocaleString("en-US") + "+";
  }
  function fmtCommission(b) {
    return b.commission ? money(b.commission, 2) : '<span class="tag tag-good">None</span>';
  }
  function uniq(arr) {
    return arr.filter(function (v, i) { return arr.indexOf(v) === i; });
  }

  var toastTimer;
  function toast(msg) {
    var el = $("#toast");
    el.textContent = msg;
    el.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { el.classList.remove("show"); }, 2400);
  }

  // Highest score first; ties by name, the same order as the generated pages.
  function byRating(a, b) { return b.overall - a.overall || a.name.localeCompare(b.name); }
  function reviewUrl(b) { return "brokers/" + encodeURIComponent(b.id) + ".html"; }
  // Button to the broker: the affiliate link when set, otherwise the official site (no tracking).
  function brokerCta(b) {
    var aff = AFFILIATE[b.id];
    return aff
      ? '<a class="btn btn-primary" href="' + esc(aff) + '" target="_blank" rel="sponsored nofollow noopener">Open account<span class="sr-only"> with ' + esc(b.name) + "</span></a>"
      : '<a class="btn btn-primary" href="https://' + esc(b.domain) + '" target="_blank" rel="nofollow noopener">Visit ' + esc(b.name) + "</a>";
  }

  // ---------- Top picks ----------
  function renderTopPicks() {
    var top = BROKERS.slice().sort(byRating).slice(0, 3);
    var medals = ["Best overall", "Runner-up", "Also great"];
    $("#top-picks-grid").innerHTML = top.map(function (b, i) {
      return '<article class="pick-card">' +
        '<span class="pick-badge">' + medals[i] + "</span>" +
        '<div class="pick-head">' + logo(b, "lg") +
          "<div><h3>" + esc(b.name) + "</h3>" +
          '<p class="muted">' + esc(b.bestFor) + "</p></div></div>" +
        '<div class="pick-score"><strong>' + b.overall.toFixed(1) + "</strong>" + stars(b.overall) + "</div>" +
        '<dl class="pick-facts">' +
          "<div><dt>EUR/USD cost</dt><dd>" + money(b.cost, 2) + "/lot</dd></div>" +
          "<div><dt>Min deposit</dt><dd>" + money(b.minDeposit) + "</dd></div>" +
          "<div><dt>Regulators</dt><dd>" + b.regulators.length + "</dd></div>" +
        "</dl>" +
        '<ul class="pick-pros">' + b.pros.slice(0, 2).map(function (p) { return "<li>" + esc(p) + "</li>"; }).join("") + "</ul>" +
        '<a class="btn btn-primary btn-block" href="' + reviewUrl(b) + '">Read review</a>' +
      "</article>";
    }).join("");
  }

  // ---------- Filters ----------
  function populateFilters() {
    var regs = uniq([].concat.apply([], BROKERS.map(function (b) { return b.regulators; }))).sort();
    var plats = uniq([].concat.apply([], BROKERS.map(function (b) { return b.platforms; }))).sort();
    $("#f-regulator").insertAdjacentHTML("beforeend", regs.map(function (r) {
      return '<option value="' + esc(r) + '">' + esc(r) + "</option>";
    }).join(""));
    $("#f-platform").insertAdjacentHTML("beforeend", plats.map(function (p) {
      return '<option value="' + esc(p) + '">' + esc(p) + "</option>";
    }).join(""));
    $("#stat-brokers").textContent = BROKERS.length;
    $("#stat-regulators").textContent = regs.length;
  }

  function filtered() {
    var q = state.search.trim().toLowerCase();
    var list = BROKERS.filter(function (b) {
      if (q && b.name.toLowerCase().indexOf(q) === -1) return false;
      if (state.regulator && b.regulators.indexOf(state.regulator) === -1) return false;
      if (state.platform && b.platforms.indexOf(state.platform) === -1) return false;
      if (b.minDeposit > state.maxDeposit) return false;
      if (state.tier1 && !b.tier1) return false;
      return true;
    });
    var sorters = {
      rating: byRating,
      cost: function (a, b) { return a.cost - b.cost; },
      deposit: function (a, b) { return a.minDeposit - b.minDeposit || b.overall - a.overall; },
      instruments: function (a, b) { return b.instruments - a.instruments; },
      name: function (a, b) { return a.name.localeCompare(b.name); }
    };
    return list.sort(sorters[state.sort]);
  }

  function renderTable() {
    var list = filtered();
    var cheapest = Math.min.apply(null, BROKERS.map(function (b) { return b.cost; }));
    $("#result-count").textContent = "Showing " + list.length + " of " + BROKERS.length + " brokers";
    $("#empty-state").hidden = list.length > 0;
    $("#broker-table").hidden = list.length === 0;

    $("#broker-tbody").innerHTML = list.map(function (b) {
      var checked = state.compare.indexOf(b.id) !== -1;
      return "<tr>" +
        '<td class="col-check"><label class="compare-check" title="Add to compare">' +
          '<input type="checkbox" data-compare="' + b.id + '"' + (checked ? " checked" : "") +
          ' aria-label="Compare ' + esc(b.name) + '" /><span>Compare</span></label></td>' +
        '<td data-label="Broker"><div class="cell-broker">' + logo(b) +
          '<div><button class="link-btn broker-name" data-review="' + b.id + '">' + esc(b.name) + "</button>" +
          '<small class="muted">' + esc(b.bestFor) + "</small></div></div></td>" +
        '<td data-label="Rating"><div class="cell-rating"><strong>' + b.overall.toFixed(1) + "</strong>" + stars(b.overall) + "</div></td>" +
        '<td data-label="EUR/USD spread">' + b.spread.toFixed(1) + ' pips<small class="muted">' + esc(b.account) + "</small></td>" +
        '<td data-label="Commission">' + fmtCommission(b) + "</td>" +
        '<td data-label="All-in cost"><strong>' + money(b.cost, 2) + "</strong>" +
          (b.cost === cheapest ? ' <span class="tag tag-good">Lowest</span>' : "") + "</td>" +
        '<td data-label="Min deposit">' + (b.minDeposit === 0 ? '<span class="tag tag-good">$0</span>' : money(b.minDeposit)) + "</td>" +
        '<td data-label="Regulators"><div class="chips">' + b.regulators.slice(0, 3).map(function (r) {
            return '<span class="chip' + (TIER1.indexOf(r) !== -1 ? " chip-tier1" : "") + '">' + esc(r) + "</span>";
          }).join("") + (b.regulators.length > 3 ? '<span class="chip chip-more">+' + (b.regulators.length - 3) + "</span>" : "") +
        "</div></td>" +
        '<td data-label="Platforms"><div class="chips">' + b.platforms.slice(0, 3).map(function (p) {
            return '<span class="chip">' + esc(p) + "</span>";
          }).join("") + (b.platforms.length > 3 ? '<span class="chip chip-more">+' + (b.platforms.length - 3) + "</span>" : "") +
        "</div></td>" +
        '<td class="col-action"><button class="btn btn-small" data-review="' + b.id + '">Review</button></td>' +
      "</tr>";
    }).join("");
  }

  function bindFilters() {
    $("#f-search").addEventListener("input", function (e) { state.search = e.target.value; renderTable(); });
    $("#f-regulator").addEventListener("change", function (e) { state.regulator = e.target.value; renderTable(); });
    $("#f-platform").addEventListener("change", function (e) { state.platform = e.target.value; renderTable(); });
    $("#f-sort").addEventListener("change", function (e) { state.sort = e.target.value; renderTable(); });
    $("#f-tier1").addEventListener("change", function (e) { state.tier1 = e.target.checked; renderTable(); });
    $("#f-deposit").addEventListener("input", function (e) {
      state.maxDeposit = Number(e.target.value);
      $("#f-deposit-out").textContent = state.maxDeposit >= 200 ? "Any" : money(state.maxDeposit);
      renderTable();
    });
    $("#f-reset").addEventListener("click", resetFilters);
    $("#empty-reset").addEventListener("click", resetFilters);

    $("#hero-search").addEventListener("submit", function (e) {
      e.preventDefault();
      var q = $("#hero-search-input").value;
      $("#f-search").value = q;
      state.search = q;
      renderTable();
      $("#compare").scrollIntoView({ behavior: "smooth" });
    });
  }

  function resetFilters() {
    state.search = ""; state.regulator = ""; state.platform = "";
    state.maxDeposit = 200; state.sort = "rating"; state.tier1 = false;
    $("#f-search").value = ""; $("#f-regulator").value = ""; $("#f-platform").value = "";
    $("#f-deposit").value = 200; $("#f-deposit-out").textContent = "Any";
    $("#f-sort").value = "rating"; $("#f-tier1").checked = false;
    renderTable();
  }

  // ---------- Compare ----------
  function toggleCompare(id, on) {
    var idx = state.compare.indexOf(id);
    if (on && idx === -1) {
      if (state.compare.length >= MAX_COMPARE) {
        toast("You can compare up to " + MAX_COMPARE + " brokers at a time.");
        return false;
      }
      state.compare.push(id);
    } else if (!on && idx !== -1) {
      state.compare.splice(idx, 1);
    }
    renderTray();
    return true;
  }

  function renderTray() {
    var tray = $("#compare-tray");
    tray.hidden = state.compare.length === 0;
    document.body.classList.toggle("has-tray", state.compare.length > 0);
    var slots = [];
    for (var i = 0; i < MAX_COMPARE; i++) {
      var b = byId[state.compare[i]];
      slots.push(b
        ? '<span class="tray-item">' + logo(b, "sm") + esc(b.name) +
          '<button class="tray-remove" data-uncompare="' + b.id + '" aria-label="Remove ' + esc(b.name) + '">&times;</button></span>'
        : '<span class="tray-item tray-empty">Add a broker</span>');
    }
    $("#tray-items").innerHTML = slots.join("");
    $("#tray-compare").disabled = state.compare.length < 2;
    $("#tray-compare").textContent = state.compare.length < 2 ? "Select 2+" : "Compare " + state.compare.length;
  }

  function openCompare() {
    var list = state.compare.map(function (id) { return byId[id]; });
    var best = {
      overall: Math.max.apply(null, list.map(function (b) { return b.overall; })),
      cost: Math.min.apply(null, list.map(function (b) { return b.cost; })),
      minDeposit: Math.min.apply(null, list.map(function (b) { return b.minDeposit; })),
      instruments: Math.max.apply(null, list.map(function (b) { return b.instruments; })),
      regs: Math.max.apply(null, list.map(function (b) { return b.regulators.length; }))
    };
    function cell(b, html, isBest) {
      return "<td" + (isBest ? ' class="is-best"' : "") + ">" + html + "</td>";
    }
    var rows = [
      ["Overall rating", function (b) { return cell(b, "<strong>" + b.overall.toFixed(1) + "</strong> " + stars(b.overall), b.overall === best.overall); }],
      ["All-in EUR/USD cost", function (b) { return cell(b, money(b.cost, 2) + " / lot", b.cost === best.cost); }],
      ["Typical spread", function (b) { return cell(b, b.spread.toFixed(1) + " pips"); }],
      ["Commission (round-turn)", function (b) { return cell(b, fmtCommission(b)); }],
      ["Account type", function (b) { return cell(b, esc(b.account)); }],
      ["Minimum deposit", function (b) { return cell(b, money(b.minDeposit), b.minDeposit === best.minDeposit); }],
      ["Max. retail leverage", function (b) { return cell(b, "1:" + b.leverage); }],
      ["Instruments", function (b) { return cell(b, fmtInstruments(b.instruments), b.instruments === best.instruments); }],
      ["Regulators", function (b) { return cell(b, esc(b.regulators.join(", ")), b.regulators.length === best.regs); }],
      ["Platforms", function (b) { return cell(b, esc(b.platforms.join(", "))); }],
      ["Founded", function (b) { return cell(b, b.founded); }],
      ["Headquarters", function (b) { return cell(b, esc(b.hq)); }]
    ].concat(CATEGORIES.map(function (c) {
      var top = Math.max.apply(null, list.map(function (b) { return b.ratings[c.key]; }));
      return [c.label, function (b) { return cell(b, b.ratings[c.key].toFixed(1) + " / 5", b.ratings[c.key] === top); }];
    }));

    var html =
      '<h2 id="modal-title">Side-by-side comparison</h2>' +
      '<p class="muted">Highlighted cells show the best value in each row.</p>' +
      '<div class="table-wrap"><table class="compare-table"><thead><tr><th scope="col"><span class="sr-only">Feature</span></th>' +
      list.map(function (b) {
        return '<th scope="col"><div class="compare-head">' + logo(b) + "<span>" + esc(b.name) + "</span></div></th>";
      }).join("") + "</tr></thead><tbody>" +
      rows.map(function (r) {
        return '<tr><th scope="row">' + r[0] + "</th>" + list.map(r[1]).join("") + "</tr>";
      }).join("") +
      '<tr><th scope="row"><span class="sr-only">Actions</span></th>' + list.map(function (b) {
        return '<td><button class="btn btn-small" data-review="' + b.id + '">Full review</button></td>';
      }).join("") + "</tr>" +
      "</tbody></table></div>";
    openModal(html, "wide");
  }

  // ---------- Review modal ----------
  function openReview(id) {
    var b = byId[id];
    if (!b) return;
    var inCompare = state.compare.indexOf(id) !== -1;
    var html =
      '<header class="review-head">' + logo(b, "lg") +
        '<div><h2 id="modal-title">' + esc(b.name) + " review</h2>" +
        '<p class="muted">' + esc(b.bestFor) + " · Founded " + b.founded + " · " + esc(b.hq) + "</p></div>" +
        '<div class="review-score"><strong>' + b.overall.toFixed(1) + "</strong>" + stars(b.overall) + "<small>Overall</small></div>" +
      "</header>" +
      '<p class="review-summary">' + esc(b.summary) + "</p>" +
      '<div class="review-grid">' +
        '<section><h3>Ratings breakdown</h3><ul class="bars">' +
          CATEGORIES.map(function (c) {
            return "<li><span>" + c.label + "</span>" +
              '<span class="bar"><span style="width:' + (b.ratings[c.key] / 5) * 100 + '%"></span></span>' +
              "<b>" + b.ratings[c.key].toFixed(1) + "</b></li>";
          }).join("") +
        "</ul></section>" +
        '<section><h3>Key facts</h3><dl class="facts">' +
          "<div><dt>EUR/USD spread</dt><dd>" + b.spread.toFixed(1) + " pips (" + esc(b.account) + ")</dd></div>" +
          "<div><dt>Commission</dt><dd>" + (b.commission ? money(b.commission, 2) + " per lot round-turn" : "None") + "</dd></div>" +
          "<div><dt>All-in cost</dt><dd>" + money(b.cost, 2) + " per standard lot</dd></div>" +
          "<div><dt>Min deposit</dt><dd>" + money(b.minDeposit) + "</dd></div>" +
          "<div><dt>Max leverage</dt><dd>1:" + b.leverage + " <small class=\"muted\">(varies by entity)</small></dd></div>" +
          "<div><dt>Instruments</dt><dd>" + fmtInstruments(b.instruments) + "</dd></div>" +
        "</dl></section>" +
      "</div>" +
      '<div class="review-grid">' +
        '<section><h3>Pros</h3><ul class="pros">' + b.pros.map(function (p) { return "<li>" + esc(p) + "</li>"; }).join("") + "</ul></section>" +
        '<section><h3>Cons</h3><ul class="cons">' + b.cons.map(function (p) { return "<li>" + esc(p) + "</li>"; }).join("") + "</ul></section>" +
      "</div>" +
      '<div class="review-grid">' +
        '<section><h3>Regulation</h3><div class="chips">' + b.regulators.map(function (r) {
          return '<span class="chip' + (TIER1.indexOf(r) !== -1 ? " chip-tier1" : "") + '">' + esc(r) + "</span>";
        }).join("") + '</div><p class="muted small">Highlighted = tier-1 regulator.</p></section>' +
        '<section><h3>Platforms</h3><div class="chips">' + b.platforms.map(function (p) {
          return '<span class="chip">' + esc(p) + "</span>";
        }).join("") + "</div></section>" +
      "</div>" +
      '<footer class="review-actions">' +
        brokerCta(b) +
        '<a class="btn btn-ghost" href="' + reviewUrl(b) + '">Read full review</a>' +
        '<button class="btn btn-ghost" data-toggle-compare="' + b.id + '">' + (inCompare ? "Remove from compare" : "Add to compare") + "</button>" +
        '<button class="btn btn-ghost" data-share="' + b.id + '">Copy link</button>' +
      "</footer>" +
      '<p class="muted small">Data is indicative and may vary by country. Always verify on the broker\'s website. ' +
      "Most retail CFD accounts lose money. We may earn a commission if you open an account through our links.</p>";
    openModal(html);
    if (location.hash !== "#broker/" + id) history.replaceState(null, "", "#broker/" + id);
  }

  // ---------- Modal ----------
  var modal, lastFocus;
  function openModal(html, variant) {
    lastFocus = document.activeElement;
    $("#modal-body").innerHTML = html;
    modal.classList.toggle("modal-wide", variant === "wide");
    if (!modal.open) {
      if (typeof modal.showModal === "function") modal.showModal();
      else modal.setAttribute("open", "");
    }
    modal.scrollTop = 0;
    document.body.classList.add("modal-open");
  }
  function closeModal() {
    if (typeof modal.close === "function" && modal.open) modal.close();
    else modal.removeAttribute("open");
  }
  function onModalClosed() {
    document.body.classList.remove("modal-open");
    if (location.hash.indexOf("#broker/") === 0) history.replaceState(null, "", location.pathname + location.search);
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }

  // ---------- Calculator ----------
  function renderCalc() {
    var trades = Math.max(0, Number($("#c-trades").value) || 0);
    var lots = Math.max(0, Number($("#c-lots").value) || 0);
    var list = BROKERS.map(function (b) {
      return { b: b, monthly: b.cost * trades * lots };
    }).sort(function (x, y) { return x.monthly - y.monthly; });
    var max = list.length ? list[list.length - 1].monthly || 1 : 1;
    $("#calc-results").innerHTML = list.map(function (r, i) {
      return '<li class="' + (i === 0 ? "is-cheapest" : "") + '">' +
        '<span class="calc-rank">' + (i + 1) + "</span>" +
        '<span class="calc-name">' + logo(r.b, "sm") + '<button class="link-btn" data-review="' + r.b.id + '">' + esc(r.b.name) + "</button></span>" +
        '<span class="calc-bar"><span style="width:' + Math.max(2, (r.monthly / max) * 100) + '%"></span></span>' +
        '<span class="calc-val"><strong>' + money(r.monthly, 2) + '</strong><small class="muted">/month</small></span>' +
      "</li>";
    }).join("");
  }

  // ---------- Methodology ----------
  function renderMethod() {
    $("#method-grid").innerHTML = CATEGORIES.map(function (c) {
      return '<div class="method-card"><span class="method-weight">' + Math.round(c.weight * 100) + "%</span>" +
        "<h3>" + c.label + "</h3><p>" + c.desc + "</p></div>";
    }).join("");
  }

  // ---------- Theme & nav ----------
  function currentTheme() {
    var attr = document.documentElement.getAttribute("data-theme");
    if (attr) return attr;
    return window.matchMedia && matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  function bindChrome() {
    $("#theme-toggle").addEventListener("click", function () {
      var next = currentTheme() === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      try { localStorage.setItem("br-theme", next); } catch (e) {}
    });
    var nav = $("#main-nav"), menuBtn = $("#menu-toggle");
    menuBtn.addEventListener("click", function () {
      var open = nav.classList.toggle("open");
      menuBtn.setAttribute("aria-expanded", String(open));
    });
    nav.addEventListener("click", function (e) {
      if (e.target.tagName === "A") { nav.classList.remove("open"); menuBtn.setAttribute("aria-expanded", "false"); }
    });
    $("#year").textContent = new Date().getFullYear();
  }

  // ---------- Global event delegation ----------
  function bindDelegation() {
    document.addEventListener("click", function (e) {
      var t = e.target.closest("[data-review],[data-uncompare],[data-toggle-compare],[data-share]");
      if (!t) return;
      if (t.dataset.review) { openReview(t.dataset.review); }
      else if (t.dataset.uncompare) { toggleCompare(t.dataset.uncompare, false); renderTable(); }
      else if (t.dataset.toggleCompare) {
        var id = t.dataset.toggleCompare, on = state.compare.indexOf(id) === -1;
        if (toggleCompare(id, on)) {
          t.textContent = on ? "Remove from compare" : "Add to compare";
          toast(on ? byId[id].name + " added to compare" : byId[id].name + " removed from compare");
          renderTable();
        }
      } else if (t.dataset.share) {
        var url = location.origin + location.pathname + "#broker/" + t.dataset.share;
        if (navigator.clipboard) {
          navigator.clipboard.writeText(url).then(function () { toast("Link copied"); }, function () { toast(url); });
        } else { toast(url); }
      }
    });
    document.addEventListener("change", function (e) {
      var id = e.target.dataset && e.target.dataset.compare;
      if (!id) return;
      if (!toggleCompare(id, e.target.checked)) e.target.checked = false;
    });

    $("#tray-clear").addEventListener("click", function () { state.compare = []; renderTray(); renderTable(); });
    $("#tray-compare").addEventListener("click", openCompare);

    modal = $("#modal");
    $("#modal-close").addEventListener("click", closeModal);
    modal.addEventListener("close", onModalClosed);
    modal.addEventListener("click", function (e) { if (e.target === modal) closeModal(); });

    ["#c-trades", "#c-lots"].forEach(function (s) { $(s).addEventListener("input", renderCalc); });
    $("#calc-form").addEventListener("submit", function (e) { e.preventDefault(); });
  }

  function handleHash() {
    var m = location.hash.match(/^#broker\/([\w-]+)$/);
    if (m && byId[m[1]]) openReview(m[1]);
  }

  // ---------- Init ----------
  populateFilters();
  renderTopPicks();
  renderTable();
  renderTray();
  renderCalc();
  renderMethod();
  bindFilters();
  bindChrome();
  bindDelegation();
  handleHash();
  window.addEventListener("hashchange", handleHash);
})();
