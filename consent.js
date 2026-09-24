/* Cookie consent. Google Analytics loads only after the visitor accepts it; the choice is
   kept in localStorage ("stima-consent") and can be changed through any [data-cookie-settings] link. */
(function(){
  "use strict";
  var GA_ID = "G-CBQTM9PBQE";
  var KEY = "stima-consent";
  var loaded = false, banner = null;

  /* gtag() is always defined so page code can send events; nothing leaves the browser until GA loads */
  window.dataLayer = window.dataLayer || [];
  window.gtag = window.gtag || function(){ window.dataLayer.push(arguments); };

  function read(){ try { return localStorage.getItem(KEY); } catch(e){ return null; } }
  function write(v){ try { localStorage.setItem(KEY, v); } catch(e){} }

  function loadGA(){
    window["ga-disable-" + GA_ID] = false;
    if(loaded) return;
    loaded = true;
    gtag("js", new Date());
    gtag("config", GA_ID);
    var s = document.createElement("script");
    s.async = true;
    s.src = "https://www.googletagmanager.com/gtag/js?id=" + GA_ID;
    document.head.appendChild(s);
  }

  function stopGA(){
    window["ga-disable-" + GA_ID] = true;
    var host = location.hostname.split(".");
    var domains = ["", host.slice(-2).join("."), "." + host.slice(-2).join(".")];
    document.cookie.split(";").forEach(function(c){
      var name = c.split("=")[0].trim();
      if(name !== "_ga" && name.indexOf("_ga_") !== 0) return;
      domains.forEach(function(d){
        document.cookie = name + "=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/" + (d ? "; domain=" + d : "");
      });
    });
  }

  function choose(v){
    write(v);
    if(v === "granted") loadGA(); else stopGA();
    hide();
  }

  function build(){
    banner = document.createElement("div");
    banner.className = "ck";
    banner.hidden = true;
    banner.setAttribute("role", "dialog");
    banner.setAttribute("aria-label", "Cookie choice");
    banner.innerHTML =
      '<div class="lg-kicker">Cookies</div>' +
      '<p class="ck-text">May we use Google Analytics to see how people find Stima? It sets cookies only if you accept. No assessment data is involved. ' +
      '<a href="/terms/#privacy" data-legal="privacy">Privacy Policy</a></p>' +
      '<div class="ck-actions">' +
        '<button type="button" class="ck-btn ck-yes">Accept analytics</button>' +
        '<button type="button" class="ck-btn">Decline</button>' +
      '</div>';
    document.body.appendChild(banner);
    banner.querySelector(".ck-yes").addEventListener("click", function(){ choose("granted"); });
    banner.querySelector(".ck-btn:not(.ck-yes)").addEventListener("click", function(){ choose("denied"); });
  }

  function show(){
    if(!banner) build();
    banner.hidden = false;
    requestAnimationFrame(function(){ requestAnimationFrame(function(){ banner.classList.add("open"); }); });
  }

  function hide(){
    if(!banner) return;
    banner.classList.remove("open");
    setTimeout(function(){ banner.hidden = true; }, 400);
  }

  document.addEventListener("click", function(e){
    var a = e.target.closest && e.target.closest("[data-cookie-settings]");
    if(!a) return;
    e.preventDefault();
    show();
  });

  function init(){
    var v = read();
    if(v === "granted") loadGA();
    else if(v !== "denied") show();
  }
  if(document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();

  window.stimaConsent = { show: show };
})();
