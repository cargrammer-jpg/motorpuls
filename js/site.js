// Motorpuls: kategorifilter, bildspel och nyhetsbrevsrutan. Bara nyhetsbrevet skickar data (e-post till Supabase, vid anmälan).
(() => {
  // Category filter (front page)
  const chips = document.querySelectorAll('.chip[data-filter]');
  const items = document.querySelectorAll('.item[data-cat]');
  const status = document.getElementById('filter-status');
  chips.forEach(chip => chip.addEventListener('click', () => {
    const f = chip.dataset.filter;
    chips.forEach(c => c.setAttribute('aria-pressed', String(c === chip)));
    let n = 0;
    items.forEach(it => { const show = f === 'alla' || it.dataset.cat === f; it.hidden = !show; if (show) n++; });
    document.querySelectorAll('.day').forEach(d => { d.hidden = !d.querySelector('.item:not([hidden])'); });
    if (status) status.textContent = `${n} artiklar visas` + (f === 'alla' ? '' : ` i ${chip.textContent.trim()}`);
  }));

})();

// Bildspel i artiklar (progressiv förbättring): utan JS en rad att svepa i med scroll-snap.
// Med JS: knappar, räknare, piltangenter när bildspelet har fokus. Smidig scroll bara utan prefers-reduced-motion (CSS).
(() => {
  document.querySelectorAll('[data-gallery]').forEach(g => {
    const track = g.querySelector('.gallery__track');
    const slides = [...track.children];
    const nav = g.querySelector('.gallery__nav');
    const cur = g.querySelector('[data-current]');
    const [prev, next] = nav.querySelectorAll('button');
    let i = 0, pending = null, timer = 0;
    g.classList.add('is-ready');
    nav.hidden = false;
    const render = () => {
      if (cur.textContent !== String(i + 1)) cur.textContent = String(i + 1);
      prev.disabled = i === 0;
      next.disabled = i === slides.length - 1;
    };
    const update = () => {
      const n = Math.min(slides.length - 1, Math.max(0, Math.round(track.scrollLeft / Math.max(1, track.clientWidth))));
      if (pending !== null) { if (n !== pending) return; pending = null; }
      i = n; render();
    };
    const settle = () => { pending = null; update(); };
    const go = to => {
      i = pending = Math.min(slides.length - 1, Math.max(0, to));
      render();
      track.scrollTo({ left: slides[i].offsetLeft - track.offsetLeft });
      clearTimeout(timer); timer = setTimeout(settle, 1200);  // fallback if the scroll is interrupted
    };
    nav.addEventListener('click', e => { const b = e.target.closest('button'); if (b) go(i + Number(b.dataset.dir)); });
    track.addEventListener('keydown', e => {
      const d = { ArrowLeft: -1, ArrowRight: 1 }[e.key];
      if (d) { e.preventDefault(); go(i + d); }
      else if (e.key === 'Home' || e.key === 'End') { e.preventDefault(); go(e.key === 'Home' ? 0 : slides.length); }
    });
    let raf = 0;
    track.addEventListener('scroll', () => { cancelAnimationFrame(raf); raf = requestAnimationFrame(update); }, { passive: true });
    track.addEventListener('scrollend', settle);
    addEventListener('resize', settle, { passive: true });
    update();
  });
})();

