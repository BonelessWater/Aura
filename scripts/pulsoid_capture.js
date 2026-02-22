/**
 * Pulsoid heart rate capture
 * Loads the Pulsoid widget in headless Chromium, reads the displayed BPM
 * every 2 seconds, and writes a rolling 90-second window to
 * public/data/live_hr.json so the dashboard can poll it.
 *
 * Run with:  node scripts/pulsoid_capture.js
 */

import { chromium } from 'playwright';
import { writeFileSync, readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import path from 'path';

const WIDGET_URL = 'https://pulsoid.net/widget/view/41ec10fc-556a-40e4-99f8-49776c9a8498';
const OUT_FILE   = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../public/data/live_hr.json');
const POLL_MS    = 2000;   // read DOM every 2 s
const WINDOW_S   = 90;     // keep 90 seconds of history

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page    = await browser.newPage();

  console.log('Opening widget…');
  await page.goto(WIDGET_URL, { waitUntil: 'domcontentloaded' });

  // Give the widget JS time to connect and render the first reading
  await page.waitForTimeout(4000);
  console.log('Capturing…');

  let history = [];

  const poll = async () => {
    try {
      // Pulsoid widgets render the BPM as the largest visible text node.
      // We grab every text node and pick the one that's a plausible BPM number.
      const bpm = await page.evaluate(() => {
        const walker = document.createTreeWalker(
          document.body,
          NodeFilter.SHOW_TEXT,
          null,
        );
        const candidates = [];
        let node;
        while ((node = walker.nextNode())) {
          const t = node.textContent.trim();
          const n = parseInt(t, 10);
          if (!isNaN(n) && n >= 30 && n <= 230 && t === String(n)) {
            candidates.push(n);
          }
        }
        // Return the largest candidate (avoids picking small UI numbers)
        return candidates.length ? Math.max(...candidates) : null;
      });

      if (bpm !== null) {
        const now = Date.now();
        history.push({ ts: now, bpm });

        // Trim to rolling window
        const cutoff = now - WINDOW_S * 1000;
        history = history.filter(p => p.ts >= cutoff);

        writeFileSync(OUT_FILE, JSON.stringify(history));
        process.stdout.write(`\r${new Date().toLocaleTimeString()}  ❤  ${bpm} bpm   `);
      }
    } catch (e) {
      // Page may reload / reconnect — just keep going
    }
  };

  // Poll immediately then on interval
  await poll();
  setInterval(poll, POLL_MS);

  // Keep alive
  process.on('SIGINT', async () => {
    console.log('\nShutting down…');
    await browser.close();
    process.exit(0);
  });
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});
