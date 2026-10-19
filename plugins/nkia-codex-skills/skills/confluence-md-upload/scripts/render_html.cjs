// Render an HTML report in headless Chrome, capture each interactive demo step by step,
// and write a static, Confluence-safe body.
// Usage: node render_html.cjs <config.json>
// config: {html, outDir, demoSelector, captureSelector, removeSelector, nextText, waitMs, maxSteps, width, snapshotSelector}
const fs = require('fs');
const path = require('path');
const puppeteer = require(process.env.PUPPETEER_PATH || 'puppeteer');

const cfg = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

(async () => {
  const browser = await puppeteer.launch({ headless: true, dumpio: !!process.env.RENDER_DEBUG, args: ['--no-sandbox', '--disable-setuid-sandbox'] });
  const page = await browser.newPage();
  await page.setViewport({ width: cfg.width, height: 1000, deviceScaleFactor: 1 });
  await page.emulateMediaFeatures([{ name: 'prefers-color-scheme', value: 'light' }]);
  await page.goto('file://' + path.resolve(cfg.html), { waitUntil: 'networkidle0' });
  // Open every toggle so figures inside them have a layout box, and hide demo controls
  // so the step images show only the visual and its caption.
  await page.evaluate((demoSel, removeSel) => {
    document.querySelectorAll('details').forEach((d) => { d.open = true; });
    if (removeSel) document.querySelectorAll(demoSel).forEach((demo) =>
      demo.querySelectorAll(removeSel).forEach((x) => { x.style.display = 'none'; }));
  }, cfg.demoSelector, cfg.removeSelector);
  await sleep(cfg.waitMs);

  const demos = await page.$$(cfg.demoSelector);
  const meta = [];
  for (let d = 0; d < demos.length; d++) {
    const demo = demos[d];
    const dir = path.join(cfg.outDir, `demo-${String(d + 1).padStart(2, '0')}`);
    fs.mkdirSync(dir, { recursive: true });
    // Capture area = union of the demo's visual parts (whole demo when none match).
    const clip = async () => page.evaluate((el, sel) => {
      const parts = [...el.querySelectorAll(sel)];
      const boxes = (parts.length ? parts : [el]).map((p) => p.getBoundingClientRect()).filter((b) => b.width && b.height);
      const x = Math.min(...boxes.map((b) => b.left)), y = Math.min(...boxes.map((b) => b.top));
      const r = Math.max(...boxes.map((b) => b.right)), btm = Math.max(...boxes.map((b) => b.bottom));
      return { x: x + window.scrollX, y: y + window.scrollY, width: r - x, height: btm - y };
    }, demo, cfg.captureSelector);
    const next = await page.evaluateHandle((el, text) =>
      [...el.querySelectorAll('button')].find((b) => b.textContent.trim() === text) || null, demo, cfg.nextText);
    const frames = [];
    let prev = null;
    for (let s = 0; s < cfg.maxSteps; s++) {
      await demo.scrollIntoView();
      await sleep(s === 0 ? 300 : cfg.waitMs);
      const c = await clip();
      const buf = await page.screenshot({ clip: { x: Math.floor(c.x), y: Math.floor(c.y), width: Math.ceil(c.width), height: Math.ceil(c.height) } });
      if (prev && Buffer.compare(prev, buf) === 0) break;
      const file = path.join(dir, `frame-${String(s).padStart(2, '0')}.png`);
      fs.writeFileSync(file, buf);
      frames.push({ file, width: Math.ceil(c.width), height: Math.ceil(c.height) });
      prev = buf;
      if (!next.asElement() || (await next.evaluate((b) => b.disabled))) break;
      await next.evaluate((b) => b.click());
    }
    meta.push({ dir, frames });
  }

  // Script-drawn figures outside demos (charts, SVG) become still images.
  const figs = await page.$$(cfg.snapshotSelector || ':not(*)');
  let figCount = 0;
  for (const fig of figs) {
    const ok = await fig.evaluate((el, demoSel, snapSel) => {
      if (el.closest(demoSel)) return false;
      const outer = el.parentElement && el.parentElement.closest(snapSel);
      return !outer && el.offsetWidth > 0 && el.offsetHeight > 0;
    }, cfg.demoSelector, cfg.snapshotSelector);
    if (!ok) continue;
    figCount += 1;
    const name = `figure-${String(figCount).padStart(2, '0')}.png`;
    await fig.scrollIntoView();
    await sleep(200);
    await fig.screenshot({ path: path.join(cfg.outDir, name) });
    await fig.evaluate((el, n) => {
      const p = document.createElement('p');
      const img = document.createElement('img');
      img.setAttribute('src', n);
      img.setAttribute('alt', n.replace('.png', ''));
      p.appendChild(img);
      el.replaceWith(p);
    }, name);
  }

  // Replace each demo's captured parts with an image placeholder, then build a static body.
  const body = await page.evaluate((c, count) => {
    const demos = [...document.querySelectorAll(c.demoSelector)];
    demos.forEach((demo, i) => {
      const parts = [...demo.querySelectorAll(c.captureSelector)];
      const img = document.createElement('img');
      img.setAttribute('src', `demo-${String(i + 1).padStart(2, '0')}.gif`);
      img.setAttribute('alt', `demo-${String(i + 1).padStart(2, '0')}`);
      const p = document.createElement('p');
      p.appendChild(img);
      (parts[0] || demo).before(p);
      parts.forEach((x) => x.remove());
      if (c.removeSelector) demo.querySelectorAll(c.removeSelector).forEach((x) => x.remove());
    });
    document.querySelectorAll('script,style,noscript,button,input,select,textarea,svg,canvas,link,meta,title').forEach((x) => x.remove());

    // <details> at block level become Confluence expands (markers folded later in ADF);
    // nested ones or ones inside tables/lists become a bold line followed by their body.
    const nestedIn = (el) => el.parentElement && el.parentElement.closest('details,li,td,th');
    [...document.querySelectorAll('details')].reverse().forEach((det) => {
      const sum = det.querySelector(':scope > summary');
      const title = sum ? sum.textContent.trim().replace(/\s+/g, ' ') : '';
      if (sum) sum.remove();
      const frag = document.createDocumentFragment();
      const open = document.createElement('p');
      const close = document.createElement('p');
      if (nestedIn(det)) {
        const b = document.createElement('strong');
        b.textContent = title;
        open.appendChild(b);
        frag.appendChild(open);
        while (det.firstChild) frag.appendChild(det.firstChild);
      } else {
        open.textContent = `[[EXPAND-OPEN]]${title}`;
        close.textContent = '[[EXPAND-CLOSE]]';
        frag.appendChild(open);
        while (det.firstChild) frag.appendChild(det.firstChild);
        frag.appendChild(close);
      }
      det.replaceWith(frag);
    });

    // Keep only elements Atlassian MCP HTML accepts: b/i become strong/em, other tags are unwrapped.
    const rename = { B: 'strong', I: 'em' };
    [...document.body.querySelectorAll('b,i')].reverse().forEach((el) => {
      const n = document.createElement(rename[el.tagName]);
      n.append(...el.childNodes);
      el.replaceWith(n);
    });
    const allowed = new Set(['H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'P', 'STRONG', 'EM', 'CODE', 'PRE', 'UL', 'OL', 'LI',
      'TABLE', 'THEAD', 'TBODY', 'TFOOT', 'TR', 'TH', 'TD', 'A', 'IMG', 'BR', 'HR', 'BLOCKQUOTE']);
    [...document.body.querySelectorAll('*')].reverse().forEach((el) => { if (!allowed.has(el.tagName)) el.replaceWith(...el.childNodes); });
    const keep = new Set(['href', 'src', 'alt', 'colspan', 'rowspan']);
    document.body.querySelectorAll('*').forEach((el) => {
      [...el.attributes].forEach((a) => { if (!keep.has(a.name)) el.removeAttribute(a.name); });
    });
    document.body.querySelectorAll('a[href^="#"]').forEach((a) => a.replaceWith(...a.childNodes));
    return document.body.innerHTML;
  }, cfg, demos.length);

  fs.writeFileSync(path.join(cfg.outDir, 'body.html'), body);
  fs.writeFileSync(path.join(cfg.outDir, 'demos.json'), JSON.stringify(meta, null, 1));
  await browser.close();
})().catch((e) => { console.error(e); process.exit(1); });
