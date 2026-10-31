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
// nära toppen blir den hel igen. JS sätter bara klasserna och --mh-dx; utseende och animation (bara transform/opacity)
// ligger i CSS. Skrollhanteraren är passiv, körs högst en gång per bildruta (rAF) och läser bara scrollY: sidans höjd
// och loggans läge mäts vid load/resize, aldrig under skroll, så den tvingar aldrig fram layout. Inget läses heller
// direkt när skriptet körs (det tvingade fram sidans första layout, 110 ms i Lighthouse): första mätningen görs i
// ResizeObserver-anropet, som kommer efter att webbläsaren själv gjort layouten.
(() => {
  const m = document.querySelector('.masthead');
  const w = m && m.querySelector('.wordmark');
  if (!w) return;
  document.documentElement.classList.add('mh-js');
  const ON = 40, OFF = 8;  // px: krymp efter ON, hel bar igen under OFF (hysteres)
  const HIDE = 200;        // px: under detta göms baren aldrig helt
  const DOWN = 24, UP = 16; // px: så långt man ska ha skrollat åt samma håll innan baren göms resp. visas
  const EDGE = 12;         // px från vänsterkanten i krympt läge
  const row = w.parentElement;
  let max = 0, last = 0, acc = 0, ticking = false, small = false, hidden = false;
  // Mätningar (layoutläsningar) bara här. Loggans vänsterkant mäts på raden runt den (som aldrig transformeras).
  // iOS skickar resize när Safaris verktygsfält fälls ihop under skroll; mätningen läggs då i nästa bildruta.
  let mq = 0;
  const measure = () => {
    mq = 0;
    // alla läsningar först, sedan skrivningen (ingen läsning efter en ändring)
    max = Math.max(0, document.documentElement.scrollHeight - innerHeight);
    const left = row.getBoundingClientRect().left + parseFloat(getComputedStyle(row).paddingLeft);
    m.style.setProperty('--mh-dx', Math.min(0, EDGE - left) + 'px');
  };
  const remeasure = () => { if (!mq) mq = requestAnimationFrame(measure); };
  const set = (s, h) => {
    if (s !== small) m.classList.toggle('is-small', small = s);
    if (h !== hidden) m.classList.toggle('is-hidden', hidden = h);
  };
  const update = () => {
    ticking = false;
    // Klämd till sidans gränser: iOS gummibandseffekt ger negativ scrollY högst upp och för stor längst ned.
    const y = Math.min(max || Infinity, Math.max(0, scrollY)), d = y - last;
    last = y;
    if (y <= OFF) { acc = 0; return set(false, false); }
    if (y <= HIDE) { acc = 0; return set(small || y > ON, false); }
    acc = (d > 0) === (acc > 0) ? acc + d : d;  // sträcka åt samma håll; nollställs när riktningen vänder
    if (acc > DOWN) set(true, true);
    else if (acc < -UP) set(true, false);
    else set(true, hidden);
  };
  // Första mätningen: i ResizeObserver-anropet (layouten är redan gjord) och direkt därefter läget för en sida som
  // öppnas nedskrollad. Utan ResizeObserver: i nästa bildruta.
  let first = true;
  const init = () => { if (first) { first = false; last = Math.max(0, scrollY); measure(); update(); } else remeasure(); };
  addEventListener('scroll', () => { if (!ticking) { ticking = true; requestAnimationFrame(update); } }, { passive: true });
  addEventListener('resize', remeasure, { passive: true });
  addEventListener('load', remeasure);
  if ('ResizeObserver' in window) new ResizeObserver(init).observe(document.body);
  else requestAnimationFrame(init);
  m.addEventListener('focusin', () => set(small, false));
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
    render();  // bildspelet börjar på första bilden; att läsa scrollLeft här direkt efter is-ready tvingade fram layout
  });
})();

// Dela (artiklar): länkarna till X, Facebook, LinkedIn och WhatsApp fungerar utan JS. Här: "Kopiera länk" med en kort
// bekräftelse, och "Dela" (systemets delningsmeny via Web Share API) där webbläsaren har den. Ingen data skickas.
(() => {
  document.querySelectorAll('[data-share]').forEach(box => {
    const { url, title } = box.dataset;
    const status = box.querySelector('.share__status');
    box.classList.add('is-ready');
    if (navigator.share && (!navigator.canShare || navigator.canShare({ title, url }))) {
      box.classList.add('has-native');
      box.querySelector('[data-share-native]').addEventListener('click', () => navigator.share({ title, url }).catch(() => {}));
    }
    let timer = 0;
    const say = msg => { status.textContent = msg; clearTimeout(timer); timer = setTimeout(() => { status.textContent = ''; }, 2500); };
    box.querySelector('[data-share-copy]').addEventListener('click', async () => {
      try { await navigator.clipboard.writeText(url); say('Länken är kopierad'); }
      catch { say('Kunde inte kopiera, använd adressfältet'); }
    });
  });
})();
