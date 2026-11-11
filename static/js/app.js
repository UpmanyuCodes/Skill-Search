// Skill Search front-end helpers (no build step needed).
(function () {
  "use strict";

  function getCookie(name) {
    const match = document.cookie.match(new RegExp("(^|;\\s*)" + name + "=([^;]*)"));
    return match ? decodeURIComponent(match[2]) : "";
  }

  // "Use my location" buttons: data-lat / data-lng point at the inputs to fill,
  // data-status at an element for feedback, data-submit submits the form.
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
        if (btn.dataset.submit !== undefined) { btn.form ? btn.form.submit() : latInput.form.submit(); }
      }, function (err) {
        btn.disabled = false;
        say("Couldn't get location (" + err.message + "). You can type your city instead.", "text-danger");
      }, { enableHighAccuracy: false, timeout: 10000, maximumAge: 600000 });
    });
  });

  // Save / unsave providers without reloading.
  document.querySelectorAll("form[data-fav]").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      fetch(form.action, {
        method: "POST",
        headers: { "X-CSRFToken": getCookie("csrftoken"), "X-Requested-With": "XMLHttpRequest" },
        credentials: "same-origin",
      }).then(function (r) {
        if (r.redirected || r.status === 403) { window.location = form.dataset.login || form.action; return null; }
        return r.json();
      }).then(function (data) {
        if (!data) return;
        const btn = form.querySelector("button");
        btn.classList.toggle("saved", data.saved);
        btn.querySelector("i").className = data.saved ? "bi bi-heart-fill" : "bi bi-heart";
        const label = btn.querySelector("[data-label]");
        if (label) label.textContent = data.saved ? "Saved" : "Save";
      });
    });
  });

  // Copy-to-clipboard buttons.
  document.querySelectorAll("[data-copy]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      navigator.clipboard.writeText(btn.dataset.copy).then(function () {
        const old = btn.innerHTML;
        btn.innerHTML = '<i class="bi bi-check2"></i> Copied';
        setTimeout(function () { btn.innerHTML = old; }, 1500);
      });
    });
  });

  // Share button (Web Share API with clipboard fallback).
  document.querySelectorAll("[data-share]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      const data = { title: document.title, url: window.location.href };
      if (navigator.share) { navigator.share(data).catch(function () {}); }
      else { navigator.clipboard.writeText(data.url); btn.innerHTML = '<i class="bi bi-check2"></i> Link copied'; }
    });
  });

  // Keep chat scrolled to the newest message.
  const chat = document.getElementById("chat-window");
  if (chat) chat.scrollTop = chat.scrollHeight;
})();
