// Můj ČEZ: customer meter reading (samoodečet) card.
// Served by the integration, validation and sending are done by the backend
// (websocket muj_cez/reading_form, muj_cez/reading_check, muj_cez/reading_submit).

const VERSION = "5";

const STRINGS = {
  cs: {
    title: "Odečet elektroměru",
    help: "Nápověda",
    point: "Odběrné místo",
    type: "Typ odečtu",
    date: "Stav ke dni",
    device: "Číslo elektroměru",
    previous: "Poslední stav",
    vt: "Vysoký tarif (T1)",
    nt: "Nízký tarif (T2)",
    note: "Poznámka pro vás",
    submit: "Zkontrolovat a odeslat",
    confirm: "Odeslat odečet",
    back: "Zpět",
    sent: "Odečet byl odeslán.",
    loading: "Načítám…",
    none: "Žádné odběrné místo elektřiny.",
    hint: "Počkejte, až bude na displeji aktivní T1. Opište číslice před desetinnou čárkou.",
    hint_dual: "Počkejte, až bude na displeji aktivní T1, pak T2. Opište číslice před desetinnou čárkou.",
    delta: "+{kwh} kWh za {days} d ({per_day} kWh/den)",
    summary: "Zkontrolujte údaje před odesláním",
    distributor: "Tento odečet se předá distributorovi.",
    errors: {
      required: "Povinný údaj",
      integer: "Zadejte celé číslo kWh",
      negative: "Hodnota nesmí být záporná",
      lower: "Hodnota je nižší než předchozí stav ze dne {date} ({value} kWh)",
      high: "Hodnota je nezvykle vysoká",
      date_future: "Datum nesmí být v budoucnosti",
      date_before: "Datum je dřív než poslední odečet ({date})",
      note_long: "Poznámka může mít nejvýš {max} znaků",
      type: "Neznámý typ odečtu",
      too_long: "Hodnota může mít nejvýš 9 číslic",
      duplicate_day: "K tomuto dni už je odečet zadaný",
      no_remaining: "Kontrolní odečty na letošní rok jsou vyčerpané",
      date_range: "Portál pro tento typ přijme datum od {min} do {max}",
      type_unavailable: "Tento typ odečtu teď u odběrného místa nejde zadat",
    },
    remaining: "Zbývá kontrolních odečtů letos: {n}",
    implausible: "Portál hodnoty označil za neobvyklé (např. po výměně elektroměru).",
    attachment: "Distributor odečet zamítl. Pokud jsou hodnoty správné, zadejte ho znovu na portálu s fotografií displeje.",
    types: {
      control: ["Kontrolní odečet pro distributora", "Odečet předáme distributorovi a bude zohledněn ve vyúčtování energií."],
      diary: ["Deníčkový odečet", "Slouží pro vaše vlastní sledování spotřeby. Nepředává se distributorovi ani do vyúčtování."],
      extraordinary: ["Odečet pro mimořádné vyúčtování", "Odečet předáme distributorovi a podle něj vystavíme mimořádné vyúčtování."],
      info: ["Odečet pro informace o vyúčtování", "Vystavíme informace o vyúčtování jen pro přehled o spotřebě. Předává se distributorovi."],
    },
  },
  en: {
    title: "Meter reading",
    help: "Help",
    point: "Supply point",
    type: "Reading type",
    date: "Reading date",
    device: "Meter number",
    previous: "Last reading",
    vt: "High tariff (T1)",
    nt: "Low tariff (T2)",
    note: "Your note",
    submit: "Check and send",
    confirm: "Send reading",
    back: "Back",
    sent: "The reading was sent.",
    loading: "Loading…",
    none: "No electricity supply point.",
    hint: "Wait until T1 is shown on the display. Enter the digits before the decimal point.",
    hint_dual: "Wait until T1, then T2 is shown on the display. Enter the digits before the decimal point.",
    delta: "+{kwh} kWh in {days} d ({per_day} kWh/day)",
    summary: "Check the reading before sending",
    distributor: "This reading is passed to the distributor.",
    errors: {
      required: "Required",
      integer: "Enter whole kWh",
      negative: "The value cannot be negative",
      lower: "Lower than the previous reading of {date} ({value} kWh)",
      high: "The value is unusually high",
      date_future: "The date cannot be in the future",
      date_before: "The date is before the last reading ({date})",
      note_long: "The note can have at most {max} characters",
      type: "Unknown reading type",
      too_long: "At most 9 digits",
      duplicate_day: "A reading for this day already exists",
      no_remaining: "No control readings left this year",
      date_range: "The portal accepts a date from {min} to {max} for this type",
      type_unavailable: "This reading type is not available for the supply point now",
    },
    remaining: "Control readings left this year: {n}",
    implausible: "The portal marked the values as unusual (e.g. after a meter replacement).",
    attachment: "The distributor rejected the reading. If the values are right, enter it again on the portal with a photo of the display.",
    types: {
      control: ["Control reading for the distributor", "Passed to the distributor and used in billing."],
      diary: ["Diary reading", "For your own tracking only, not passed to the distributor."],
      extraordinary: ["Reading for extraordinary billing", "Passed to the distributor, an extraordinary bill is issued."],
      info: ["Reading for billing information", "Billing information for your overview. Passed to the distributor."],
    },
  },
};

