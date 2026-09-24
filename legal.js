/* Legal documents popup. Any link with data-legal="terms-of-use|privacy|participant-terms"
   opens that document in a modal, loaded from /terms/. Without JS the link opens the full page. */
(function(){
  "use strict";
  var SRC = "/terms/";
  var pop = null, body, tabsEl, metaEl, fullLink, lastFocus = null;
  var docs = null, loading = null, current = null;

  function build(){
    pop = document.createElement("div");
    pop.className = "lgp";
    pop.hidden = true;
    pop.setAttribute("role", "dialog");
    pop.setAttribute("aria-modal", "true");
    pop.setAttribute("aria-labelledby", "lgpTitle");
    pop.innerHTML =
      '<div class="lgp-backdrop" data-lgp-close></div>' +
      '<div class="lgp-card">' +
        '<div class="lgp-head">' +
          '<div class="lgp-top">' +
            '<div><div class="lg-kicker">Legal</div><h2 class="lgp-title" id="lgpTitle">The fine print, <em>in plain sight.</em></h2></div>' +
            '<button type="button" class="lgp-x" data-lgp-close aria-label="Close">×</button>' +
          '</div>' +
          '<div class="lg-tabs" role="tablist" aria-label="Legal documents"></div>' +
        '</div>' +
        '<div class="lgp-body" tabindex="-1" data-lenis-prevent><div class="lgp-loading">Opening the document…</div></div>' +
        '<div class="lgp-foot"><span class="lgp-meta"></span><a class="lgp-full" href="' + SRC + '">Open as a full page ↗</a></div>' +
      '</div>';
    document.body.appendChild(pop);
    body = pop.querySelector(".lgp-body");
    tabsEl = pop.querySelector(".lg-tabs");
    metaEl = pop.querySelector(".lgp-meta");
    fullLink = pop.querySelector(".lgp-full");
    pop.querySelectorAll("[data-lgp-close]").forEach(function(el){ el.addEventListener("click", close); });
    pop.addEventListener("keydown", trapTab);
    /* in-document links (table of contents, cross references) scroll the popup, not the page */
    body.addEventListener("click", function(e){
      var a = e.target.closest && e.target.closest('a[href^="#"]');
      if(!a) return;
      var id = a.getAttribute("href").slice(1);
      e.preventDefault();
      if(docs && docs[id]){ show(id); return; }
      var t = body.querySelector('[id="' + id.replace(/"/g, "") + '"]');
      if(!t) return;
      if(a.closest(".lg-toc")){
        pinned = Date.now() + 900;
        body.querySelectorAll(".lg-toc a").forEach(function(x){ x.classList.toggle("on", x === a); });
      }
      body.scrollTo({ top: body.scrollTop + t.getBoundingClientRect().top - body.getBoundingClientRect().top - 12, behavior: "smooth" });
    });
    body.addEventListener("scroll", spy, { passive: true });
  }

  function load(){
    if(docs) return Promise.resolve(docs);
    if(loading) return loading;
    loading = fetch(SRC, { credentials: "same-origin" }).then(function(r){
      if(!r.ok) throw new Error("status " + r.status);
      return r.text();
    }).then(function(text){
      var dom = new DOMParser().parseFromString(text, "text/html");
      docs = {};
      var order = [];
      dom.querySelectorAll("article.lg-doc").forEach(function(art){
        docs[art.id] = art;
        order.push(art.id);
      });
      tabsEl.innerHTML = "";
      order.forEach(function(key){
        var src = dom.querySelector('.lg-tab[data-doc="' + key + '"]');
        var b = document.createElement("button");
        b.type = "button";
        b.className = "lg-tab";
        b.setAttribute("role", "tab");
        b.dataset.doc = key;
        b.innerHTML = src ? src.innerHTML : docs[key].dataset.title;
        b.addEventListener("click", function(){ show(key); });
        tabsEl.appendChild(b);
      });
      return docs;
    }).catch(function(err){
      loading = null;
      throw err;
    });
    return loading;
  }

  function show(key){
    var art = docs[key] || docs[Object.keys(docs)[0]];
    current = art.id;
    var toc = art.querySelector(".lg-toc");
    var doc = art.querySelector(".lg-body");
    body.innerHTML = "";
    if(toc) body.appendChild(document.importNode(toc, true));
    body.appendChild(document.importNode(doc, true));
    body.scrollTop = 0;
    metaEl.textContent = art.dataset.meta || "";
    fullLink.href = SRC + "#" + art.id;
    tabsEl.querySelectorAll(".lg-tab").forEach(function(t){
      t.setAttribute("aria-selected", String(t.dataset.doc === art.id));
    });
  }

  var pinned = 0;
  function spy(){
    if(Date.now() < pinned) return;
    if(body.scrollTop + body.clientHeight >= body.scrollHeight - 2) return;
    var heads = body.querySelectorAll(".lg-text h2[id]");
    var line = body.getBoundingClientRect().top + body.clientHeight * 0.25;
    var on = null;
    heads.forEach(function(h){ if(h.getBoundingClientRect().top <= line) on = h.id; });
    body.querySelectorAll(".lg-toc a").forEach(function(a){
      a.classList.toggle("on", a.getAttribute("href") === "#" + on);
    });
  }

  function open(key){
    if(!pop) build();
    lastFocus = document.activeElement;
    pop.hidden = false;
    document.documentElement.classList.add("lgp-lock");
    if(window.stimaLenis && window.stimaLenis.stop) window.stimaLenis.stop();
    requestAnimationFrame(function(){ requestAnimationFrame(function(){ pop.classList.add("open"); }); });
    pop.querySelector(".lgp-x").focus();
    return load().then(function(){ show(key); }).catch(function(){
      window.location.href = SRC + "#" + (key || "");
    });
  }

  function close(){
    if(!pop || pop.hidden) return;
    pop.classList.remove("open");
    document.documentElement.classList.remove("lgp-lock");
    if(window.stimaLenis && window.stimaLenis.start) window.stimaLenis.start();
    setTimeout(function(){ pop.hidden = true; }, 450);
    if(lastFocus && lastFocus.focus) lastFocus.focus();
  }

  function trapTab(e){
    if(e.key !== "Tab") return;
    var f = [].filter.call(pop.querySelectorAll('button, a[href], [tabindex="-1"].lgp-body'), function(el){ return el.offsetParent !== null; });
    if(!f.length) return;
    var first = f[0], last = f[f.length - 1];
    if(e.shiftKey && document.activeElement === first){ e.preventDefault(); last.focus(); }
    else if(!e.shiftKey && document.activeElement === last){ e.preventDefault(); first.focus(); }
  }

  document.addEventListener("keydown", function(e){
    if(e.key === "Escape" && pop && !pop.hidden) close();
  });
  document.addEventListener("click", function(e){
    var a = e.target.closest && e.target.closest("[data-legal]");
    if(!a || e.metaKey || e.ctrlKey || e.shiftKey || e.button > 0) return;
    e.preventDefault();
    open(a.getAttribute("data-legal"));
  });

  window.stimaLegal = { open: open, close: close };
})();
