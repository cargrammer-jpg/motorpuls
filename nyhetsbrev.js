// Motorpuls nyhetsbrevsruta i sidfoten (NEWSLETTER_BOX i build.py). Laddas bara när flaggan är på.
// Rutan finns redan i HTML (inget layoutskift). Anmälan: fetch POST till edge-funktionen newsletter-subscribe i Supabase
// (dubbel bekräftelse: funktionen sparar en väntande rad och skickar ett bekräftelsemejl via Resend). Ingen nyckel i klienten.
(() => {
  const box = document.getElementById('nyhetsbrev-fot');
  if (!box) return;
  const cfg = JSON.parse(box.dataset.config || '{}');
  const form = box.querySelector('form');
  const input = form.querySelector('input[type="email"]');
  const btn = form.querySelector('button');
  const status = form.querySelector('.nlf__status');
  const label = btn.textContent;
  const say = (msg, err) => { status.textContent = msg; status.classList.toggle('is-error', !!err); };
  const done = () => {
    const p = document.createElement('p');
    p.className = 'nlf__done'; p.tabIndex = -1; p.setAttribute('role', 'status');
    p.textContent = 'Nästan klart! Vi har skickat ett mejl till dig. Öppna det och tryck på Bekräfta, annars kommer inga nyhetsbrev. Hittar du det inte, titta i skräpposten.';
    form.replaceWith(p); p.focus();
  };
  const valid = v => v.length >= 6 && v.length <= 254 && /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v);
  input.addEventListener('input', () => { if (input.hasAttribute('aria-invalid')) { input.removeAttribute('aria-invalid'); say(''); } });
  form.addEventListener('submit', async e => {
    e.preventDefault();
    const trap = form.elements.webbplats.value;
    if (trap) return done();  // honungsfälla: botar får ett tack men inget sparas (servern kontrollerar också)
    const email = input.value.trim().toLowerCase();
    if (!valid(email)) { input.setAttribute('aria-invalid', 'true'); say('Skriv en giltig e-postadress, till exempel namn@exempel.se.', true); input.focus(); return; }
    if (!cfg.api || !window.fetch) { say('Förhandsvisning: anmälan är inte inkopplad än.', true); return; }
    btn.disabled = true; btn.textContent = 'Skickar...'; say('');
    try {
      const r = await fetch(cfg.api + '/newsletter-subscribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, source: location.pathname, webbplats: trap })
      });
      // Samma svar oavsett om adressen redan prenumererar, så att ingen kan se vilka adresser som är anmälda.
      if (r.ok) return done();
      say(r.status === 400 ? 'Adressen kunde inte sparas. Kontrollera att den är rätt skriven.'
        : r.status === 429 ? 'För många försök. Vänta en stund och försök igen.'
        : 'Något gick fel. Försök igen om en stund.', true);
    } catch {
      say('Ingen kontakt med servern. Kontrollera uppkopplingen och försök igen.', true);
    }
    btn.disabled = false; btn.textContent = label;
  });
})();
