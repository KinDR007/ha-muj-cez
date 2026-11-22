// Můj ČEZ: tabs of one supply point (overview, prices, meter reading) in one view.
// Served by the integration. Each tab holds sections like a sections view
// ({column_span, cards}), laid out in a responsive grid: as many columns as fit
// (at most max_columns), a section spans min(column_span, columns).
//
//   type: custom:muj-cez-tabs
//   id: <stable key, the selected tab is remembered per browser>
//   tabs:
//     - title: Přehled
//       icon: mdi:lightning-bolt-circle
//       max_columns: 3
//       max_width: 720        # optional, px, centers the content
//       sections: [{column_span: 2, cards: [...]}, ...]

const VERSION = "1";
const MIN_COLUMN = 340; // px, like the sections view
const GAP = 16;

class MujCezTabs extends HTMLElement {
  setConfig(config) {
    if (!Array.isArray(config?.tabs) || !config.tabs.length) {
      throw new Error("tabs are required");
    }
    this._config = config;
    this._panes = [];
    this._active = this._restore();
    if (this._root) this._render();
  }

  set hass(hass) {
    this._hass = hass;
    for (const pane of this._panes) for (const card of pane?.cards || []) card.hass = hass;
    if (!this._root) this._render();
  }

  connectedCallback() {
    if (!this._observer) {
      this._observer = new ResizeObserver(() => this._layout());
    }
    this._observer.observe(this);
  }

  disconnectedCallback() {
    this._observer?.disconnect();
  }

  getCardSize() {
    return 12;
  }

  getGridOptions() {
    return { columns: "full" };
  }

  _key() {
    return `muj-cez-tabs:${this._config.id || "default"}`;
  }

  _restore() {
    try {
      const index = Number(localStorage.getItem(this._key()));
      return Number.isInteger(index) && index >= 0 && index < this._config.tabs.length ? index : 0;
    } catch (_err) {
      return 0;
    }
  }

  _save() {
    try {
      localStorage.setItem(this._key(), String(this._active));
    } catch (_err) {
      // storage unavailable (private window): the first tab opens next time
    }
  }

  _render() {
    if (!this._config || !this._hass) return;
    if (!this._root) this._root = this.attachShadow({ mode: "open" });
    this._root.innerHTML = `
      <style>
        :host { display: block; }
        .bar { display: flex; overflow-x: auto; scrollbar-width: none;
          border-bottom: 1px solid var(--divider-color); margin-bottom: ${GAP}px; }
        .bar::-webkit-scrollbar { display: none; }
        button { flex: 1 0 auto; display: flex; align-items: center; justify-content: center;
          gap: 8px; padding: 12px 16px; background: none; border: none; cursor: pointer;
          border-bottom: 2px solid transparent; color: var(--secondary-text-color);
          font: inherit; font-size: 14px; font-weight: 500; letter-spacing: 0.05em;
          text-transform: uppercase; white-space: nowrap; }
        button:hover { color: var(--primary-text-color); }
        button[aria-selected="true"] { color: var(--primary-color);
          border-bottom-color: var(--primary-color); }
        ha-icon { --mdc-icon-size: 20px; }
        /* Panel views draw cards flat and edge to edge: keep the sections view look. */
        .panes { padding: 0 var(--muj-cez-tabs-padding, 16px) 16px;
          --ha-card-border-radius: var(--ha-border-radius-lg, 12px);
          --ha-card-border-width: 1px; }
        @media (max-width: 600px) { .panes { --muj-cez-tabs-padding: 8px; } }
        .pane { display: grid; gap: ${GAP}px; margin: 0 auto; align-items: start; }
        .pane[hidden] { display: none; }
        .section { display: flex; flex-direction: column; gap: 8px; min-width: 0; }
      </style>
      <div class="bar" role="tablist"></div>
      <div class="panes"></div>`;
    const bar = this._root.querySelector(".bar");
    const panes = this._root.querySelector(".panes");
    this._config.tabs.forEach((tab, index) => {
      const button = document.createElement("button");
      button.setAttribute("role", "tab");
      if (tab.icon) {
        const icon = document.createElement("ha-icon");
        icon.setAttribute("icon", tab.icon);
        button.append(icon);
      }
      button.append(document.createTextNode(tab.title || ""));
      button.addEventListener("click", () => this._select(index));
      bar.append(button);
      const pane = document.createElement("div");
      pane.className = "pane";
      pane.setAttribute("role", "tabpanel");
      if (tab.max_width) pane.style.maxWidth = `${tab.max_width}px`;
      panes.append(pane);
    });
    this._select(this._active);
  }

  _select(index) {
    this._active = index;
    this._save();
    const buttons = this._root.querySelectorAll("button");
    const panes = this._root.querySelectorAll(".pane");
    buttons.forEach((b, i) => b.setAttribute("aria-selected", String(i === index)));
    panes.forEach((p, i) => (p.hidden = i !== index));
    if (!this._panes[index]) this._build(index, panes[index]);
    this._layout();
    // Charts measure their size when shown.
    window.dispatchEvent(new Event("resize"));
  }

  async _build(index, pane) {
    const entry = { cards: [], sections: [] };
    this._panes[index] = entry;
    const helpers = await window.loadCardHelpers();
    const tab = this._config.tabs[index];
    const sections = tab.sections || [{ cards: tab.cards || [] }];
    for (const config of sections) {
      const section = document.createElement("div");
      section.className = "section";
      section.dataset.span = String(config.column_span || 1);
      for (const cardConfig of config.cards || []) {
        const card = helpers.createCardElement(cardConfig);
        card.hass = this._hass;
        entry.cards.push(card);
        section.append(card);
      }
      entry.sections.push(section);
      pane.append(section);
    }
    this._layout();
  }

  _layout() {
    const tabs = this._config?.tabs;
    if (!tabs || !this._root) return;
    const tab = tabs[this._active];
    const pane = this._root.querySelectorAll(".pane")[this._active];
    if (!pane) return;
    const width = Math.min(pane.parentElement.clientWidth, tab.max_width || Infinity);
    const fit = Math.max(1, Math.floor((width + GAP) / (MIN_COLUMN + GAP)));
    const columns = Math.min(fit, tab.max_columns || 1);
    pane.style.gridTemplateColumns = `repeat(${columns}, minmax(0, 1fr))`;
    for (const section of pane.querySelectorAll(".section")) {
      section.style.gridColumn = `span ${Math.min(Number(section.dataset.span), columns)}`;
    }
  }
}

if (!customElements.get("muj-cez-tabs")) {
  customElements.define("muj-cez-tabs", MujCezTabs);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "muj-cez-tabs",
    name: "Můj ČEZ záložky",
    description: "Přehled, ceny a odečet jednoho odběrného místa v záložkách.",
  });
  console.info(`%c MUJ-CEZ-TABS %c v${VERSION} `, "color:#fff;background:#f26a21", "");
}
