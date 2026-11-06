---
name: odoo-real-db-test
description:
  Verify Odoo 16 changes against a REAL database (UAT / prod / pre-production copy) on
  the local doodba stack — clone the DB, run the current worktree's code on the clone
  (install modules, call model methods in odoo shell, start a throwaway HTTP server),
  drive the web UI headlessly with Playwright, screenshot, then clean up. Use this
  whenever the user says "ทดสอบกับ database จริง", "ลองบน UAT", "test on real data",
  "reproduce on prod copy", reports that something "doesn't show on the web" /
  "หน้าเว็บไม่แสดง" after a change, or whenever static checks (pyflakes/xmllint) are not
  enough evidence and a runtime check on real data would settle the question — even if
  they don't name the database or the tools.
---

# Test Odoo changes on a real database (sandbox copy)

Static checks prove the code parses; they don't prove a report shows the right rows for
real data. This skill runs the **worktree's code** against a **copy** of a real DB, so
you can show evidence ("the RPC returns 10 item rows; the page renders them;
screenshot") instead of reasoning about it.

Three rules make this safe to do without asking every time:

- **Never touch the source DB or the user's runtime.** Work only on a clone whose name
  starts with `sbx_`, inside one-off containers. The script refuses every write or Odoo
  run on a db without that prefix; only `dbs` and the read-only `sql` look at other
  databases.
- **A clone of prod must not reach real people.** `clone` runs Odoo's `neutralize` on
  the copy (mail servers off, crons off, fetchmail/oauth off), and `serve` starts
  without cron threads. To publish its port, `serve` also joins a non-internal bridge
  (`odoo_sandbox_public`), so without this a served copy of prod can email real staff.
  If you create a sandbox any other way, run `$S/odoo_sandbox.sh neutralize <db>`
  before serving it.
- **Clean up what you create**, or leave it running only when you tell the user it's
  there and how to remove it.

Cloning a multi-GB DB and starting containers takes minutes; tell the user briefly what
you're doing before you start.

## Tools in this skill

- `scripts/odoo_sandbox.sh`: dbs, sql, clone, neutralize, install, update, shell, serve,
  stop, drop. Expects the `Aginix/kmitl-odoo` doodba stack at `~/Workspace/kmitl-odoo`
  (else set `ODOO_COMPOSE_DIR`) with its `db` service running; the postgres container is
  looked up from compose. Env overrides are documented at the top of the script.
- `scripts/set_admin_password.py` sets the admin password to `admin` on the clone and
  prints the login.
- `scripts/ui_check.mjs` runs a headless login, opens an action, runs optional custom
  steps, logs the RPCs and errors, and takes a screenshot.

In the examples, `S` is this skill's `scripts` folder: set
`S=<base directory of this skill>/scripts` (the skill loader prints the base directory;
in the kmitl repo it is `.agents/skills/odoo-real-db-test`).

Setup for the UI check (Node 20+). `node_modules` is git-ignored, so a fresh worktree
needs `npm ci` (about a second, served from the npm cache):

```bash
[ -d $S/node_modules/playwright-core ] || npm ci --prefix $S >/dev/null
node $S/node_modules/playwright-core/cli.js install chromium-headless-shell
```

The browser lives in the shared Playwright cache, so it downloads once per machine
(~15 s); later runs return in under a second. If the install runs for more than a
minute, it's hung, not slow: playwright-core older than 1.64 never finishes unzipping on
Node 26 and leaves a half-extracted folder, so every later run starts over. Kill it and
check that `node_modules` matches `package.json` (`npm ci --prefix $S`).

## Workflow

### 1. Pick the source DB and find the data

```bash
$S/odoo_sandbox.sh dbs
```

Choose the DB that actually contains the scenario. Check that with read-only SQL on the
source before you clone, because a clone of the wrong DB wastes minutes:

```bash
$S/odoo_sandbox.sh sql "<src>" "select count(*) from budget_move_line where kmitl_project_analytic_id is not null"
```

Use the table/field names you are testing. DB names differ per machine, so read them
from `dbs`. As a rule of thumb:

- `pre-production-*` are dumps of production. A run on the newest one counts as the prod
  dry-run for an upgrade or migration.
- `ok_uat-*` usually have the richest workflow history (obligate/consume, e-Saraban
  documents); prod copies may have none of the newer workflows.
- `devel` is often nearly empty.

Labels shown in the UI often live on a related record, not on the document you expect.
For example, a procurement plan row's text comes from its analytic account (`code` =
plan number, `name` = description). If a name isn't where you looked, follow the
many2one. Look up ids instead of guessing them: record ids such as fiscal years differ
per DB.

