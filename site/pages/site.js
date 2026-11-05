/* Fills links and counters from config.js. Pages stay readable without it. */
(function () {
  var c = window.FNAM || {};
  document.querySelectorAll("[data-cfg-href]").forEach(function (a) { var v = c[a.getAttribute("data-cfg-href")]; if (v) a.href = v; });
  document.querySelectorAll("[data-cfg-text]").forEach(function (e) { var v = c[e.getAttribute("data-cfg-text")]; if (v !== undefined) e.textContent = v; });
  document.querySelectorAll("[data-pledge-bar]").forEach(function (e) { e.style.width = Math.min(100, 100 * c.PLEDGE_PAID / c.PLEDGE_GOAL) + "%"; });
})();

/* Side-by-side loopers: one slider and play button drive both panes. Frames preload once the looper is on screen. */
(function () {
  document.querySelectorAll("figure.looper").forEach(function (f) {
    var hours = f.dataset.hours.split(",").map(Number), base = f.dataset.base, field = f.dataset.field;
    var imgs = f.querySelectorAll("img[data-m]"), sl = f.querySelector(".lp-slider"), btn = f.querySelector(".lp-play");
    var hr = f.querySelector(".lp-hr"), timer = null, loaded = false;
    function src(m, h) { return base.replace("{m}", m) + String(h).padStart(3, "0") + "-" + field + ".png"; }
    function show(i) {
      var h = hours[i];
      imgs.forEach(function (im) { im.src = src(im.dataset.m, h); });
      hr.textContent = "f" + String(h).padStart(2, "0");
    }
    function preload() {
      if (loaded) return; loaded = true;
      hours.forEach(function (h) { imgs.forEach(function (im) { new Image().src = src(im.dataset.m, h); }); });
    }
    function stop() { clearInterval(timer); timer = null; btn.innerHTML = "&#9654;"; btn.setAttribute("aria-label", "Play"); }
    sl.addEventListener("input", function () { stop(); preload(); show(+sl.value); });
    btn.addEventListener("click", function () {
      if (timer) return stop();
      preload(); btn.innerHTML = "&#10074;&#10074;"; btn.setAttribute("aria-label", "Pause");
      timer = setInterval(function () { sl.value = (+sl.value + 1) % hours.length; show(+sl.value); }, 600);
    });
    if ("IntersectionObserver" in window) {
      new IntersectionObserver(function (es, o) { if (es[0].isIntersecting) { preload(); o.disconnect(); } }, { rootMargin: "200px" }).observe(f);
    }
  });
})();
