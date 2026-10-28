// Headless Odoo 16 UI check with playwright-core + the cached Playwright
// Chromium. Logs in, opens a client/window action, runs optional custom steps,
// records every JSON-RPC call (model.method, row/result size, errors) plus page
// errors, and saves a screenshot.
//
// Usage:
//   node ui_check.mjs --url http://127.0.0.1:18069 --login L --password P \
//        --action budget_dashboard [--steps steps.mjs] [--shot out.png] \
//        [--rpc-filter get_dashboard_data]
//
// A steps module exports `default async function (page, {log, shot, waitRpc})`:
//   log(...parts)      line in the final report
//   shot(name)         extra screenshot next to --shot (e.g. "before-search")
//   waitRpc(substr)    promise for the next call_kw response whose URL contains
//                      substr — start it BEFORE the action that triggers it
// Use it to pick filters, type searches, count rendered rows, etc.
import {chromium} from "playwright-core";
import {existsSync, readdirSync} from "node:fs";
import {homedir} from "node:os";
import {join, resolve} from "node:path";
import {pathToFileURL} from "node:url";

const args = Object.fromEntries(
  process.argv.slice(2).reduce((acc, cur, i, all) => {
    if (cur.startsWith("--")) acc.push([cur.slice(2), all[i + 1]]);
    return acc;
  }, [])
);
const url = (args.url || "http://127.0.0.1:18069").replace(/\/$/, "");
const shot = args.shot || "ui_check.png";

// Any headless shell already cached (macOS ~/Library/Caches, Linux ~/.cache),
// newest build first, so a teammate who installed Playwright for another
// project can run this before downloading the one playwright-core expects.
function findCachedShell() {
  const roots = [
    process.env.PLAYWRIGHT_BROWSERS_PATH,
    join(homedir(), "Library/Caches/ms-playwright"),
    join(homedir(), ".cache/ms-playwright"),
  ].filter((r) => r && existsSync(r));
  for (const root of roots) {
    const dirs = readdirSync(root)
      .filter((d) => d.startsWith("chromium_headless_shell-"))
      .sort((a, b) => Number(b.split("-")[1]) - Number(a.split("-")[1]));
    for (const d of dirs) {
      for (const sub of readdirSync(join(root, d))) {
        for (const exe of ["chrome-headless-shell", "headless_shell"]) {
          const path = join(root, d, sub, exe);
          if (existsSync(path)) return path;
        }
      }
    }
  }
  return undefined;
}

// Prefer the headless shell this playwright-core version expects.
async function launchBrowser() {
  if (args.chrome) return chromium.launch({executablePath: args.chrome});
  try {
    return await chromium.launch();
  } catch {
    const executablePath = findCachedShell();
    if (executablePath) return chromium.launch({executablePath});
    console.error(
      "No Playwright chromium found. Run: node " +
        "<skill>/scripts/node_modules/playwright-core/cli.js install chromium-headless-shell" +
        " (or pass --chrome <path>)."
    );
    process.exit(2);
  }
}

const report = [];
const log = (...parts) => report.push(parts.join(" "));
const browser = await launchBrowser();
const page = await browser.newPage({viewport: {width: 1600, height: 1000}});
page.on("pageerror", (e) => log("PAGEERROR", e.message));
page.on("console", (m) => m.type() === "error" && log("CONSOLE.ERROR", m.text()));
page.on("response", async (r) => {
  const u = r.url();
  if (!u.includes("/web/dataset/call_kw/")) return;
  if (args["rpc-filter"] && !u.includes(args["rpc-filter"])) return;
  const method = u.split("/web/dataset/call_kw/")[1];
  let body = {};
  try {
    body = await r.json();
  } catch {
    return;
  }
  if (body.error) {
    log(
      "RPC.ERROR",
      method,
      JSON.stringify(body.error.data?.message || body.error.message)
    );
    return;
  }
  const res = body.result;
  const size = Array.isArray(res)
    ? `list[${res.length}]`
    : res && Array.isArray(res.rows)
    ? `rows[${res.rows.length}]`
    : typeof res;
  const params = JSON.parse(r.request().postData() || "{}").params || {};
  const ctx = params.kwargs?.context || {};
  const extraCtx = Object.fromEntries(
    Object.entries(ctx).filter(
      ([k]) => !["lang", "tz", "uid", "allowed_company_ids"].includes(k)
    )
  );
  // Full args (truncated) so a shell check can replay exactly what the page sent.
  const argsJson = JSON.stringify(params.args || []).slice(0, 300);
  log("RPC", method, size, `args=${argsJson}`, `ctx=${JSON.stringify(extraCtx)}`);
});

try {
  await page.goto(`${url}/web/login`);
  await page.fill("input[name=login]", args.login);
  await page.fill("input[name=password]", args.password);
  await page.click("button[type=submit]");
  // Odoo keeps long-polling, so "networkidle" never fires: wait for the navbar.
  await page.waitForSelector(".o_main_navbar", {timeout: 90000});
  if (args.action) {
    // A hash change right after login aborts the navigation; reload instead.
    await page.goto(`${url}/web#action=${args.action}`).catch(() => {});
    await page.reload();
    await page.waitForSelector(".o_action_manager .o_action, .o_action_manager > *", {
      timeout: 90000,
    });
    await page.waitForTimeout(2000);
  }
  if (args.steps) {
    const base = resolve(shot).replace(/\.png$/, "");
    const helpers = {
      log,
      shot: async (name) => {
        const path = `${base}-${name}.png`;
        await page.screenshot({path});
        log("SCREENSHOT", path);
      },
      waitRpc: (substr, timeout = 120000) =>
        page.waitForResponse(
          (r) => r.url().includes("/web/dataset/call_kw/") && r.url().includes(substr),
          {timeout}
        ),
    };
    const mod = await import(pathToFileURL(resolve(args.steps)).href);
    await mod.default(page, helpers);
  }
} catch (e) {
  log("FAILED", e.message.split("\n")[0]);
} finally {
  await page.screenshot({path: shot}).catch(() => {});
  log("SCREENSHOT", resolve(shot));
  console.log(report.join("\n"));
  await browser.close();
}