const fmtDate = (iso, lang) =>
  iso ? new Date(iso + "T00:00:00").toLocaleDateString(lang === "cs" ? "cs-CZ" : undefined) : "";
const fmtNum = (v, lang) =>
  v === null || v === undefined ? "–" : Number(v).toLocaleString(lang === "cs" ? "cs-CZ" : undefined);
const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

class MujCezReadingCard extends HTMLElement {
  setConfig(config) {
    this._config = config || {};
    this._state = { phase: "loading" };
    this._form = { type: "diary", date: null, vt: "", nt: "", note: "" };
    this._touched = new Set();
  }

  static getStubConfig() {
    return {};
  }

  getCardSize() {
    return 8;
  }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    if (first) {
      this._lang = (hass.language || "en").startsWith("cs") ? "cs" : "en";
      this._t = STRINGS[this._lang];
      this.attachShadow({ mode: "open" });
      this._load();
    }
  }

  async _load() {
    this._render();
    try {
      const msg = { type: "muj_cez/reading_form" };
      if (this._config.entry_id) msg.entry_id = this._config.entry_id;
      const data = await this._hass.callWS(msg);
      this._data = data;
      const points = data.points || [];
      const wanted = points.find((p) => p.ean === this._config.ean) || points[0];
      this._point = wanted ? wanted.key : null;
      this._form.date = data.today;
      this._state = { phase: points.length ? "form" : "empty" };
    } catch (err) {
      this._state = { phase: "error", message: err.message || String(err) };
    }
    this._render();
    this._check();
  }

  get _current() {
    return (this._data?.points || []).find((p) => p.key === this._point);
  }

  _payload() {
    const p = this._current;
    return {
      entry_id: p.entry_id,
      ean: p.ean,
      reading_type: this._form.type,
      date: this._form.date,
      vt: this._form.vt,
      nt: p.dual_tariff ? this._form.nt : null,
      note: this._form.note,
    };
  }

  _check() {
    clearTimeout(this._timer);
    if (this._state.phase !== "form" || !this._current) return;
    this._timer = setTimeout(async () => {
      try {
        this._result = await this._hass.callWS({ type: "muj_cez/reading_check", ...this._payload() });
      } catch (err) {
        this._result = { ok: false, errors: [], warnings: [], message: err.message };
      }
      this._renderIssues();
    }, 250);
  }

  async _submit() {
    this._state = { phase: "sending" };
    this._render();
    try {
      const res = await this._hass.callWS({ type: "muj_cez/reading_submit", ...this._payload() });
      this._state = { phase: "done", result: res };
    } catch (err) {
      this._state = { phase: "form", message: err.message || String(err) };
    }
    this._render();
    if (this._state.phase === "form") this._check();
  }

  _msg(issue) {
    let text = this._t.errors[issue.code] || issue.code;
    const params = { ...issue.params };
    for (const k of ["date", "min", "max"]) if (params[k]) params[k] = fmtDate(params[k], this._lang);
    if (params.value !== undefined) params.value = fmtNum(params.value, this._lang);
    for (const [k, v] of Object.entries(params)) text = text.replace(`{${k}}`, v);
    return text;
  }

  _renderIssues() {
    const root = this.shadowRoot;
    if (!root || !this._result) return;
    const r = this._result;
    for (const field of ["type", "date", "vt", "nt", "note"]) {
      const box = root.getElementById(`issues-${field}`);
      if (!box) continue;
      // "required" only after the user has been in the field (as on the portal)
      const errs = (r.errors || []).filter(
        (i) => i.field === field && (i.code !== "required" || this._touched.has(field)),
      );
      const warns = (r.warnings || []).filter((i) => i.field === field);
      const delta = r.delta?.[field];
      let html = errs.map((i) => `<div class="err">⛔ ${esc(this._msg(i))}</div>`).join("");
      html += warns.map((i) => `<div class="warn">⚠ ${esc(this._msg(i))}</div>`).join("");
      if (delta && !errs.length) {
        let text = this._t.delta;
        for (const [k, v] of Object.entries(delta)) text = text.replace(`{${k}}`, fmtNum(v, this._lang));
        html += `<div class="info">${esc(text)}</div>`;
      }
      box.innerHTML = html;
      root.getElementById(`field-${field}`)?.classList.toggle("bad", errs.length > 0);
      root.getElementById(`field-${field}`)?.classList.toggle("warned", !errs.length && warns.length > 0);
    }
    const count = root.getElementById("note-count");
    if (count) count.textContent = `${this._form.note.length}/${this._data.note_max}`;
    const btn = root.getElementById("submit");
    if (btn) btn.disabled = !r.ok;
    const general = root.getElementById("general");
    if (general) general.textContent = r.message || "";
  }

  _render() {
    const root = this.shadowRoot;
    if (!root) return;
    const t = this._t;
    const s = this._state;
    let body = "";
    if (s.phase === "loading") body = `<p class="muted">${t.loading}</p>`;
    else if (s.phase === "error") body = `<p class="err">${esc(s.message)}</p>`;
    else if (s.phase === "empty") body = `<p class="muted">${t.none}</p>`;
    else if (s.phase === "confirm") body = this._confirmHtml();
    else if (s.phase === "sending") body = `<p class="muted">${t.loading}</p>`;
    else if (s.phase === "done") body = this._doneHtml();
    else body = this._formHtml();
    const url = this._data?.docs_url;
    const help = url
      ? `<a class="help" href="${esc(url)}" target="_blank" rel="noreferrer" title="${t.help}" aria-label="${t.help}">?</a>`
      : "";
    root.innerHTML = `<style>${CSS}</style>
      <ha-card>
        <div class="head"><span>${esc(this._config.title || t.title)}</span>${help}</div>
        <div class="body">${body}</div>
      </ha-card>`;
    this._bind();
    if (s.phase === "form") this._renderIssues();
  }

  _formHtml() {
    const t = this._t;
    const p = this._current;
    const points = this._data.points;
    const f = this._form;
    const pointSel =
      points.length > 1
        ? `<label class="field"><span class="lbl">${t.point}</span>
            <select id="point">${points
              .map((x) => `<option value="${esc(x.key)}" ${x.key === p.key ? "selected" : ""}>${esc(x.label)}</option>`)
              .join("")}</select></label>`
        : `<div class="field"><span class="lbl">${t.point}</span><div class="ro">${esc(p.label)}</div></div>`;
    if (!(p.types || this._data.types).includes(f.type)) f.type = (p.types || this._data.types)[0];
    const types = (p.types || this._data.types)
      .map((k) => `<option value="${k}" ${k === f.type ? "selected" : ""}>${esc(t.types[k]?.[0] || k)}</option>`)
      .join("");
    const prev = p.previous || {};
    const prevText = prev.date
      ? `${fmtDate(prev.date, this._lang)} · VT ${fmtNum(prev.vt, this._lang)} kWh` +
        (p.dual_tariff ? ` · NT ${fmtNum(prev.nt, this._lang)} kWh` : "")
      : "–";
    const reg = (key) => `
      <label class="field" id="field-${key}"><span class="lbl">${t[key]} *</span>
        <div class="unit"><input id="${key}" inputmode="numeric" autocomplete="off" value="${esc(f[key])}"><span>kWh</span></div>
        <div class="issues" id="issues-${key}"></div></label>`;
    return `
      ${pointSel}
      <label class="field" id="field-type"><span class="lbl">${t.type}</span>
        <select id="type">${types}</select>
        <div class="muted small">${esc(t.types[f.type]?.[1] || "")}</div>
        ${f.type === "control" && p.remaining_control != null ? `<div class="muted small">${esc(t.remaining.replace("{n}", p.remaining_control))}</div>` : ""}
        <div class="issues" id="issues-type"></div></label>
      <label class="field" id="field-date"><span class="lbl">${t.date}</span>
        <input id="date" type="date" max="${this._data.today}" value="${esc(f.date)}">
        <div class="issues" id="issues-date"></div></label>
      <div class="row">
        <div class="field"><span class="lbl">${t.device}</span><div class="ro">${esc(p.device || "–")}</div></div>
        <div class="field"><span class="lbl">${t.previous}</span><div class="ro">${esc(prevText)}</div></div>
      </div>
      ${reg("vt")}
      ${p.dual_tariff ? reg("nt") : ""}
      <div class="hint">ⓘ ${p.dual_tariff ? t.hint_dual : t.hint}</div>
      <label class="field" id="field-note"><span class="lbl">${t.note}</span>
        <input id="note" maxlength="${this._data.note_max}" value="${esc(f.note)}">
        <div class="muted small" id="note-count">${f.note.length}/${this._data.note_max}</div>
        <div class="issues" id="issues-note"></div></label>
      <div class="err" id="general">${esc(this._state.message || "")}</div>
      <button id="submit" class="primary" disabled>${t.submit}</button>`;
  }

  _confirmHtml() {
    const t = this._t;
    const p = this._current;
    const f = this._form;
    const r = this._result || {};
    const line = (key) => {
      const d = r.delta?.[key];
      const extra = d ? ` (+${fmtNum(d.kwh, this._lang)} kWh)` : "";
      return `<tr><td>${t[key]}</td><td>${esc(fmtNum(f[key], this._lang))} kWh${extra}</td></tr>`;
    };
    const toDistributor = (this._data.distributor_types || []).includes(f.type);
    const warns = (r.warnings || []).map((i) => `<div class="warn">⚠ ${t[i.field] || ""}: ${esc(this._msg(i))}</div>`);
    return `
      <p><b>${t.summary}</b></p>
      <table>
        <tr><td>${t.point}</td><td>${esc(p.label)}</td></tr>
        <tr><td>${t.type}</td><td>${esc(t.types[f.type]?.[0] || f.type)}</td></tr>
        <tr><td>${t.date}</td><td>${esc(fmtDate(f.date, this._lang))}</td></tr>
        ${line("vt")}
        ${p.dual_tariff ? line("nt") : ""}
        ${f.note ? `<tr><td>${t.note}</td><td>${esc(f.note)}</td></tr>` : ""}
      </table>
      ${warns.join("")}
      ${toDistributor ? `<div class="warn">${t.distributor}</div>` : ""}
      <button id="confirm" class="primary">${t.confirm}</button>
      <button id="back" class="link">${t.back}</button>`;
  }

  _doneHtml() {
    const t = this._t;
    const res = this._state.result || {};
    let text = `<p class="ok">✓ ${t.sent}</p>`;
    if (res.implausible) text += `<div class="warn">⚠ ${t.implausible}</div>`;
    if (res.attachment_needed) text += `<div class="err">⛔ ${t.attachment}</div>`;
    return `${text}<button id="back" class="link">${t.back}</button>`;
  }

  _bind() {
    const root = this.shadowRoot;
    const on = (id, ev, fn) => root.getElementById(id)?.addEventListener(ev, fn);
    on("point", "change", (e) => {
      this._point = e.target.value;
      this._touched.clear();
      this._render();
      this._check();
    });
    on("type", "change", (e) => {
      this._form.type = e.target.value;
      this._render();
      this._check();
    });
    for (const key of ["date", "vt", "nt", "note"]) {
      on(key, "input", (e) => {
        this._form[key] = e.target.value;
        this._touched.add(key);
        this._check();
      });
    }
    on("submit", "click", () => {
      if (!this._result?.ok) return;
      this._state = { phase: "confirm" };
      this._render();
    });
    on("confirm", "click", () => this._submit());
    on("back", "click", () => {
      if (this._state.phase === "done") {
        this._form = { ...this._form, vt: "", nt: "", note: "" };
        this._touched.clear();
        this._load();
        return;
      }
      this._state = { phase: "form" };
      this._render();
      this._check();
    });
  }
}

