import http from 'node:http';
import fs from 'node:fs/promises';
import fssync from 'node:fs';
import path from 'node:path';
import { spawn } from 'node:child_process';

const sourceDir = '/Users/adib/Desktop/Infinity_AI_Buildfest/InfluenceIQ';
const outDir = '/Users/adib/Documents/InfluenceIQ/audit/original-screenshots';
const chromePath = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const port = 4187;
const cdpPort = 9333;
const widths = [1440, 1280, 1024, 768, 430, 390];
const routes = [
  ['landing', 'InfluenceIQ.html'],
  ['signup', 'Signup.html'],
  ['onboarding', 'Onboarding.html'],
  ['dashboard', 'Dashboard.html'],
  ['discover', 'Discover.html'],
  ['discover-table', 'DiscoverTable.html'],
  ['lists', 'Lists.html'],
  ['briefs', 'Briefs.html'],
  ['brief-new', 'Brief.html'],
  ['matching', 'Matching.html'],
  ['shortlist', 'Shortlist.html'],
  ['profile', 'Profile.html'],
  ['settings', 'Settings.html'],
];

function contentType(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  if (ext === '.html') return 'text/html; charset=utf-8';
  if (ext === '.css') return 'text/css; charset=utf-8';
  if (ext === '.js') return 'application/javascript; charset=utf-8';
  if (ext === '.svg') return 'image/svg+xml';
  if (ext === '.png') return 'image/png';
  if (ext === '.jpg' || ext === '.jpeg') return 'image/jpeg';
  return 'application/octet-stream';
}

function startStaticServer() {
  const server = http.createServer(async (req, res) => {
    try {
      const rawUrl = new URL(req.url ?? '/', `http://127.0.0.1:${port}`);
      const requested = decodeURIComponent(rawUrl.pathname === '/' ? '/InfluenceIQ.html' : rawUrl.pathname);
      const normalized = path.normalize(requested).replace(/^(\.\.(\/|\\|$))+/, '');
      const filePath = path.join(sourceDir, normalized);
      if (!filePath.startsWith(sourceDir)) {
        res.writeHead(403);
        res.end('Forbidden');
        return;
      }
      const bytes = await fs.readFile(filePath);
      res.writeHead(200, { 'Content-Type': contentType(filePath) });
      res.end(bytes);
    } catch {
      res.writeHead(404);
      res.end('Not found');
    }
  });
  return new Promise((resolve) => {
    server.listen(port, '127.0.0.1', () => resolve(server));
  });
}

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitForPageTarget() {
  const endpoint = `http://127.0.0.1:${cdpPort}/json/list`;
  for (let i = 0; i < 80; i += 1) {
    try {
      const res = await fetch(endpoint);
      if (res.ok) {
        const targets = await res.json();
        const page = targets.find((target) => target.type === 'page' && target.webSocketDebuggerUrl);
        if (page) return page;
      }
    } catch {
      // Chrome is still starting.
    }
    await wait(250);
  }
  throw new Error('Chrome page DevTools endpoint did not become available.');
}

async function cdpConnect(wsUrl) {
  const ws = new WebSocket(wsUrl);
  let id = 0;
  const pending = new Map();
  ws.addEventListener('message', (event) => {
    const msg = JSON.parse(event.data);
    if (msg.id && pending.has(msg.id)) {
      const { resolve, reject } = pending.get(msg.id);
      pending.delete(msg.id);
      if (msg.error) reject(new Error(JSON.stringify(msg.error)));
      else resolve(msg.result);
    }
  });
  await new Promise((resolve, reject) => {
    ws.addEventListener('open', resolve, { once: true });
    ws.addEventListener('error', reject, { once: true });
  });
  return {
    send(method, params = {}) {
      id += 1;
      ws.send(JSON.stringify({ id, method, params }));
      return new Promise((resolve, reject) => pending.set(id, { resolve, reject }));
    },
    close() {
      ws.close();
    },
  };
}

async function captureRoute(cdp, slug, file, width) {
  const url = `http://127.0.0.1:${port}/${file}`;
  await cdp.send('Emulation.setDeviceMetricsOverride', {
    width,
    height: 900,
    deviceScaleFactor: 1,
    mobile: width < 768,
  });
  await cdp.send('Page.navigate', { url });
  await wait(file === 'Matching.html' ? 700 : 1200);
  const metrics = await cdp.send('Runtime.evaluate', {
    expression: `(() => {
      const b = document.body;
      const e = document.documentElement;
      return {
        width: Math.max(b.scrollWidth, e.scrollWidth, b.offsetWidth, e.offsetWidth, e.clientWidth),
        height: Math.max(b.scrollHeight, e.scrollHeight, b.offsetHeight, e.offsetHeight, e.clientHeight),
        title: document.title
      };
    })()`,
    returnByValue: true,
  });
  const pageWidth = Math.ceil(metrics.result.value.width);
  const pageHeight = Math.ceil(metrics.result.value.height);
  await cdp.send('Emulation.setDeviceMetricsOverride', {
    width,
    height: Math.min(Math.max(pageHeight, 900), 16000),
    deviceScaleFactor: 1,
    mobile: width < 768,
  });
  const screenshot = await cdp.send('Page.captureScreenshot', {
    format: 'png',
    captureBeyondViewport: true,
    fromSurface: true,
    clip: {
      x: 0,
      y: 0,
      width: Math.max(pageWidth, width),
      height: pageHeight,
      scale: 1,
    },
  });
  const filename = `${slug}-${width}.png`;
  await fs.writeFile(path.join(outDir, filename), Buffer.from(screenshot.data, 'base64'));
  return { slug, file, width, filename, title: metrics.result.value.title, pageWidth, pageHeight };
}

async function main() {
  await fs.mkdir(outDir, { recursive: true });
  const server = await startStaticServer();
  const userDataDir = `/private/tmp/influenceiq-chrome-profile-${Date.now()}`;
  const chrome = spawn(chromePath, [
    '--headless=new',
    '--disable-gpu',
    '--hide-scrollbars',
    '--no-first-run',
    '--no-default-browser-check',
    `--remote-debugging-port=${cdpPort}`,
    `--user-data-dir=${userDataDir}`,
    `http://127.0.0.1:${port}/InfluenceIQ.html`,
  ], { stdio: 'ignore' });

  try {
    const pageTarget = await waitForPageTarget();
    const cdp = await cdpConnect(pageTarget.webSocketDebuggerUrl);
    await cdp.send('Page.enable');
    await cdp.send('Runtime.enable');

    const manifest = [];
    for (const [slug, file] of routes) {
      for (const width of widths) {
        const result = await captureRoute(cdp, slug, file, width);
        manifest.push(result);
        console.log(`${result.filename} ${result.pageWidth}x${result.pageHeight}`);
      }
    }
    await fs.writeFile(
      '/Users/adib/Documents/InfluenceIQ/audit/original-screenshots-manifest.json',
      `${JSON.stringify({ capturedAt: new Date().toISOString(), routes, widths, screenshots: manifest }, null, 2)}\n`,
    );
    cdp.close();
  } finally {
    chrome.kill('SIGTERM');
    server.close();
    if (fssync.existsSync(userDataDir)) {
      await fs.rm(userDataDir, { recursive: true, force: true, maxRetries: 3, retryDelay: 250 });
    }
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
