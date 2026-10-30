// Motorpuls: kategorifilter, nyhetsbrevsruta och bildspel. Ingen data skickas.
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

  // Newsletter: show once after ~55% scroll, non-modal, no focus stealing
  const nl = document.getElementById('nyhetsbrev');
  if (!nl || !('showPopover' in HTMLElement.prototype)) return;
  const KEY = 'mp-nl-seen';
  const force = new URLSearchParams(location.search).has('nyhetsbrev'); // for previews
  const seen = () => { try { return localStorage.getItem(KEY); } catch { return null; } };
  const remember = () => { try { localStorage.setItem(KEY, '1'); } catch {} };
  const open = () => { if (!nl.matches(':popover-open')) { nl.showPopover(); remember(); } };
  const close = () => nl.hidePopover();
  nl.querySelector('.nl__close').addEventListener('click', close);
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && nl.matches(':popover-open')) close(); });
  nl.querySelector('form').addEventListener('submit', e => {
    e.preventDefault();
    nl.querySelector('.nl__status').textContent = 'Tack! (Exempel: inget har skickats ännu.)';
  });
  if (force) return open();
  if (seen()) return;
  const onScroll = () => {
    const max = document.documentElement.scrollHeight - innerHeight;
    if (max > 0 && scrollY / max > 0.55) { removeEventListener('scroll', onScroll); open(); }
  };
  addEventListener('scroll', onScroll, { passive: true });
})();

// Sidhuvud i tre lägen: hel bar högst upp, smal bar (loggan mindre och ute till vänster) när man skrollat förbi
// toppen, och helt undanglidd när man skrollar nedåt längre ned och läser. Skroll uppåt tar tillbaka den smala baren,
// nära toppen blir den hel igen. JS sätter bara klasserna och --mh-dx; utseende och animation ligger i CSS.
(() => {
  const m = document.querySelector('.masthead');
  const w = m && m.querySelector('.wordmark');
  if (!w) return;
  document.documentElement.classList.add('mh-js');
  const ON = 40, OFF = 8;  // px: krymp efter ON, hel bar igen under OFF (hysteres)
  const HIDE = 200;        // px: under detta göms baren aldrig helt
  const STEP = 6;          // px: ignorera små ryck i skrollriktningen
  const EDGE = 12;         // px från vänsterkanten i krympt läge
  const measure = () => {
    const cls = m.className;
    m.classList.remove('is-small', 'is-hidden');
    m.style.transition = 'none'; w.style.transition = 'none';
    const left = w.getBoundingClientRect().left;
    m.style.setProperty('--mh-dx', Math.min(0, EDGE - left) + 'px');
    m.className = cls;
    void w.offsetWidth;
    m.style.transition = ''; w.style.transition = '';
  };
  let last = Math.max(0, scrollY), ticking = false;
  const update = () => {
    ticking = false;
    const y = Math.max(0, scrollY), d = y - last;
    if (y <= OFF) { m.classList.remove('is-small', 'is-hidden'); last = y; return; }
    if (y > ON) m.classList.add('is-small');
    if (y <= HIDE) { m.classList.remove('is-hidden'); last = y; return; }
    if (Math.abs(d) < STEP) return;
    m.classList.toggle('is-hidden', d > 0);
    last = y;
  };
  measure(); update();
  addEventListener('scroll', () => { if (!ticking) { ticking = true; requestAnimationFrame(update); } }, { passive: true });
  addEventListener('resize', measure, { passive: true });
  m.addEventListener('focusin', () => m.classList.remove('is-hidden'));
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
