#!/usr/bin/env node
/**
 * Native-window launcher for the review UI.
 *
 * Spawns Chromium in `--app=URL` mode (no address bar, no toolbar — a real
 * desktop application window) pointed at the local review server. Exits when
 * the user closes the window.
 *
 * Usage:
 *   node scripts/launcher.cjs --port 8765 --title "Record Icon Review" \
 *                              --width 1280 --height 800
 *
 * Or via env vars (used by the Python review_server subprocess):
 *   PUPPETEER_LAUNCHER_PORT=8765
 *   PUPPETEER_LAUNCHER_TITLE=...
 *   PUPPETEER_LAUNCHER_WIDTH=1280
 *   PUPPETEER_LAUNCHER_HEIGHT=800
 *
 * Exit codes:
 *   0  user closed the window normally
 *   1  invalid args / launch error
 *   2  navigation error (e.g. server unreachable, dist missing)
 */
"use strict";

const puppeteer = require("puppeteer");

function parseArgs(argv) {
  const args = { port: null, title: "Record Icon Review", width: 1280, height: 800 };
  for (let i = 0; i < argv.length; i++) {
    const flag = argv[i];
    const value = argv[i + 1];
    switch (flag) {
      case "--port":
        args.port = parseInt(value, 10);
        i++;
        break;
      case "--title":
        args.title = value;
        i++;
        break;
      case "--width":
        args.width = parseInt(value, 10);
        i++;
        break;
      case "--height":
        args.height = parseInt(value, 10);
        i++;
        break;
      case "--help":
      case "-h":
        process.stdout.write(
          "Usage: launcher.cjs --port <N> [--title T] [--width W] [--height H]\n"
        );
        process.exit(0);
        break;
      default:
        process.stderr.write(`Unknown flag: ${flag}\n`);
        process.exit(1);
    }
  }
  // Env var fallback (for Python subprocess invocation).
  if (args.port === null && process.env.PUPPETEER_LAUNCHER_PORT) {
    args.port = parseInt(process.env.PUPPETEER_LAUNCHER_PORT, 10);
  }
  if (process.env.PUPPETEER_LAUNCHER_TITLE) args.title = process.env.PUPPETEER_LAUNCHER_TITLE;
  if (process.env.PUPPETEER_LAUNCHER_WIDTH) args.width = parseInt(process.env.PUPPETEER_LAUNCHER_WIDTH, 10);
  if (process.env.PUPPETEER_LAUNCHER_HEIGHT) args.height = parseInt(process.env.PUPPETEER_LAUNCHER_HEIGHT, 10);
  return args;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.port || args.port < 1 || args.port > 65535) {
    process.stderr.write("Error: --port is required and must be 1-65535\n");
    process.exit(1);
  }

  const url = `http://127.0.0.1:${args.port}/`;

  let browser;
  try {
    browser = await puppeteer.launch({
      headless: false,
      // --app=URL         opens a real app window (no chrome UI: no address bar,
      //                   no tabs, no bookmarks bar). The URL is a no-op here; the
      //                   real URL is loaded via page.goto() below.
      // --window-size     initial window size
      // --window-position center the window on the primary display
      // --disable-features=Translate  skip the translate popup noise
      args: [
        `--app=data:text/html,`,
        `--window-size=${args.width},${args.height}`,
        "--window-position=center",
        "--disable-features=Translate",
        "--no-default-browser-check",
        "--no-first-run",
      ],
      defaultViewport: null, // respect --window-size; don't force a viewport
      // backgroundColor is the initial render color (avoids white flash).
      // Background color also matches our dark/light mode surface via prefers-color-scheme.
    });
  } catch (e) {
    process.stderr.write(`[launcher] failed to launch Chromium: ${e.message}\n`);
    process.exit(1);
  }

  // Listen for the user closing the window — the browser process disconnects.
  // This is the "user submitted or closed" signal back to the Python parent.
  const closed = new Promise((resolve) => {
    browser.on("disconnected", () => resolve("closed"));
  });

  const page = await browser.newPage();
  try {
    await page.goto(url, { waitUntil: "domcontentloaded", timeout: 10000 });
  } catch (e) {
    process.stderr.write(`[launcher] failed to load ${url}: ${e.message}\n`);
    await browser.close().catch(() => {});
    process.exit(2);
  }

  // Hand control to the user. We exit when the window closes.
  await closed;
  process.exit(0);
}

main().catch((e) => {
  process.stderr.write(`[launcher] fatal: ${e.stack || e.message}\n`);
  process.exit(1);
});
