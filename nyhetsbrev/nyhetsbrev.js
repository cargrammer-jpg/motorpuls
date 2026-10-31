// Motorpuls nyhetsbrevsruta i sidfoten (förhandsvisning, NEWSLETTER_BOX i build.py). Laddas bara när flaggan är på.
// Rutan finns redan i HTML (inget layoutskift). Anmälan: fetch POST till Supabase REST (tabellen newsletter_subscribers,
// anon får bara INSERT med consent = true, RLS) med projektets publika nyckel. Tom konfiguration: inget skickas.
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
    p.textContent = 'Tack! Du är anmäld. Vi hör av oss när första utskicket går.';
    form.replaceWith(p); p.focus();
  };
  const valid = v => v.length >= 6 && v.length <= 254 && /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v);
  input.addEventListener('input', () => { if (input.hasAttribute('aria-invalid')) { input.removeAttribute('aria-invalid'); say(''); } });
  form.addEventListener('submit', async e => {
    e.preventDefault();
    if (form.elements.webbplats.value) return done();  // honungsfälla: botar får ett tack men inget sparas
    const email = input.value.trim().toLowerCase();
    if (!valid(email)) { input.setAttribute('aria-invalid', 'true'); say('Skriv en giltig e-postadress, till exempel namn@exempel.se.', true); input.focus(); return; }
    if (!cfg.url || !cfg.key || !window.fetch) { say('Förhandsvisning: anmälan är inte inkopplad än.', true); return; }
    btn.disabled = true; btn.textContent = 'Skickar...'; say('');
    try {
      const r = await fetch(cfg.url, {
        method: 'POST',
        headers: { apikey: cfg.key, 'Content-Type': 'application/json', Prefer: 'return=minimal' },
        body: JSON.stringify({ email, consent: true, source: location.pathname })
      });
      // 409: adressen finns redan. Visas som lyckad anmälan så att ingen kan se vilka adresser som är anmälda.
      if (r.ok || r.status === 409) return done();
      say(r.status === 400 ? 'Adressen kunde inte sparas. Kontrollera att den är rätt skriven.' : 'Något gick fel. Försök igen om en stund.', true);
    } catch {
      say('Ingen kontakt med servern. Kontrollera uppkopplingen och försök igen.', true);
    }
    btn.disabled = false; btn.textContent = label;
  });
})();
