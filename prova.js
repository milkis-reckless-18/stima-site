/* Prova pages (index, hiring-teams, higher-ed).
   "Talk to us" posts to /api/leads through leads.js: the Stima app keeps the message in the admin
   leads dashboard and emails it to info@mystima.io, so the visitor's mail app never opens.
   Plan buttons with data-plan scroll to the form and start the message for the visitor. */
(function(){
  "use strict";
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
