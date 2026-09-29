/* Lead capture for mystima.io.
   The forms (early access, the position paper, "Talk to us" on the Prova pages) post JSON to STIMA_LEADS_ENDPOINT. Since 7 September 2026 the
   Stima app runs on this host (nginx proxies /api and the app prefixes to it),
   so /api/leads is the app's endpoint and leads appear in mystima.io/admin.
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
  function send(body){
    body.utm = window.stimaUtm();
    body.page = location.pathname + location.search;
    body.referrer = document.referrer || undefined;
    return fetch(window.STIMA_LEADS_ENDPOINT, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
      .then(function(r){ return r.json().catch(function(){ return {}; }).then(function(j){ if (!r.ok) throw new Error(j.error || "Could not save your email. Try again."); return j; }); })
      .then(function(j){ try { gtag("event", "generate_lead", { method: body.source, role: body.role || "", campaign: (window.stimaUtm().utm_campaign || "") }); } catch (e) {} return j; });
  }
  window.stimaSendLead = function(email, role, source, website){
    return send({ email: email, role: role || undefined, source: source, ticks: window.stimaTicks(), website: website || undefined });
  };
  /* "Talk to us" on the Prova pages: the app saves the message and emails it to info@mystima.io. */
  window.stimaSendContact = function(f){
    return send({ email: f.email, name: f.name || undefined, message: f.message, role: f.role || undefined, source: "contact", website: f.website || undefined });
  };
})();
