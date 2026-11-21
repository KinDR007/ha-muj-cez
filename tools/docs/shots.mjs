// Anonymized dark mode screenshots for docs/guide.
//
// Usage (from the repo root, tokens from config.md):
//   HA_LOCAL_URL=... HA_LOCAL_TOKEN=... HA_REMOTE_URL=... HA_REMOTE_TOKEN=... \
//     node tools/docs/shots.mjs [shot id ...]
//
// Shots are defined in shots.json: Home Assistant (local / remote), page path, actions
// (fill, click, clickLabel), the element to cut out (section by heading, card by tag,
// dialog, or a clip rectangle) and
// optional numbered callouts placed next to texts. Before every screenshot all visible
// text (including shadow DOM) is anonymized: strings from private.local.json (git-ignored:
// names, addresses, e-mails) and every run of 7+ digits (EAN, meter, contract, customer,
// invoice numbers, variable symbols). The reading card is never sent: "confirm" clicks
// are refused.

import { readFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright-core";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, "..", "..");
const SPEC = JSON.parse(readFileSync(join(HERE, "shots.json"), "utf8"));
const PRIVATE = JSON.parse(readFileSync(join(HERE, "private.local.json"), "utf8"));
const CHROME = process.env.CHROME || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const FORBIDDEN_CLICKS = ["#confirm"]; // would send a real meter reading

const hosts = {
  local: [process.env.HA_LOCAL_URL, process.env.HA_LOCAL_TOKEN],
  remote: [process.env.HA_REMOTE_URL, process.env.HA_REMOTE_TOKEN],
};

// --- in-page helpers (serialized into the page) -------------------------------------

function pageHelpers() {
  const deep = (root, out = []) => {
    for (const el of root.querySelectorAll("*")) {
      out.push(el);
      if (el.shadowRoot) deep(el.shadowRoot, out);
    }
    return out;
  };
  const textNodes = (root, out = []) => {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) out.push(walker.currentNode);
    for (const el of root.querySelectorAll("*")) if (el.shadowRoot) textNodes(el.shadowRoot, out);
    return out;
  };
  const fakeDigits = (s) => {
    if (s.length === 18 && s.startsWith("859")) return "859182400000000123";
    return "1234567890123456789".slice(0, s.length);
  };
  window.__anon = (replace) => {
    const keys = Object.keys(replace).sort((a, b) => b.length - a.length);
    const fix = (t) => {
      for (const k of keys) t = t.split(k).join(replace[k]);
      return t.replace(/\d{7,}/g, fakeDigits);
    };
    for (const n of textNodes(document)) {
      const t = fix(n.nodeValue);
      if (t !== n.nodeValue) n.nodeValue = t;
    }
    for (const el of deep(document)) {
      if ((el.localName === "input" || el.localName === "textarea") && el.value) {
        const t = fix(el.value);
        if (t !== el.value) el.value = t;
      }
    }
  };
  // Element whose own text starts with `text` (deepest match, visible).
  window.__findText = (text, within) => {
    const scope = within ? deep(document).find((e) => e.localName === within) : null;
    const pool = scope ? [scope, ...deep(scope.shadowRoot || scope)] : deep(document);
    let best = null;
    for (const el of pool) {
      const own = [...el.childNodes].filter((c) => c.nodeType === 3).map((c) => c.nodeValue).join("").trim();
      if (!own.startsWith(text)) continue;
      const r = el.getBoundingClientRect();
      if (r.width && r.height) best = el;
    }
    return best;
  };
  // Numbered badge right after the text itself (not the element box, which may span the
  // whole row) or centred above it ("above", for buttons) or left of the element ("left", for chips).
  window.__callouts = (items, within) => {
    for (const [n, text, pos] of items) {
      const el = window.__findText(text, within);
      if (!el) {
        console.warn("callout not found: " + text);
        continue;
      }
      const node = [...el.childNodes].find((c) => c.nodeType === 3 && c.nodeValue.trim());
      const range = document.createRange();
      range.selectNodeContents(node || el);
      const t = range.getBoundingClientRect();
      const box = el.getBoundingClientRect();
      const b = document.createElement("div");
      b.textContent = n;
      const left =
        pos === "above" ? box.left + box.width / 2 - 9 : pos === "left" ? box.left - 24 : t.right + 6;
      const top = pos === "above" ? box.top - 20 : t.top + t.height / 2 - 9;
      b.style.cssText =
        "position:fixed;z-index:99999;width:18px;height:18px;border-radius:50%;background:#ff5722;" +
        "color:#fff;font:700 11px/18px Roboto,Arial,sans-serif;text-align:center;" +
        `left:${left}px;top:${top}px`;
      document.body.appendChild(b);
    }
  };
  // Element to cut out: section by heading text, first element by tag, or a dialog.
  window.__target = (t) => {
    const all = deep(document);
    if (t.section) {
      return all.filter((e) => e.localName === "hui-section").find((s) => {
        const txt = textNodes(s.shadowRoot || s).map((n) => n.nodeValue).join(" ");
        return txt.includes(t.section);
      });
    }
    if (t.tag) return all.find((e) => e.localName === t.tag);
    if (t.dialog) {
      const ds = all.filter((e) => e.localName === "dialog" && e.getBoundingClientRect().height > 0);
      return ds[ds.length - 1] || null;
    }
    return null;
  };
}

