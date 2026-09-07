/* Lead capture for mystima.io.
   The forms post JSON to STIMA_LEADS_ENDPOINT. Until the Stima app is live at
   app.mystima.io this is the collector on the same server (/api/leads, nginx ->
   leads.py); switch the constant to "https://admin.mystima.io/api/leads" after
   the app deploy and import the interim file with `pnpm leads:import`.
   utm_* from the first page view are kept in sessionStorage so a click on
   /mit is attributed even when the visitor reaches the form on a clean URL. */
window.STIMA_LEADS_ENDPOINT = "/api/leads";
(function(){
  var KEY = "stima-utm";
  try {
    var q = new URLSearchParams(location.search), utm = {};
    ["utm_source","utm_medium","utm_campaign","utm_term","utm_content"].forEach(function(k){ if (q.get(k)) utm[k] = q.get(k); });
    if (Object.keys(utm).length) sessionStorage.setItem(KEY, JSON.stringify(utm));
  } catch (e) {}
  window.stimaUtm = function(){ try { return JSON.parse(sessionStorage.getItem(KEY)) || {}; } catch (e) { return {}; } };
  window.stimaTicks = function(){
    var out = [];
    try {
      var st = JSON.parse(localStorage.getItem("stima-resonates")) || {};
      Object.keys(st).forEach(function(rid){
        var it = st[rid]; if (!it || !it.on) return;
        if (it.custom) { out.push({ rid: rid, text: it.text, custom: true }); return; }
        var box = document.querySelector('input[data-rid="' + rid + '"]');
        var b = box && box.closest(".tick") ? box.closest(".tick").querySelector("b") : null;
        out.push({ rid: rid, text: b ? b.textContent : rid });
      });
    } catch (e) {}
    return out;
  };
  window.stimaSendLead = function(email, role, source, website){
    var body = { email: email, role: role || undefined, source: source, ticks: window.stimaTicks(), utm: window.stimaUtm(), page: location.pathname + location.search, referrer: document.referrer || undefined, website: website || undefined };
    return fetch(window.STIMA_LEADS_ENDPOINT, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
      .then(function(r){ return r.json().catch(function(){ return {}; }).then(function(j){ if (!r.ok) throw new Error(j.error || "Could not save your email. Try again."); return j; }); })
      .then(function(j){ try { gtag("event", "generate_lead", { method: source, role: role || "", campaign: (window.stimaUtm().utm_campaign || "") }); } catch (e) {} return j; });
  };
})();