// Nyhetsbrev: orange ruta efter artikeltexten och som band på startsidan (ingen popup).
// Rutan läggs in med JS eftersom anmälan kräver JS (fetch till Supabase), så sidor utan JS visar ingen trasig form.
// Supabase REST med den publika nyckeln (publishable, får synas i klienten). Tabellen tillåter bara INSERT för anon (RLS).
(() => {
  const NL = {
    url: 'https://yhxnrcykinmuoqbgboda.supabase.co/rest/v1/newsletter_subscribers',
    key: 'sb_publishable_obvTElRjWsEDBGP_aJ4dFA_8PcVkx1c'
  };
  if (document.getElementById('nyhetsbrev') || !window.fetch) return;
  const html = `
    <section class="nlb" id="nyhetsbrev" aria-labelledby="nlb-h">
      <div class="nlb__inner">
        <div class="nlb__text">
          <p class="nlb__kicker">Nyhetsbrev</p>
          <h2 id="nlb-h">Få Motorpuls i inkorgen</h2>
          <p class="nlb__lede">Korta, sakliga bilnyheter med källor, direkt till din e-post.</p>
        </div>
        <form class="nlb__form" novalidate>
          <label class="visually-hidden" for="nlb-email">E-postadress</label>
          <div class="nlb__row">
            <input id="nlb-email" type="email" name="email" inputmode="email" autocomplete="email" maxlength="254" required placeholder="din@epost.se" aria-describedby="nlb-fine">
            <button class="nlb__btn" type="submit">Prenumerera</button>
          </div>
          <div class="nlb__hp" aria-hidden="true"><label>Lämna tomt <input type="text" name="webbplats" tabindex="-1" autocomplete="off"></label></div>
          <p class="nlb__fine" id="nlb-fine">Vi skickar nyheter från Motorpuls. Avsluta när du vill. <a href="/integritet/">Så hanterar vi din e-post</a>.</p>
          <p class="nlb__status" role="status" aria-live="polite"></p>
        </form>
      </div>
    </section>`;
  const tpl = document.createElement('template');
  tpl.innerHTML = html.trim();
  const box = tpl.content.firstElementChild;
  // Placering: artikel efter text, källor och AI-notis (före "Fler nyheter"). Startsida: efter dagen med den tredje artikeln.
  const note = document.querySelector('.article .ai-note');
  const items = document.querySelectorAll('.feed-section .item');
  if (note) note.after(box);
  else if (items.length) (items[Math.min(2, items.length - 1)].closest('.day') || items[0]).after(box);
  else if (document.querySelector('.front > .wrap')) document.querySelector('.front > .wrap').append(box);
  else return;

  const form = box.querySelector('form');
  const input = form.querySelector('#nlb-email');
  const btn = form.querySelector('button');
  const status = form.querySelector('.nlb__status');
  const say = (msg, err) => { status.textContent = msg; status.classList.toggle('is-error', !!err); };
  const done = () => {
    box.classList.add('is-done');
    form.innerHTML = '<p class="nlb__done" role="status" tabindex="-1">Tack! Du är anmäld. Vi hör av oss när första utskicket går.</p>';
    form.querySelector('.nlb__done').focus();
  };
  const valid = v => v.length >= 6 && v.length <= 254 && /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v);
  input.addEventListener('input', () => { if (input.getAttribute('aria-invalid')) { input.removeAttribute('aria-invalid'); say(''); } });
  form.addEventListener('submit', async e => {
    e.preventDefault();
    if (form.elements.webbplats.value) return done();  // honungsfälla: botar får ett "tack" men inget sparas
    const email = input.value.trim().toLowerCase();
    if (!valid(email)) { input.setAttribute('aria-invalid', 'true'); say('Skriv en giltig e-postadress, till exempel namn@exempel.se.', true); input.focus(); return; }
    btn.disabled = true; btn.textContent = 'Skickar...'; say('');
    try {
      const r = await fetch(NL.url, {
        method: 'POST',
        headers: { apikey: NL.key, 'Content-Type': 'application/json', Prefer: 'return=minimal' },
        body: JSON.stringify({ email, consent: true, source: location.pathname })
      });
      // 409 = adressen finns redan: visas som lyckad anmälan, så att ingen kan se vilka adresser som är anmälda
      if (r.ok || r.status === 409) return done();
      say(r.status === 400 ? 'Adressen kunde inte sparas. Kontrollera att den är rätt skriven.' : 'Något gick fel. Försök igen om en stund.', true);
    } catch {
      say('Ingen kontakt med servern. Kontrollera uppkopplingen och försök igen.', true);
    }
    btn.disabled = false; btn.textContent = 'Prenumerera';
  });
})();
