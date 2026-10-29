// Motorpuls prototyp: kategorifilter + nyhetsbrevsruta. Ingen data skickas.
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
