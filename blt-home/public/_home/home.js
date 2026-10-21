// owaspblt.org landing page behaviour. Everything here is progressive: the page
// is complete without it (all products listed, live numbers simply absent).
(function () {
  "use strict";

  var root = document.documentElement;
  var reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function $(sel, ctx) { return (ctx || document).querySelector(sel); }
  function $all(sel, ctx) { return Array.prototype.slice.call((ctx || document).querySelectorAll(sel)); }
  function el(tag, cls, text) {
    var node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text != null) node.textContent = String(text);
    return node;
  }

  // ---- Theme --------------------------------------------------------------
  var themeToggle = $("#theme-toggle");
  function syncThemeLabel() {
    if (themeToggle) themeToggle.setAttribute("aria-label", root.classList.contains("dark") ? "Switch to light theme" : "Switch to dark theme");
  }
  if (themeToggle) {
    syncThemeLabel();
    themeToggle.addEventListener("click", function () {
      var dark = !root.classList.contains("dark");
      root.classList.toggle("dark", dark);
      try { localStorage.setItem("theme", dark ? "dark" : "light"); } catch (e) { /* private mode */ }
      syncThemeLabel();
    });
  }

  // ---- Mobile menu -------------------------------------------------------
  var mobileToggle = $("#mobile-toggle");
  var mobileMenu = $("#mobile-menu");
  function setMobile(open) {
    mobileMenu.classList.toggle("open", open);
    mobileToggle.classList.toggle("active", open);
    mobileToggle.setAttribute("aria-expanded", String(open));
  }
  if (mobileToggle && mobileMenu) {
    mobileToggle.addEventListener("click", function () { setMobile(!mobileMenu.classList.contains("open")); });
    $all("a", mobileMenu).forEach(function (a) { a.addEventListener("click", function () { setMobile(false); }); });
  }

  // ---- Products: read once from the Explore cards --------------------------
  var products = $all("#explore-groups .product-card").map(function (a) {
    var img = $("img", a);
    return {
      href: a.getAttribute("href"),
      name: ($("strong", a) || a).textContent.trim(),
      logo: img ? img.getAttribute("src") : "",
      group: a.closest(".explore-group").getAttribute("data-group"),
    };
  });

  // ---- Apps launcher -------------------------------------------------------
  var appsGrid = $("#apps-grid");
  var appsTrigger = $("#apps-trigger");
  var appsPanel = $("#apps-panel");
  var appsWrap = $("#apps-launcher");
  var appsBuilt = false;
  function buildApps() {
    if (appsBuilt || !appsGrid) return;
    appsBuilt = true;
    products.forEach(function (p) {
      var li = el("li");
      var a = el("a", "group flex flex-col items-center gap-1.5 rounded-2xl px-1 py-3 transition-colors hover:bg-red-50/80 dark:hover:bg-gray-800");
      a.href = p.href;
      var img = el("img", "h-10 w-10 object-contain transition-transform group-hover:scale-105");
      img.src = p.logo;
      img.alt = "";
      img.width = 40;
      img.height = 40;
      img.decoding = "async";
      var label = el("span", "max-w-full truncate text-[0.6875rem] font-medium text-gray-700 dark:text-gray-300", p.name.replace(/^BLT-/, ""));
      a.appendChild(img);
      a.appendChild(label);
      li.appendChild(a);
      appsGrid.appendChild(li);
    });
  }
  function setApps(open) {
    if (open) buildApps();
    appsPanel.classList.toggle("open", open);
    appsTrigger.setAttribute("aria-expanded", String(open));
  }
  if (appsTrigger && appsPanel && appsWrap) {
    appsTrigger.addEventListener("click", function () { setApps(!appsPanel.classList.contains("open")); });
    document.addEventListener("click", function (e) { if (!appsWrap.contains(e.target)) setApps(false); });
    $all("a", appsPanel).forEach(function (a) { a.addEventListener("click", function () { setApps(false); }); });
  }
  document.addEventListener("keydown", function (e) {
    if (e.key !== "Escape") return;
    if (appsPanel && appsPanel.classList.contains("open")) { setApps(false); appsTrigger.focus(); }
    if (mobileMenu && mobileMenu.classList.contains("open")) { setMobile(false); mobileToggle.focus(); }
  });

  // ---- Explore: tabs + orbit ------------------------------------------------
  var tabList = $("#explore-tabs");
  var groups = $all("#explore-groups .explore-group");
  var orbitSvg = $("#orbit-svg");
  var orbit = $("#orbit");
  var SVGNS = "http://www.w3.org/2000/svg";

  function drawOrbit(group) {
    if (!orbit || !orbitSvg) return;
    $all(".orbit-node", orbit).forEach(function (n) { n.remove(); });
    while (orbitSvg.firstChild) orbitSvg.removeChild(orbitSvg.firstChild);
    var items = products.filter(function (p) { return p.group === group; }).slice(0, 14);
    var size = 416, c = size / 2;
    var inner = items.slice(0, Math.min(6, items.length));
    var outer = items.slice(inner.length);
    var placed = [];
    [[inner, 105, -90], [outer, 178, -70]].forEach(function (ring) {
      ring[0].forEach(function (p, i) {
        var a = ((ring[2] + (360 / ring[0].length) * i) * Math.PI) / 180;
        placed.push({ p: p, x: c + Math.cos(a) * ring[1], y: c + Math.sin(a) * ring[1] * 0.92 });
      });
    });
    placed.forEach(function (item, i) {
      var path = document.createElementNS(SVGNS, "path");
      var cx = c + (item.x - c) * 0.36, cy = c + (item.y - c) * 0.3 - 30;
      path.setAttribute("d", "M " + c + " " + c + " Q " + cx + " " + cy + " " + item.x + " " + item.y);
      path.setAttribute("class", "orbit-beam");
      orbitSvg.appendChild(path);
      var node = el("a", "orbit-node");
      node.href = item.p.href;
      node.tabIndex = -1; // the same links are in the card grid; keep the tab order short
      node.title = item.p.name;
      node.style.left = (item.x / size) * 100 + "%";
      node.style.top = (item.y / size) * 100 + "%";
      node.style.animationDelay = (i % 5) * -0.7 + "s";
      var img = el("img");
      img.src = item.p.logo;
      img.alt = "";
      img.loading = "lazy";
      node.appendChild(img);
      node.addEventListener("mouseenter", function () {
        $all(".orbit-beam", orbitSvg).forEach(function (b, j) { b.classList.toggle("active", j === i); });
      });
      orbit.appendChild(node);
    });
  }

  function selectGroup(name, focus) {
    $all('[role="tab"]', tabList).forEach(function (tab) {
      var on = tab.getAttribute("data-group") === name;
      tab.setAttribute("aria-selected", String(on));
      tab.tabIndex = on ? 0 : -1;
      if (on && focus) tab.focus();
    });
    groups.forEach(function (g) { g.hidden = g.getAttribute("data-group") !== name; });
    drawOrbit(name);
  }

  if (tabList && groups.length) {
    groups.forEach(function (g) {
      var name = g.getAttribute("data-group");
      var heading = $("h3", g);
      var count = $all(".product-card", g).length;
      var tab = el("button", "explore-tab rounded-full border border-gray-200 bg-white px-4 py-1.5 text-sm font-medium text-gray-700 transition-colors hover:border-red-300 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-200");
      tab.type = "button";
      tab.id = "tab-" + name;
      tab.setAttribute("role", "tab");
      tab.setAttribute("data-group", name);
      tab.setAttribute("aria-controls", g.id || (g.id = "panel-" + name));
      tab.textContent = heading.textContent + " ";
      tab.appendChild(el("span", "opacity-60", "(" + count + ")"));
      tab.addEventListener("click", function () { selectGroup(name, false); });
      tabList.appendChild(tab);
      g.setAttribute("role", "tabpanel");
      g.setAttribute("aria-labelledby", tab.id);
      heading.classList.add("sr-only");
    });
    tabList.addEventListener("keydown", function (e) {
      var tabs = $all('[role="tab"]', tabList);
      var i = tabs.indexOf(document.activeElement);
      if (i < 0) return;
      var next = e.key === "ArrowRight" ? i + 1 : e.key === "ArrowLeft" ? i - 1 : e.key === "Home" ? 0 : e.key === "End" ? tabs.length - 1 : null;
      if (next === null) return;
      e.preventDefault();
      next = (next + tabs.length) % tabs.length;
      selectGroup(tabs[next].getAttribute("data-group"), true);
    });
    tabList.hidden = false;
    selectGroup(groups[0].getAttribute("data-group"), false);
  }

  // ---- Hero: Conway's Game of Life (Kaif's design) -------------------------
  (function () {
    var canvas = $("#lifeCanvas");
    if (!canvas || !canvas.getContext) return;
    var ctx = canvas.getContext("2d");
    var grid = [], cols = 0, rows = 0, cell = 6, timer = 0, visible = true;

    function resize() {
      var rect = canvas.getBoundingClientRect();
      var dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.max(1, Math.floor(rect.width * dpr));
      canvas.height = Math.max(1, Math.floor(rect.height * dpr));
      cell = 6 * dpr;
      cols = Math.floor(canvas.width / cell);
      rows = Math.floor(canvas.height / cell);
      grid = [];
      for (var i = 0; i < rows; i++) {
        var row = [];
        for (var j = 0; j < cols; j++) {
          var alive = Math.random() > 0.86;
          row.push({ alive: alive, opacity: alive ? 0.45 : 0 });
        }
        grid.push(row);
      }
    }
    function neighbours(x, y) {
      var sum = 0;
      for (var dx = -1; dx <= 1; dx++) for (var dy = -1; dy <= 1; dy++) {
        if (!dx && !dy) continue;
        if (grid[(x + dx + rows) % rows][(y + dy + cols) % cols].alive) sum++;
      }
      return sum;
    }
    function draw(step) {
      var dark = root.classList.contains("dark");
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      var rgb = dark ? "255,255,255" : "0,0,0";
      var r = Math.max(1, cell / 6);
      for (var i = 0; i < rows; i++) for (var j = 0; j < cols; j++) {
        var it = grid[i][j];
        if (it.alive && it.opacity < 0.5) it.opacity = Math.min(it.opacity + 0.16, 0.5);
        if (!it.alive && it.opacity > 0) it.opacity = Math.max(it.opacity - 0.16, 0);
        if (it.opacity > 0) {
          ctx.fillStyle = "rgba(" + rgb + "," + (dark ? it.opacity * 0.6 : it.opacity) + ")";
          ctx.beginPath();
          ctx.arc(j * cell + cell / 2, i * cell + cell / 2, r, 0, Math.PI * 2);
          ctx.fill();
        }
      }
      if (!step) return;
      grid = grid.map(function (row, i) {
        return row.map(function (it, j) {
          var n = neighbours(i, j);
          return { alive: it.alive ? n === 2 || n === 3 : n === 3, opacity: it.opacity };
        });
      });
    }
    function loop() {
      window.clearTimeout(timer);
      if (!visible || document.hidden) return;
      draw(true);
      timer = window.setTimeout(function () { window.requestAnimationFrame(loop); }, 125);
    }
    function start() {
      resize();
      if (reduceMotion) draw(false); // one still frame, no animation
      else loop();
    }
    start();
    var lastWidth = window.innerWidth;
    window.addEventListener("resize", function () {
      if (window.innerWidth === lastWidth) return; // ignore mobile URL-bar height changes
      lastWidth = window.innerWidth;
      start();
    });
    if (!reduceMotion) {
      document.addEventListener("visibilitychange", loop);
      if ("IntersectionObserver" in window) {
        new IntersectionObserver(function (entries) {
          visible = entries[0].isIntersecting;
          loop();
        }).observe(canvas);
      }
    }
    if (themeToggle) themeToggle.addEventListener("click", function () { if (reduceMotion) draw(false); });
  })();

  // ---- Live numbers ------------------------------------------------------------
  var fmt = new Intl.NumberFormat("en");
  function pick(obj, path) {
    return path.split(".").reduce(function (o, k) { return o == null ? undefined : o[k]; }, obj);
  }
  function isNum(v) { return typeof v === "number" && isFinite(v) && v >= 0; }
  // Attributes, not the .hidden property: some of these are SVG elements.
  function show(selector) { $all(selector).forEach(function (n) { n.removeAttribute("hidden"); }); }
  function hideFallback(name) { $all('[data-live-fallback="' + name + '"]').forEach(function (n) { n.setAttribute("hidden", ""); }); }

  function render(data) {
    if (!data || typeof data !== "object") return;
    var pool = data.pool;
    if (pool && pool.month) {
      var parts = pool.month.split("-");
      pool.monthLabel = new Date(Date.UTC(+parts[0], +parts[1] - 1, 1)).toLocaleString("en", { month: "long", year: "numeric", timeZone: "UTC" });
    }
    // Plain number slots. textContent only: fetched data is never parsed as HTML.
    $all("[data-stat]").forEach(function (node) {
      var v = pick(data, node.getAttribute("data-stat"));
      if (isNum(v)) node.textContent = fmt.format(v);
      else if (typeof v === "string") node.textContent = v;
    });
    var anyNumber = false;
    $all("[data-stat-card]").forEach(function (card) {
      if (isNum(pick(data, card.getAttribute("data-stat-card")))) { card.hidden = false; anyNumber = true; }
    });
    if (anyNumber) show("#numbers");
    if (isNum(pick(data, "forge.openIssues"))) show('[data-live="forge.openIssues"]');

    // Bugs logged (BLT-Pages): only shown once there is at least one report.
    if (data.pages && isNum(data.pages.bugs) && data.pages.bugs > 0) {
      var bugs = $('[data-live="bugs"]');
      bugs.textContent = fmt.format(data.pages.bugs);
      show('[data-live="bugs"], [data-live="bugs-label"]');
      hideFallback("bugs");
      hideFallback("bugs-label");
    }

    // Activity: one square per week of commits, shaded by quartile of the
    // non-empty weeks. Quiet weeks are simply light squares.
    var forge = data.forge;
    if (forge && Array.isArray(forge.weeks) && forge.weeks.length >= 12 && isNum(forge.recentCommits)) {
      var weeks = forge.weeks.filter(isNum);
      var busy = weeks.filter(function (n) { return n > 0; }).sort(function (a, b) { return a - b; });
      var cut = [0.25, 0.5, 0.75].map(function (q) { return busy.length ? busy[Math.floor(q * (busy.length - 1))] : 0; });
      var grid = $("#activity-grid");
      var startMs = Date.parse(forge.weeksStart);
      weeks.forEach(function (n, i) {
        var level = n <= 0 ? 0 : n <= cut[0] ? 1 : n <= cut[1] ? 2 : n <= cut[2] ? 3 : 4;
        var cell = el("li", "heat-" + level + (i === weeks.length - 1 ? " heat-now" : ""));
        cell.style.animationDelay = (i * 12) + "ms";
        if (isFinite(startMs)) {
          var label = new Date(startMs + i * 7 * 864e5).toLocaleDateString("en", { month: "short", day: "numeric", timeZone: "UTC" });
          cell.title = "Week of " + label + ": " + fmt.format(n) + (n === 1 ? " commit" : " commits");
        }
        grid.appendChild(cell);
      });
      show('[data-live="activity"]');
      hideFallback("activity");
    }

    // BLT-Pool: this month's top contributors.
    if (pool && Array.isArray(pool.top) && pool.top.length && pool.monthLabel) {
      var list = $("#pool-top");
      pool.top.forEach(function (row, idx) {
        if (!row || typeof row.login !== "string" || !isNum(row.points)) return;
        var li = el("li", "relative flex min-h-[1.5rem] items-center pl-9");
        var badge = el("span", "absolute left-0 top-0 flex h-6 w-6 items-center justify-center rounded-full bg-gray-900 text-[0.65rem] font-bold uppercase text-white ring-4 ring-white dark:bg-white dark:text-gray-900 dark:ring-gray-900", row.login.charAt(0));
        badge.setAttribute("aria-hidden", "true");
        var text = el("span", "min-w-0");
        text.appendChild(el("span", "block truncate text-xs font-medium text-gray-900 dark:text-white", row.login));
        text.appendChild(el("span", "block text-[0.65rem] text-red-600 dark:text-red-400", "#" + (idx + 1) + " · " + fmt.format(row.points) + " points"));
        li.appendChild(badge);
        li.appendChild(text);
        list.appendChild(li);
      });
      if (list.children.length) {
        show('[data-live="pool"]');
        hideFallback("pool");
      }
    }
  }

  if (window.fetch) {
    fetch("/api/home-stats", { headers: { accept: "application/json" } })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(render)
      .catch(function () { /* leave every live number hidden */ });
  }
})();
