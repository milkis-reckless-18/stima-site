# Stima

**Know your worth. Prove it.**

Career navigation, upskilling, and post-AI skills assessment.

This repo contains the pre-launch site for [Stima](https://mystima.io): the landing page, the position paper page, and the lead magnet PDF.

## Contents

- `index.html`: landing page with audience tabs, checkable "what resonates" bullets, team section, and email capture
- `paper.html`: position paper page with its own email capture
- `stima-prova-assessment-after-ai.pdf`: the lead magnet, "Assessment After AI" (Position Paper No. 01)
- `team-*.jpg` / `team-*.png`: team photos and illustrations

Everything is hand-written HTML, CSS, and JS in single files. No build step.

## Run locally

```bash
python3 -m http.server 8000
```

Then open http://localhost:8000

## Deploy

Static files only. Drag the folder into Netlify, run `vercel deploy`, or enable GitHub Pages on this repo.

## Before launch

- Wire the email capture forms (signup section, pop-up, paper page) to a provider such as Mailchimp, ConvertKit, Buttondown, or Formspree. They are currently front-end only.
- Visitor selections from the "Who it is for" section are stored in the browser under the `stima-resonates` localStorage key as JSON, ready to be submitted with the signup once a provider is connected.
- Update the canonical URLs and OG tags if the final domain differs from mystima.io.

## Products

- **Stima Semita**: career navigation. Chart the route.
- **Stima Ponte**: upskilling pathways. Bridge the gap.
- **Stima Prova**: post-AI assessment. Show the work.

© 2026 Stima · mystima.io
