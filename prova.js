/* Prova pages (index, hiring-teams, higher-ed): hotspot tips and the contact form.
   "Talk to us" posts to /api/leads through leads.js: the Stima app keeps the message in the admin
   leads dashboard and emails it to info@mystima.io, so the visitor's mail app never opens.
   Plan buttons with data-plan scroll to the form and start the message for the visitor. */
(function(){
  "use strict";
  /* Hotspot tips on the pictures: centred over the dot they ran past the screen edge on phones and were cut
     by the rounded picture frames. Each tip is moved sideways into the visible part of its picture and opens
     below the dot when there is no room above (styles in tools/prova.src.css). */
  function clipBox(el){
    for (var p = el.parentElement; p && p !== document.body; p = p.parentElement) {
      var cs = getComputedStyle(p);
      if (cs.overflow === "hidden" || cs.overflowX === "hidden") return p.getBoundingClientRect();
    }
    return null;
  }
  function placeTip(h){
    var tip = h.querySelector(".tip");
    if (!tip) return;
    var clip = clipBox(h), r = h.getBoundingClientRect(), m = 8, gap = 14, th = tip.offsetHeight;
    var left = Math.max(m, (clip ? clip.left : 0) + m), right = Math.min(innerWidth - m, (clip ? clip.right : innerWidth) - m);
    var cx = r.left + r.width / 2, half = tip.offsetWidth / 2, dx = 0, dy = 0;
    if (cx - half < left) dx = left - (cx - half);
    else if (cx + half > right) dx = right - (cx + half);
    var top = clip ? clip.top + m : -Infinity, bottom = clip ? clip.bottom - m : Infinity;
    var above = r.top - gap - th, below = r.bottom + gap;
    var fitsAbove = above >= top, fitsBelow = below + th <= bottom;
    if (!fitsAbove && !fitsBelow) dy = Math.max(top - above, Math.min(0, bottom - (above + th)));
    h.style.setProperty("--tip-dx", Math.round(dx) + "px");
    h.style.setProperty("--tip-dy", Math.round(dy) + "px");
    h.classList.toggle("tip-below", !fitsAbove && fitsBelow);
    h.classList.toggle("tip-inside", !fitsAbove && !fitsBelow);
  }
  function placeTips(){ document.querySelectorAll(".hotspot").forEach(placeTip); }
  document.querySelectorAll(".hotspot").forEach(function(h){
    ["pointerenter", "touchstart", "focus"].forEach(function(ev){ h.addEventListener(ev, function(){ placeTip(h); }, { passive: true }); });
    /* The dots on the home page cards sit inside the card links: a tap opens the tip instead of leaving the page. */
    h.addEventListener("click", function(e){
      e.preventDefault();
      e.stopPropagation();
      var open = !h.classList.contains("tip-open");
      document.querySelectorAll(".hotspot.tip-open").forEach(function(o){ o.classList.remove("tip-open"); });
      if (open) { placeTip(h); h.classList.add("tip-open"); }
    });
  });
  document.addEventListener("click", function(){
    document.querySelectorAll(".hotspot.tip-open").forEach(function(o){ o.classList.remove("tip-open"); });
  });
  addEventListener("load", placeTips);
  addEventListener("resize", placeTips);
  placeTips();

  var form = document.getElementById("contactForm");
  if (!form) return;
  var status = document.getElementById("cfStatus");
  var msg = document.getElementById("cfMsg");
  var button = form.querySelector('button[type="submit"]');
  var label = button ? button.textContent : "";
  var prefilled = "";

  function show(text, ok, html){
    status.classList.remove("hidden", "text-coral", "text-aqua");
    status.classList.add(ok ? "text-aqua" : "text-coral");
    if (html) status.innerHTML = html; else status.textContent = text;
  }

  form.addEventListener("submit", function(e){
    e.preventDefault();
    var data = new FormData(form);
    var name = String(data.get("name") || "").trim();
    var email = String(data.get("email") || "").trim();
    var message = String(data.get("message") || "").trim();
    if (!name || !email || !message) { form.reportValidity(); return; }
    button.disabled = true;
    button.textContent = "Sending…";
    window.stimaSendContact({ name: name, email: email, message: message, role: document.body.dataset.section, website: String(data.get("website") || "") })
      .then(function(){
        form.querySelectorAll("input, textarea").forEach(function(el){ el.value = ""; });
        prefilled = "";
        show("Thanks, " + name.split(" ")[0] + ". Your message is with us, and we will reply to " + email + ".", true);
        button.textContent = "Sent";
      })
      .catch(function(err){
        var mail = "mailto:info@mystima.io?subject=" + encodeURIComponent("Stima Prova for " + name) + "&body=" + encodeURIComponent(message + "\n\n" + name + " (" + email + ")");
        show("", false, (err && err.message ? err.message.replace(/</g, "&lt;") + " " : "Could not send the message. ") +
          'You can also write to <a class="underline" href="' + mail + '">info@mystima.io</a>.');
        button.disabled = false;
        button.textContent = label;
      });
  });

  form.addEventListener("input", function(){
    if (button.disabled && button.textContent === "Sent") { button.disabled = false; button.textContent = label; }
  });

  document.addEventListener("click", function(e){
    var a = e.target.closest && e.target.closest("[data-plan]");
    if (!a) return;
    if (!msg.value.trim() || msg.value === prefilled) { msg.value = a.getAttribute("data-plan") + " "; prefilled = msg.value; }
    setTimeout(function(){ (document.getElementById("cfName").value ? msg : document.getElementById("cfName")).focus({ preventScroll: true }); }, 450);
  });
})();
