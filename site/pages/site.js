/* Fills links and counters from config.js. Pages stay readable without it. */
(function () {
  var c = window.FNAM || {};
  document.querySelectorAll("[data-cfg-href]").forEach(function (a) { var v = c[a.getAttribute("data-cfg-href")]; if (v) a.href = v; });
  document.querySelectorAll("[data-cfg-text]").forEach(function (e) { var v = c[e.getAttribute("data-cfg-text")]; if (v !== undefined) e.textContent = v; });
  document.querySelectorAll("[data-pledge-bar]").forEach(function (e) { e.style.width = Math.min(100, 100 * c.PLEDGE_PAID / c.PLEDGE_GOAL) + "%"; });
})();