const CSS = `
  ha-card { overflow: hidden; }
  .head { display: flex; align-items: center; justify-content: space-between; padding: 16px 16px 0; font-size: 1.25em; font-weight: 500; }
  .help { width: 24px; height: 24px; border-radius: 50%; border: 1px solid var(--secondary-text-color);
    color: var(--secondary-text-color); font-size: 0.6em; line-height: 24px; text-align: center; text-decoration: none; }
  .help:hover { color: var(--primary-color); border-color: var(--primary-color); }
  .body { padding: 8px 16px 16px; display: flex; flex-direction: column; gap: 12px; }
  .field { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
  .row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  .lbl { font-size: 0.85em; color: var(--secondary-text-color); }
  .ro { padding: 6px 0; border-bottom: 1px solid var(--divider-color); overflow-wrap: anywhere; }
  input, select { font: inherit; color: var(--primary-text-color); background: var(--card-background-color, transparent);
    border: none; border-bottom: 1px solid var(--secondary-text-color); padding: 6px 0; outline: none; width: 100%; box-sizing: border-box; }
  input:focus, select:focus { border-bottom: 2px solid var(--primary-color); }
  .unit { display: flex; align-items: center; gap: 8px; }
  .unit span { color: var(--secondary-text-color); }
  .bad input { border-bottom: 2px solid var(--error-color, #db4437); }
  .warned input { border-bottom: 2px solid var(--warning-color, #ffa600); }
  .err { color: var(--error-color, #db4437); font-size: 0.9em; }
  .warn { color: var(--warning-color, #ffa600); font-size: 0.9em; }
  .info { color: var(--secondary-text-color); font-size: 0.9em; }
  .ok { color: var(--success-color, #43a047); }
  .muted { color: var(--secondary-text-color); }
  .small { font-size: 0.85em; }
  .hint { background: var(--secondary-background-color); border-radius: 8px; padding: 10px 12px; font-size: 0.9em; }
  button.primary { font: inherit; padding: 10px; border: none; border-radius: 8px; cursor: pointer;
    background: var(--primary-color); color: var(--text-primary-color, #fff); }
  button.primary:disabled { opacity: 0.4; cursor: default; }
  button.link { font: inherit; background: none; border: none; color: var(--primary-color); cursor: pointer; padding: 6px; }
  table { border-collapse: collapse; width: 100%; }
  td { padding: 4px 0; vertical-align: top; }
  td:first-child { color: var(--secondary-text-color); padding-right: 12px; white-space: nowrap; }
  pre { white-space: pre-wrap; overflow-wrap: anywhere; background: var(--secondary-background-color); padding: 8px; border-radius: 8px; font-size: 0.8em; }
  @media (max-width: 420px) { .row { grid-template-columns: 1fr; } }
`;

// Loaded early (frontend extra module): the frontend may replace the custom element
// registry afterwards (scoped elements polyfill) and the first definition is lost, so it
// is checked again until the app has started.
const define = () => {
  if (!customElements.get("muj-cez-reading-card")) {
    customElements.define("muj-cez-reading-card", MujCezReadingCard);
  }
};
define();
for (const ms of [100, 500, 1500, 3000, 6000, 10000]) setTimeout(define, ms);
window.addEventListener("load", define);
window.customCards = window.customCards || [];
if (!window.customCards.some((c) => c.type === "muj-cez-reading-card")) {
  window.customCards.push({
    type: "muj-cez-reading-card",
    name: "Můj ČEZ: odečet elektroměru",
    description: "Zadání samoodečtu VT/NT s kontrolou hodnot.",
  });
  console.info(`muj-cez-reading-card ${VERSION}`);
}