### 2. Clone and install

```bash
$S/odoo_sandbox.sh clone "<src>" sbx_<topic>
$S/odoo_sandbox.sh install sbx_<topic> new_module_a,new_bridge_b   # from inside the worktree
```

- `clone` tries an instant `CREATE DATABASE … TEMPLATE` first. A running Odoo keeps idle
  connections to every db, so this usually falls back to `pg_dump | pg_restore`
  automatically: about a minute per GB, and a few harmless `unaccent` index errors in
  the log. Tell the user it will take a while. Never kill the user's sessions to speed
  it up.
- `clone` ends by printing
  `neutralized: true, active crons: 1, active mail servers: invalid`. The one cron is
  `autovacuum`, and `invalid` is the dummy server that swallows mail. Anything else
  means the copy is not safe to serve.

- `install` uses `-i`. A **new** auto_install bridge is installed when its deps are
  installed in the same run. Listing it explicitly is harmless.
- For Python-only changes to already-installed modules you need **no upgrade**. The
  clone runs the worktree code as soon as the process starts.
- Use `update` (`-u`) only when data or views changed. `-u` on a core module cascades to
  every dependent and can be slow or fail on unrelated drift.
- The log commonly contains pre-existing drift noise, e.g. `Model X has no table` or
  `Some modules are not loaded … purchase_request_prepaid`. These come from a DB
  snapshot older than the code. Treat them as unrelated unless they name your modules.

### 3. Prove the server side in `odoo shell`

Write a small script that calls the method the UI calls, with the **same arguments and
context the front end sends**, and prints compact results. Missing context flags are a
classic reason why "it works in the test but not in the browser". To learn the exact
arguments, either read the component's `load()` / defaults in the JS, or run step 4 once
first: `ui_check.mjs` logs every RPC with its `args=` and non-default `ctx=` so you can
replay them.

```python
# /tmp/check.py
fy = env["account.fiscal.year"].search([("name", "=", "2570")])   # look ids up, don't hardcode
D = env["budget.dashboard"].with_context(pool_tag_rows=True)
rows = D.get_dashboard_data(fy.id, root_id, {"source_analytic_id": 421}, ["department_analytic_id"])["rows"]
items = [r for r in rows if r["row_type"] == "pool_tag"]
print("rows", len(rows), "items", len(items))
for r in items[:5]:
    print(" ", r["key"], "|", r["name"], r["current"])
```

```bash
$S/odoo_sandbox.sh shell sbx_<topic> /tmp/check.py
```

Print plain markers, because Odoo's own log lines are filtered out. Commit only when you
deliberately change the clone, e.g. the password script.

Keep check and steps scripts next to the screenshots (e.g. `<worktree>/.context/`), not
only in `/tmp`, so the evidence can be re-run and shown later.

### 4. Prove the UI headlessly (when the question is "does the page show it")

```bash
$S/odoo_sandbox.sh shell sbx_<topic> $S/set_admin_password.py   # prints SANDBOX_LOGIN=...
$S/odoo_sandbox.sh serve sbx_<topic> 18069                      # waits until /web/login answers
node $S/ui_check.mjs --url http://127.0.0.1:18069 --login <login> --password admin \
     --action <client_action_tag_or_id> --steps /tmp/steps.mjs \
     --shot <worktree>/.context/<topic>.png --rpc-filter <method>
```

A steps module drives the page and reports back:

```js
// <worktree>/.context/steps.mjs
export default async function (page, {log, shot, waitRpc}) {
  const selects = page.locator(".o_bd_controls select");
  // Select by visible label: option values are record ids that differ per DB.
  // Start waiting for the reload RPC *before* triggering it; fixed sleeps are
  // too short on big reports.
  const reloaded = waitRpc("get_dashboard_data");
  await selects.nth(0).selectOption({label: "2570"});
  await reloaded;
  await page.waitForTimeout(500); // let OWL render
  await shot("no-search");
  await page.fill(".o_brp_search input", "5108000020"); // client-side filter, no RPC
  await page.waitForTimeout(1000);
  log("items rendered:", await page.locator("tr.o_bd_pool_tag").count());
  log(
    "sample:",
    JSON.stringify(
      (await page.locator("tr.o_bd_pool_tag td").allInnerTexts()).slice(0, 4)
    )
  );
  await page
    .locator("tr.o_bd_pool_tag")
    .first()
    .scrollIntoViewIfNeeded()
    .catch(() => {});
}
```

