// Sidorna /prenumeration/bekrafta/ och /prenumeration/avsluta/ (bara med NEWSLETTER_BOX). Länken i mejlet bär koden
// (?token=). Att öppna sidan ändrar inget, så länkskannrar i mejl kan inte bekräfta eller avsluta. Först knappen
// POSTar koden till edge-funktionen newsletter-confirm eller newsletter-unsubscribe.
(() => {
  const box = document.querySelector('.nlp');
  if (!box) return;
  const form = box.querySelector('form');
  const btn = form.querySelector('button');
  const msg = box.querySelector('.nlp__msg[role="status"]');
  const kind = box.dataset.kind;
  const token = new URLSearchParams(location.search).get('token') || '';
  const say = (t, err) => { msg.textContent = t; msg.classList.toggle('is-error', !!err); msg.focus(); };
  if (!/^[0-9a-f]{64}$/.test(token)) { say('Länken saknar sin kod. Öppna länken direkt från mejlet, eller kopiera hela adressen.', true); return; }
  if (history.replaceState) history.replaceState(null, '', location.pathname);  // koden syns inte kvar i adressfältet
  form.hidden = false;
  const text = {
    bekrafta: {
      confirmed: 'Klart! Du prenumererar nu på Motorpuls nyhetsbrev.',
      already: 'Du har redan bekräftat. Nyhetsbrevet kommer till din inkorg.',
      missing: 'Länken fungerar inte längre. Den kan ha gått ut efter 30 dagar, eller så har adressen tagits bort. Anmäl dig gärna igen längst ner på sidan.'
    },
    avsluta: {
      unsubscribed: 'Klart. Din adress är raderad och du får inga fler nyhetsbrev från Motorpuls.',
      missing: 'Adressen finns inte i vår lista. Den kan redan vara borttagen.'
    }
  }[kind];
  form.addEventListener('submit', async e => {
    e.preventDefault();
    btn.disabled = true;
    try {
      const r = await fetch(box.dataset.api, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ token }) });
      const data = await r.json().catch(() => ({}));
      if (data.status && text[data.status]) { form.hidden = true; return say(text[data.status], data.status === 'missing'); }
      say('Något gick fel. Försök igen om en stund.', true);
    } catch {
      say('Ingen kontakt med servern. Kontrollera uppkopplingen och försök igen.', true);
    }
    btn.disabled = false;
  });
})();
