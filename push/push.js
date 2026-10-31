// Motorpuls push-ruta (förhandsvisning, PUSH_BOX i build.py). Laddas bara när flaggan är på.
// Webbläsarens fråga om notiser visas aldrig vid sidladdning, bara efter "Ja tack". "Inte nu" gäller i 30 dagar.
// Förhandsvisning: ?push=visa visar rutan direkt, ?push=ios visar iPhone-tipset.
(() => {
  const box = document.getElementById('push');
  if (!box) return;
  const KEY = 'mp-push-inte-nu', DAYS = 30;
  const preview = new URLSearchParams(location.search).get('push');
  const cfg = JSON.parse(box.dataset.config || '{}');
  // iOS Safari utanför hemskärmen: navigator.standalone finns bara där och är false. Web Push kräver hemskärmsappen.
  const ios = preview === 'ios' || ('standalone' in navigator && navigator.standalone === false);
  const supported = 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window;
  const snoozed = () => { try { return Date.now() < Number(localStorage.getItem(KEY) || 0); } catch { return false; } };
  if (!preview && (snoozed() || (!ios && (!supported || Notification.permission !== 'default')))) return;
  if (ios) box.classList.add('is-ios');

  const status = box.querySelector('.pushb__status');
  const yes = box.querySelector('[data-push="ja"]');
  const toast = box.classList.contains('pushb--toast');
  let prev = null; // fokus före rutan, återställs när den stängs
  box.addEventListener('focusin', (e) => { if (e.relatedTarget && !box.contains(e.relatedTarget)) prev = e.relatedTarget; });

  const close = () => {
    const had = box.contains(document.activeElement);
    box.hidden = true;
    if (had) (prev && prev.isConnected ? prev : document.querySelector('.more .btn') || document.querySelector('.wordmark'))?.focus();
  };
  const say = (t) => { status.textContent = t; };

  box.querySelector('[data-push="nej"]').addEventListener('click', () => {
    try { localStorage.setItem(KEY, String(Date.now() + DAYS * 864e5)); } catch {}
    close();
  });
  box.addEventListener('keydown', (e) => { if (e.key === 'Escape' && toast) close(); });

  const key = (b64) => {
    const s = atob((b64 + '='.repeat((4 - b64.length % 4) % 4)).replace(/-/g, '+').replace(/_/g, '/'));
    return Uint8Array.from(s, (c) => c.charCodeAt(0));
  };

  yes.addEventListener('click', async () => {
    if (!supported) { say('Din webbläsare kan inte ta emot notiser.'); return; }
    yes.disabled = true;
    let perm = 'default';
    try { perm = await Notification.requestPermission(); } catch {}
    if (perm !== 'granted') {
      yes.disabled = false;
      say(perm === 'denied' ? 'Notiser är avstängda. Du kan slå på dem i webbläsarens inställningar.' : 'Inga notiser nu. Du kan ändra dig när du vill.');
      return;
    }
    try {
      const reg = await navigator.serviceWorker.register('/sw.js');
      if (!cfg.vapidPublicKey || !cfg.subscribeUrl) { say('Tack! Utskicken är inte igång än, så inga notiser skickas ännu.'); return; }
      await navigator.serviceWorker.ready;
      const sub = (await reg.pushManager.getSubscription()) ||
        await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: key(cfg.vapidPublicKey) });
      const j = sub.toJSON();
      const r = await fetch(cfg.subscribeUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', apikey: cfg.anonKey, Authorization: `Bearer ${cfg.anonKey}`, Prefer: 'return=minimal' },
        body: JSON.stringify({ endpoint: j.endpoint, p256dh: j.keys.p256dh, auth: j.keys.auth, source: location.pathname })
      });
      if (!r.ok && r.status !== 409) throw new Error(String(r.status)); // 409: redan sparad
      say('Klart! Du får en notis när vi publicerar nyheter.');
      yes.hidden = true;
    } catch {
      yes.disabled = false;
      say('Det gick inte att slå på notiser just nu. Försök igen senare.');
    }
  });

  const show = () => { box.hidden = false; };
  if (preview) { show(); return; }
  if (!toast) {
    // Artikel: visa bara om platsen ligger under skärmkanten, så att inget i bild flyttar sig (ingen CLS).
    const anchor = box.previousElementSibling;
    if (anchor && anchor.getBoundingClientRect().bottom > innerHeight) show();
    return;
  }
  // Startsida: fast ruta när läsaren har skrollat ned till "Alla artiklar" (eller halva sidan om den saknas).
  const target = document.getElementById('flodet') || document.querySelector('.pop');
  if (!target || !('IntersectionObserver' in window)) return;
  const io = new IntersectionObserver((es) => { if (es.some((e) => e.isIntersecting)) { io.disconnect(); show(); } });
  io.observe(target);
})();
