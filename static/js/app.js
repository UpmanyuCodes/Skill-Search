// Skill Search front-end helpers (no build step needed).
(function () {
  "use strict";

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const finePointer = window.matchMedia("(hover: hover) and (pointer: fine)").matches;

  function getCookie(name) {
    const match = document.cookie.match(new RegExp("(^|;\\s*)" + name + "=([^;]*)"));
    return match ? decodeURIComponent(match[2]) : "";
  }

  // ---- "Use my location" buttons -----------------------------------------
  // data-lat / data-lng point at the inputs to fill, data-status at an element
  // for feedback, data-submit submits the form afterwards.
  document.querySelectorAll("[data-locate]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      const latInput = document.querySelector(btn.dataset.lat);
      const lngInput = document.querySelector(btn.dataset.lng);
      const status = btn.dataset.status ? document.querySelector(btn.dataset.status) : null;
      const say = function (msg, cls) { if (status) { status.textContent = msg; status.className = "small " + (cls || "text-secondary"); } };
      if (!navigator.geolocation) { say("Location is not supported by this browser.", "text-danger"); return; }
      say("Finding your location...");
      btn.disabled = true;
      navigator.geolocation.getCurrentPosition(function (pos) {
        latInput.value = pos.coords.latitude.toFixed(6);
        lngInput.value = pos.coords.longitude.toFixed(6);
        btn.disabled = false;
        say("Location captured ✓", "text-success");
        if (btn.dataset.submit !== undefined) {
          const form = btn.form || latInput.form;
          const city = form.querySelector('[name="city"]');
          if (city) city.value = "";  // location wins over a typed city
          form.submit();
        }
      }, function (err) {
        btn.disabled = false;
        const why = err.code === 1 ? "permission was denied" : "it timed out";
        say("Couldn't get your location (" + why + "). Type your city instead.", "text-danger");
      }, { enableHighAccuracy: false, timeout: 10000, maximumAge: 600000 });
    });
  });

  // ---- Save / unsave providers without reloading -------------------------
  document.querySelectorAll("form[data-fav]").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      fetch(form.action, {
        method: "POST",
        headers: { "X-CSRFToken": getCookie("csrftoken"), "X-Requested-With": "XMLHttpRequest" },
        credentials: "same-origin",
      }).then(function (r) {
        if (r.redirected || !r.ok) { window.location.reload(); return null; }
        return r.json();
      }).then(function (data) {
        if (!data) return;
        const btn = form.querySelector("button");
        btn.classList.toggle("saved", data.saved);
        const icon = btn.querySelector("i");
        icon.className = data.saved ? "bi bi-heart-fill" : "bi bi-heart";
        if (btn.classList.contains("btn")) icon.classList.toggle("text-danger", data.saved);
        const label = btn.querySelector("[data-label]");
        if (label) label.textContent = data.saved ? "Saved" : "Save";
      }).catch(function () { form.submit(); });
    });
  });

  // ---- Share button -------------------------------------------------------
  document.querySelectorAll("[data-share]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      const data = { title: document.title, url: window.location.href };
      if (navigator.share) { navigator.share(data).catch(function () {}); return; }
      navigator.clipboard.writeText(data.url).then(function () {
        const old = btn.innerHTML;
        btn.innerHTML = '<i class="bi bi-check2"></i> Link copied';
        setTimeout(function () { btn.innerHTML = old; }, 1800);
      });
    });
  });

  // ---- Flash messages fade out on their own ------------------------------
  document.querySelectorAll(".flash-stack .alert").forEach(function (el, i) {
    setTimeout(function () {
      if (window.bootstrap) bootstrap.Alert.getOrCreateInstance(el).close(); else el.remove();
    }, 6000 + i * 600);
  });

  // ---- Stop double submits -----------------------------------------------
  document.querySelectorAll("form[method=post]:not([data-fav]):not([data-chat])").forEach(function (form) {
    form.addEventListener("submit", function () {
      setTimeout(function () {
        form.querySelectorAll("button:not([type=button])").forEach(function (b) { b.disabled = true; });
      }, 0);
    });
  });

  // ---- 3D: hero stage follows the pointer --------------------------------
  const scene = document.querySelector("[data-scene]");
  if (scene && finePointer && !reduceMotion) {
    const stage = scene.querySelector(".scene-stage");
    const host = scene.closest(".hero") || scene;
    host.addEventListener("pointermove", function (e) {
      const r = host.getBoundingClientRect();
      const x = (e.clientX - r.left) / r.width - 0.5;
      const y = (e.clientY - r.top) / r.height - 0.5;
      stage.style.setProperty("--ry", (x * 26).toFixed(2) + "deg");
      stage.style.setProperty("--rx", (8 - y * 16).toFixed(2) + "deg");
    });
    host.addEventListener("pointerleave", function () {
      stage.style.removeProperty("--ry");
      stage.style.removeProperty("--rx");
    });
  }

  // ---- 3D: cards tilt toward the pointer ---------------------------------
  if (finePointer && !reduceMotion) {
    document.querySelectorAll("[data-tilt]").forEach(function (el) {
      const max = parseFloat(el.dataset.tilt) || 8;
      el.classList.add("tilt");
      el.addEventListener("pointermove", function (e) {
        const r = el.getBoundingClientRect();
        const x = (e.clientX - r.left) / r.width;
        const y = (e.clientY - r.top) / r.height;
        el.style.setProperty("--ty", ((x - 0.5) * 2 * max).toFixed(2) + "deg");
        el.style.setProperty("--tx", ((0.5 - y) * 2 * max).toFixed(2) + "deg");
        el.style.setProperty("--mx", (x * 100).toFixed(1) + "%");
        el.style.setProperty("--my", (y * 100).toFixed(1) + "%");
      });
      el.addEventListener("pointerleave", function () {
        el.style.setProperty("--tx", "0deg");
        el.style.setProperty("--ty", "0deg");
      });
    });
  }

  // ---- Scroll reveal ------------------------------------------------------
  if ("IntersectionObserver" in window && !reduceMotion && document.visibilityState === "visible") {
    const io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) { entry.target.classList.add("in"); io.unobserve(entry.target); }
      });
    }, { threshold: 0.08, rootMargin: "0px 0px -40px 0px" });
    const fold = window.innerHeight;
    document.querySelectorAll("[data-reveal], .cat-tile, .provider-card, .step-card, .panel, .form-card, .cta-card").forEach(function (el) {
      if (el.getBoundingClientRect().top < fold) return;  // already on screen: leave it alone
      const siblings = el.parentElement && el.parentElement.parentElement ? Array.prototype.indexOf.call(el.parentElement.parentElement.children, el.parentElement) : 0;
      el.style.setProperty("--d", Math.min(Math.max(siblings, 0), 6) * 60 + "ms");
      el.classList.add("reveal");
      io.observe(el);
    });
  }

  // ---- Count-up numbers ---------------------------------------------------
  document.querySelectorAll("[data-count]").forEach(function (el) {
    const target = parseInt(el.dataset.count, 10) || 0;
    if (reduceMotion || target === 0) { el.textContent = target.toLocaleString("en-IN"); return; }
    const start = performance.now(), duration = 1400;
    (function tick(now) {
      const t = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - t, 4);
      el.textContent = Math.round(target * eased).toLocaleString("en-IN");
      if (t < 1) requestAnimationFrame(tick);
    })(start);
    // If the tab is hidden rAF never fires, so make sure the real number shows.
    setTimeout(function () { el.textContent = target.toLocaleString("en-IN"); }, duration + 400);
  });

  // ---- Chat: live updates, Enter to send ---------------------------------
  const chat = document.getElementById("chat-window");
  if (chat) {
    chat.scrollTop = chat.scrollHeight;
    const form = document.querySelector("form[data-chat]");
    const box = form ? form.querySelector("textarea") : null;
    if (box) {
      box.focus();
      box.addEventListener("keydown", function (e) {
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          if (box.value.trim()) form.requestSubmit ? form.requestSubmit() : form.submit();
        }
      });
    }
    const pollUrl = chat.dataset.poll;
    let last = parseInt(chat.dataset.last, 10) || 0;
    if (pollUrl) {
      setInterval(function () {
        if (document.hidden) return;
        fetch(pollUrl + "?after=" + last, { credentials: "same-origin", headers: { "X-Requested-With": "XMLHttpRequest" } })
          .then(function (r) { return r.ok ? r.json() : { messages: [] }; })
          .then(function (data) {
            data.messages.forEach(function (m) {
              const empty = chat.querySelector("[data-empty]");
              if (empty) empty.remove();
              const bubble = document.createElement("div");
              bubble.className = "bubble them";
              bubble.textContent = m.body;
              const time = document.createElement("span");
              time.className = "time";
              time.textContent = m.time;
              bubble.appendChild(time);
              chat.appendChild(bubble);
              last = Math.max(last, m.id);
              chat.scrollTop = chat.scrollHeight;
            });
          }).catch(function () {});
      }, 4000);
    }
  }
})();

// Re-enable buttons when a page comes back from the browser's back/forward cache.
window.addEventListener("pageshow", function (e) {
  if (e.persisted) document.querySelectorAll("button[disabled]").forEach(function (b) { b.disabled = false; });
});
