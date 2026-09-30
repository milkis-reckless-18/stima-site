/* Prova pages (index, hiring-teams, higher-ed): hotspot tips, card headings that fit their column, and the contact form.
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

  /* Card headings (the user, 30 September 2026): in the narrow columns of tablets and phones they broke a word per
     line ("AI / collaboration / level", "Mixed / rules,"). Each heading gets the largest size, at most a third below
     its design size (0.62 of it at most), at which no word is split, a phrase of one or two words stays on one line, three to six words
     take at most two lines and longer ones at most three; a line she broke with <br> stays whole up to three words. Headings of the same kind in one grid share the smallest
     of their sizes, so neighbouring cards match. Lines Marianna broke with <br> (span.block) count separately. */
  var CARD_HEADINGS = ".lift h3.font-serif, .lift p.font-serif";
  function segments(h){ var b = h.querySelectorAll(":scope > span.block"); return b.length ? [].slice.call(b) : [h]; }
  function layout(seg){
    var lines = {}, split = false, words = 0;
    var tw = document.createTreeWalker(seg, NodeFilter.SHOW_TEXT), n;
    while ((n = tw.nextNode())) {
      var re = /\S+/g, m;
      while ((m = re.exec(n.data))) {
        words++;
        var r = document.createRange(); r.setStart(n, m.index); r.setEnd(n, m.index + m[0].length);
        var rs = r.getClientRects(), tops = {};
        for (var i = 0; i < rs.length; i++) if (rs[i].width > 0.5) tops[Math.round(rs[i].bottom)] = 1;
        var keys = Object.keys(tops);
        if (keys.length > 1) split = true;
        keys.forEach(function(k){ lines[k] = 1; });
      }
    }
    return { lines: Object.keys(lines).length, words: words, split: split };
  }
  function fits(h, relaxed){
    var segs = segments(h), own = segs.length > 1 && !relaxed;
    return segs.every(function(seg){
      var l = layout(seg);
      // a line Marianna wrote herself ("Mixed rules," / "no measured skill") stays whole up to three words
      var max = l.words <= (own ? 3 : 2) ? 1 : l.words <= 6 ? 2 : 3;
      return !l.split && l.lines <= max;
    });
  }
  function bestSize(h){
    h.style.fontSize = ""; h.style.lineHeight = "";
    var cs = getComputedStyle(h), design = parseFloat(cs.fontSize), lh = parseFloat(cs.lineHeight);
    h.dataset.fitDesign = design; h.dataset.fitLh = isNaN(lh) ? "" : lh / design;
    // when her own line cannot stay whole even a third smaller (320 px phones), the usual rule applies at a larger size
    for (var pass = 0; pass < 2; pass++) {
      for (var fs = design; fs >= design * 0.62; fs -= 0.5) {
        apply(h, fs);
        if (fits(h, pass === 1)) return fs;
      }
    }
    return Math.ceil(design * 0.62 * 2) / 2;
  }
  function apply(h, fs){
    var design = parseFloat(h.dataset.fitDesign), ratio = parseFloat(h.dataset.fitLh);
    h.style.fontSize = fs < design ? fs + "px" : "";
    h.style.lineHeight = fs < design && ratio ? (ratio * fs).toFixed(2) + "px" : "";
  }
  var fitWidth = 0;
  function fitCards(force){
    if (!force && innerWidth === fitWidth) return;
    fitWidth = innerWidth;
    var groups = new Map();
    document.querySelectorAll(CARD_HEADINGS).forEach(function(h){
      var card = h.closest(".lift"), key = (card.parentElement ? card.parentElement : card);
      var k2 = h.tagName + "|" + h.className;
      if (!groups.has(key)) groups.set(key, {});
      (groups.get(key)[k2] = groups.get(key)[k2] || []).push(h);
    });
    groups.forEach(function(kinds){
      Object.keys(kinds).forEach(function(k){
        var hs = kinds[k], size = Infinity;
        hs.forEach(function(h){ size = Math.min(size, bestSize(h)); });
        hs.forEach(function(h){ apply(h, size); });
      });
    });
  }
  var fitQueued = false;
  addEventListener("resize", function(){ if (fitQueued) return; fitQueued = true; requestAnimationFrame(function(){ fitQueued = false; fitCards(false); }); });
  fitCards(true);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(function(){ fitCards(true); });
  addEventListener("load", function(){ fitCards(true); });

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