// --- runner ---------------------------------------------------------------------------

async function open(browser, host, path, viewport) {
  const [url, token] = hosts[host];
  if (!url || !token) throw new Error(`Set HA_${host.toUpperCase()}_URL and _TOKEN`);
  const page = await browser.newPage({
    viewport: viewport || { width: 1400, height: 3000 },
    colorScheme: "dark",
    deviceScaleFactor: 2,
  });
  await page.goto(url + "/auth/authorize", { waitUntil: "domcontentloaded" }).catch(() => {});
  await page.evaluate(
    ([u, t]) => {
      localStorage.setItem(
        "hassTokens",
        JSON.stringify({ hassUrl: u, clientId: u + "/", access_token: t, token_type: "Bearer",
          expires_in: 1e9, refresh_token: "", expires: Date.now() + 1e12 }),
      );
      localStorage.setItem("selectedTheme", JSON.stringify({ theme: "default", dark: true }));
      localStorage.setItem("dockedSidebar", JSON.stringify("always_hidden"));
    },
    [url, token],
  );
  await page.goto(url + path, { waitUntil: "networkidle" }).catch(() => {});
  await page.waitForTimeout(6000);
  await page.evaluate(pageHelpers);
  return page;
}

async function act(page, a) {
  if (a.click) {
    if (FORBIDDEN_CLICKS.includes(a.click)) throw new Error(`refused click ${a.click}`);
    if (a.click.startsWith("text=")) {
      const handle = await page.evaluateHandle((t) => window.__findText(t), a.click.slice(5));
      await handle.asElement().click();
    } else {
      await page.locator(a.click).first().click();
    }
  }
  if (a.clickLabel) {
    // Icon buttons have their accessible name only as a property.
    const handle = await page.evaluateHandle((l) => {
      let found = null;
      const walk = (r) => {
        for (const e of r.querySelectorAll("*")) {
          if (!found && e.localName === "ha-icon-button" && e.label === l) found = e;
          if (e.shadowRoot) walk(e.shadowRoot);
        }
      };
      walk(document);
      return found;
    }, a.clickLabel);
    await handle.asElement().click();
  }
  if (a.fill) await page.locator(a.fill).first().fill(String(a.value));
  if (a.select) await page.locator(a.select).first().selectOption(String(a.value));
  await page.waitForTimeout(a.wait ?? 800);
}

async function shot(browser, s) {
  const page = await open(browser, s.host, s.path, s.viewport);
  for (const a of s.actions || []) await act(page, a);
  await page.evaluate((r) => window.__anon(r), PRIVATE.replace);
  if (s.callouts) await page.evaluate(([c, w]) => window.__callouts(c, w), [s.callouts, s.target.tag]);
  const out = join(ROOT, "docs", "guide", "img", `${s.id}.png`);
  mkdirSync(dirname(out), { recursive: true });
  if (s.target.clip) {
    const [x, y, width, height] = s.target.clip;
    await page.screenshot({ path: out, clip: { x, y, width, height } });
  } else {
    const el = (await page.evaluateHandle((t) => window.__target(t), s.target)).asElement();
    if (!el) throw new Error(`${s.id}: target not found`);
    await el.screenshot({ path: out });
  }
  // Final check: no long digit runs or private strings left in the page text.
  const leaks = await page.evaluate((keys) => {
    const txt = document.body.innerText + " " + [...document.querySelectorAll("*")]
      .filter((e) => e.shadowRoot).map((e) => e.shadowRoot.textContent).join(" ");
    return [...(txt.match(/\d{7,}/g) || []).filter((d) => !/^(859182400000000123|1234567)/.test(d)),
      ...keys.filter((k) => txt.includes(k))];
  }, Object.keys(PRIVATE.replace));
  console.log(`${s.id}: ${out.slice(ROOT.length + 1)}${leaks.length ? "  LEAKS? " + leaks.length : ""}`);
  await page.close();
}

const wanted = process.argv.slice(2);
const browser = await chromium.launch({ executablePath: CHROME });
try {
  for (const s of SPEC.shots) if (!wanted.length || wanted.includes(s.id)) await shot(browser, s);
} finally {
  await browser.close();
}
