// Laddkostnad: räknar i webbläsaren. Inga anrop, inget sparas.
// 1 mil = 10 km. Förbrukning kWh/100 km delat med 10 ger kWh per mil ur batteriet.
// Laddförlust hemma är extra el från väggen: vägg = batteri × (1 + förlust/100).
// Snabbladdning räknas utan det påslaget. Månad och år avrundas till hela kronor
// från det oavrundade milpriset. Kronor per mil visas i ören.
(function (root, factory) {
  var api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.MotorpulsLadd = api;
  if (root.document && root.document.getElementById("laddkostnad")) api.bind(root.document);
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  var DEFAULTS = {
    kwhPer100: 18,
    distance: 100,
    period: "manad",
    homeShare: 80,
    homePrice: 2.34,
    fastPrice: 6,
    lossPct: 10,
    petrolL: 0.7,
    petrolPrice: 18
  };

  function parseSv(raw) {
    if (raw == null) return null;
    var t = String(raw).replace(/[\s\u00a0\u202f]/g, "").replace(",", ".");
    if (t === "") return null;
    if (!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$/.test(t)) return NaN;
    var n = Number(t);
    return Number.isFinite(n) ? n : NaN;
  }

  function formatNumber(n, decimals) {
    var neg = n < 0;
    var s = Math.abs(n).toFixed(decimals);
    var bits = s.split(".");
    var grouped = bits[0].replace(/\B(?=(\d{3})+(?!\d))/g, "\u00a0");
    return (neg ? "\u2212" : "") + grouped + (decimals ? "," + bits[1] : "");
  }

  function formatKr(n, decimals) {
    return formatNumber(n, decimals) + "\u00a0kr";
  }

  function formatShare(n) {
    var r = Math.round(n * 100) / 100;
    return formatNumber(r, 2).replace(/,00$/, "").replace(/,(\d)0$/, ",$1");
  }

  function num(v) {
    return typeof v === "number" && Number.isFinite(v);
  }

  function compute(input) {
    var kwh = input.kwhPer100;
    var dist = input.distance;
    var share = input.homeShare;
    var homePrice = input.homePrice;
    var fastPrice = input.fastPrice;
    var loss = input.lossPct;
    if (!num(kwh) || kwh <= 0 || kwh > 200) return { ok: false, field: "forbrukning", message: "Skriv förbrukningen som ett tal över 0 och högst 200, till exempel 18." };
    if (!num(dist) || dist < 0 || dist > 100000) return { ok: false, field: "stracka", message: "Skriv körsträckan i mil, 0 eller mer." };
    if (!num(share) || share < 0 || share > 100) return { ok: false, field: "hemma", message: "Andelen hemmaladdning ska vara mellan 0 och 100." };
    if (!num(homePrice) || homePrice < 0 || homePrice > 100) return { ok: false, field: "elpris", message: "Skriv elpriset hemma i kronor per kWh, 0 eller mer." };
    if (!num(fastPrice) || fastPrice < 0 || fastPrice > 100) return { ok: false, field: "snabb", message: "Skriv snabbladdningspriset i kronor per kWh, 0 eller mer." };
    if (!num(loss) || loss < 0 || loss > 100) return { ok: false, field: "forlust", message: "Laddförlusten ska vara mellan 0 och 100 procent." };

    var petrolL = input.petrolL;
    var petrolPrice = input.petrolPrice;
    var petrolEmpty = petrolL == null && petrolPrice == null;
    var petrolPartial = (petrolL == null) !== (petrolPrice == null);
    var petrolBad = !petrolEmpty && (petrolPartial || !num(petrolL) || !num(petrolPrice) || petrolL < 0 || petrolPrice < 0 || petrolL > 20 || petrolPrice > 200);
    if (petrolBad) return { ok: false, field: petrolL == null || !num(petrolL) ? "bensinl" : "bensinpris", message: "Bensinfälten ska vara tal, 0 eller mer, eller lämnas båda tomma." };

    var kwhBatt = kwh / 10;
    var kwhHome = kwhBatt * (1 + loss / 100);
    var krHome = kwhHome * homePrice;
    var krFast = kwhBatt * fastPrice;
    var homeFrac = share / 100;
    var fastFrac = 1 - homeFrac;
    var krMil = homeFrac * krHome + fastFrac * krFast;
    var milYear = input.period === "ar" ? dist : dist * 12;
    var milMonth = milYear / 12;
    var year = Math.round(krMil * milYear);
    var month = Math.round(krMil * milMonth);
    var yearHome = Math.round(homeFrac * krHome * milYear);
    var yearFast = Math.round(fastFrac * krFast * milYear);
    yearFast += year - (yearHome + yearFast);
    var monthHome = Math.round(homeFrac * krHome * milMonth);
    var monthFast = Math.round(fastFrac * krFast * milMonth);
    monthFast += month - (monthHome + monthFast);

    var petrol = null;
    if (!petrolEmpty) {
      var krPetrol = petrolL * petrolPrice;
      var petrolYear = Math.round(krPetrol * milYear);
      var petrolMonth = Math.round(krPetrol * milMonth);
      var diff = petrolYear - year;
      var diffText = diff > 0
        ? "Elbilen kostar " + formatKr(diff, 0) + " mindre per år i drivmedel."
        : diff < 0
          ? "Elbilen kostar " + formatKr(-diff, 0) + " mer per år i drivmedel."
          : "Samma drivmedelskostnad per år i den här jämförelsen.";
      petrol = {
        perMil: formatKr(Math.round(krPetrol * 100) / 100, 2),
        perManad: formatKr(petrolMonth, 0),
        perAr: formatKr(petrolYear, 0),
        diffText: diffText
      };
    }

    return {
      ok: true,
      kwhBatt: formatNumber(kwhBatt, 2),
      kwhHome: formatNumber(kwhHome, 2),
      perMil: formatKr(Math.round(krMil * 100) / 100, 2),
      perManad: formatKr(month, 0),
      perAr: formatKr(year, 0),
      homeShare: formatShare(share),
      fastShare: formatShare(100 - share),
      hemmaMil: formatKr(Math.round(krHome * 100) / 100, 2),
      hemmaManad: formatKr(monthHome, 0),
      hemmaAr: formatKr(yearHome, 0),
      snabbMil: formatKr(Math.round(krFast * 100) / 100, 2),
      snabbManad: formatKr(monthFast, 0),
      snabbAr: formatKr(yearFast, 0),
      milYear: formatNumber(milYear, milYear % 1 ? 1 : 0),
      petrol: petrol
    };
  }

  function fieldOf(form, name) {
    return form.elements[name];
  }

  function clearInvalid(form) {
    Array.prototype.forEach.call(form.elements, function (el) {
      if (!el.removeAttribute) return;
      el.removeAttribute("aria-invalid");
      if (el.dataset.described) el.setAttribute("aria-describedby", el.dataset.described);
    });
  }

  function fill(doc, result) {
    var text = {
      "out-kwh": result.kwhBatt + " kWh per mil ur batteriet, " + result.kwhHome + " kWh från väggen hemma.",
      "out-mil": result.perMil,
      "out-manad": result.perManad,
      "out-ar": result.perAr,
      "out-hemma-rubrik": "Hemma, " + result.homeShare + " procent",
      "out-hemma-mil": result.hemmaMil + " per mil vid hemmaladdning",
      "out-hemma-tid": result.hemmaManad + " per månad, " + result.hemmaAr + " per år för den andelen",
      "out-snabb-rubrik": "Snabbladdning, " + result.fastShare + " procent",
      "out-snabb-mil": result.snabbMil + " per mil vid snabbladdning",
      "out-snabb-tid": result.snabbManad + " per månad, " + result.snabbAr + " per år för den andelen",
      "ladd-rest": result.fastShare + " procent räknas som snabbladdning."
    };
    Object.keys(text).forEach(function (id) {
      var node = doc.getElementById(id);
      if (node) node.textContent = text[id];
    });
    var box = doc.getElementById("out-bensin");
    var empty = doc.getElementById("out-bensin-tom");
    if (!box || !empty) return;
    if (result.petrol) {
      box.hidden = false;
      empty.hidden = true;
      doc.getElementById("out-bensin-mil").textContent = result.petrol.perMil + " per mil";
      doc.getElementById("out-bensin-tid").textContent = result.petrol.perManad + " per månad, " + result.petrol.perAr + " per år";
      doc.getElementById("out-bensin-diff").textContent = result.petrol.diffText;
    } else {
      box.hidden = true;
      empty.hidden = false;
    }
  }

  function render(doc) {
    var form = doc.getElementById("laddkostnad");
    var err = doc.getElementById("ladd-fel");
    var figs = doc.getElementById("ladd-siffror");
    var status = doc.getElementById("ladd-status");
    if (!form || !err || !figs) return;
    clearInvalid(form);
    var result = compute({
      kwhPer100: parseSv(fieldOf(form, "forbrukning").value),
      distance: parseSv(fieldOf(form, "stracka").value),
      period: fieldOf(form, "period").value,
      homeShare: parseSv(fieldOf(form, "hemma").value),
      homePrice: parseSv(fieldOf(form, "elpris").value),
      fastPrice: parseSv(fieldOf(form, "snabb").value),
      lossPct: parseSv(fieldOf(form, "forlust").value),
      petrolL: parseSv(fieldOf(form, "bensinl").value),
      petrolPrice: parseSv(fieldOf(form, "bensinpris").value)
    });
    if (!result.ok) {
      figs.hidden = true;
      err.hidden = false;
      err.textContent = result.message;
      var bad = fieldOf(form, result.field);
      if (bad) {
        bad.setAttribute("aria-invalid", "true");
        bad.setAttribute("aria-describedby", ((bad.dataset.described || "") + " ladd-fel").trim());
      }
      if (status) status.textContent = "Rätt till värdet så räknas kostnaden igen.";
      return;
    }
    err.hidden = true;
    err.textContent = "";
    figs.hidden = false;
    fill(doc, result);
      if (status) status.textContent = "Uppdaterat utifrån värdena i formuläret.";
  }

  function bind(doc) {
    var form = doc.getElementById("laddkostnad");
    if (!form || form.dataset.bound) return;
    form.dataset.bound = "1";
    Array.prototype.forEach.call(form.elements, function (el) {
      var described = el.getAttribute && el.getAttribute("aria-describedby");
      if (described) el.dataset.described = described;
    });
    var reset = doc.getElementById("ladd-reset");
    if (reset) reset.hidden = false;
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      render(doc);
    });
    form.addEventListener("input", function () { render(doc); });
    form.addEventListener("change", function () { render(doc); });
    if (reset) reset.addEventListener("click", function () {
      fieldOf(form, "forbrukning").value = "18";
      fieldOf(form, "stracka").value = "100";
      fieldOf(form, "period").value = "manad";
      fieldOf(form, "hemma").value = "80";
      fieldOf(form, "elpris").value = "2,34";
      fieldOf(form, "snabb").value = "6";
      fieldOf(form, "forlust").value = "10";
      fieldOf(form, "bensinl").value = "0,7";
      fieldOf(form, "bensinpris").value = "18";
      render(doc);
      fieldOf(form, "forbrukning").focus();
    });
  }

  return { parseSv: parseSv, compute: compute, formatKr: formatKr, formatNumber: formatNumber, DEFAULTS: DEFAULTS, bind: bind, render: render };
});