Read the report in three layers. Each one isolates a different failure:

1. `RPC <model/method> rows[N] args=… ctx=…` tells you whether the server returned the
   data and whether the context reached it.
2. `items rendered: N` tells you whether the client showed it. Check filters such as
   hide-zero, search, and collapse.
3. `PAGEERROR` / `RPC.ERROR` / `CONSOLE.ERROR` shows a JS crash or server error.

The final screenshot is `--shot`. Each `shot(name)` saves an extra file next to it.
**Look at the screenshots** with the Read tool, and embed them for the user from
`.context/`.

### 5. Clean up

```bash
$S/odoo_sandbox.sh stop 18069
$S/odoo_sandbox.sh drop sbx_<topic>
```

If the user may want to click around themselves, leave the server up and tell them the
URL, the login, and these two cleanup commands.

## Gotchas learned the hard way

- **JS is served fresh from disk, Python is not.** A running Odoo picks up changed
  JS/XML/SCSS assets on the next page load, but Python changes need a process restart.
  "New JS + stale Python" fails silently, for example when a context flag is ignored and
  no error appears. When a user's server shows nothing while your sandbox works, suspect
  a missing restart or `-i` first.
- **Users' real interaction matters.** A row can be "missing" only because the user had
  typed a search, ticked hide-zero, or collapsed a parent. Ask what filters or search
  they used, or replay their exact steps in `steps.mjs`.
- **No `timeout` command on macOS.** Don't wrap commands in it. Use the Bash tool's
  timeout instead.
- **`networkidle` never fires in Odoo** because of bus long-polling. Wait for a selector
  such as `.o_main_navbar` or the view's root class.
- **`page.goto('/web#action=…')` right after login aborts** (`ERR_ABORTED`).
  `ui_check.mjs` catches it and reloads.
- **The filestore is not cloned.** `clone` deletes the cached asset bundles so Odoo
  rebuilds them; without that every page 500s on CSS/JS and `ui_check` times out on
  `.o_main_navbar`. Other attachments (uploaded files, images) stay missing and 500 as
  `FileNotFoundError` in the server log. That's expected unless your test reads files.
- **Rendering a PDF commits mid-call.** On a clone the report asset bundles don't exist
  yet, so the first PDF render generates them and commits the transaction.
  Savepoints vanish and "rolled back" test data stays. Render one PDF first as a
  warm-up, or treat the clone as dirty and re-read starting values on every run.
  Anything that prints during a flow (e.g. posting a budget transfer) triggers it.
- **The user's own `odoo` container may be down or on another branch.** That doesn't
  matter: the sandbox always runs the worktree passed to or detected by the script.
- **Port collisions:** the user's proxy uses 16069. Sandbox servers default to 18069,
  and `serve` refuses a port that is already listening. Pass another port to run two
  sandboxes side by side.
- **`install` verdict:** trust the module states it prints (`installed`), not the ERROR
  lines. A clean `-i` of a few modules finishes in seconds.
- **Admin login differs per DB** (e.g. `admin-erp@kmitl.ac.th`). Use the login that
  `set_admin_password.py` prints.
- **"This database is neutralized."** shows as a red bar on every page of a clone. It is
  expected in screenshots and confirms the safety step ran.
- Data in a clone is real, often Thai, and can include personal data. Keep it local,
  quote only what is needed as evidence, and drop the clone when done. Don't commit
  screenshots or outputs of real data to the repo; `.context/` is git-ignored.

## Reporting back

State plainly what was proven and on which data. For example: "On a copy of
`ok_uat-20260930`, `get_dashboard_data` returns 10 item rows. The page renders all 10
with names (screenshot)." Also state what was **not** covered, such as another DB,
another user's access rights, or a production server you can't reach. If the sandbox
contradicts the user's observation, say so and give the most likely environmental cause
(restart, `-i`, cache, filters) with a quick way for them to check, e.g. DevTools →
Network → the RPC's context and response.
