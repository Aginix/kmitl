---
name: kmitl-pr
description:
  End-to-end pull request flow for the KMITL Odoo repo — rename the branch to
  `16.0-{type}-{module}-{desc}`, test the change on a sandbox DB with
  odoo-real-db-test and capture screenshots, commit with `--no-verify` (no Claude
  co-author), push, upload the screenshots to a `pr-assets/<branch>` branch, and open a
  GitHub PR whose description is written in Thai with the test results embedded. Use
  whenever the user asks to "เปิด PR", "ทำ PR", "สร้าง pull request", "commit แล้ว push
  แล้วเปิด PR", "เทสแล้วแปะรูปใน PR", or any combination of rename branch / test /
  commit / push / PR for the current change — even if they list only some of the steps.
---

# KMITL pull request flow

Run the steps in order. Each step's result feeds the next: the branch name is used for
the assets branch, and the test output and screenshots go into the PR body. If the user
lists only some steps, do just those and skip the others.

## วิธีเรียกใช้

Make the code change first, then call the skill from the same workspace:

| คำสั่ง | สิ่งที่ทำ |
| --- | --- |
| `/kmitl-pr` | ครบทุกขั้น: เปลี่ยนชื่อ branch → เทส + แคปรูป → commit/push → อัปรูป → เปิด PR |
| `/kmitl-pr ไม่ต้องเทส` | ข้ามขั้นที่ 2 (PR จะเขียนว่ายังไม่ได้เทส) |
| `/kmitl-pr ใช้ฐาน ok_uat-20260930` | ระบุฐานข้อมูลที่จะ clone มาเทส |
| `/kmitl-pr เทสหน้า <เมนู/รายงาน>` | บอกว่าจะให้เทสและแคปรูปหน้าไหน |
| "เทสแล้วแปะรูปใน PR" | ใช้กับ PR ที่เปิดไปแล้ว: ทำเฉพาะขั้นที่ 2, 4 แล้วเพิ่มผลด้วย `gh pr comment` |
| "commit แล้ว push แล้วเปิด PR" | ทำเฉพาะขั้นที่ 3–5 |

You can also say it in plain words, e.g. "เปิด PR ให้หน่อย". If the user doesn't name a
DB or a page to test, pick them from the change: the DB is the newest by the date in
its name (`scripts/pick_db.py`, see step 2), the page from the views/reports in the diff. State the choice in the PR.

`SK` = this skill's base directory (printed by the skill loader).
`T` = the odoo-real-db-test skill's `scripts` folder (`.agents/skills/odoo-real-db-test/scripts`).

## 1. Rename the branch

Pattern from CLAUDE.md: `16.0-{type}-{module_name}-{short-desc}`.
`type` is one of `imp` / `add` / `mig` / `fix`. Use the module that carries the main
change, plus a few kebab-case words describing it.

```bash
git branch -m 16.0-imp-purchase_request_kmitl-deputy-secretary
```

Rename only the local branch. If it was already pushed under the old name, tell the user
and ask before deleting the old remote branch.

## 2. Test on a sandbox DB and take screenshots

Load and follow the `odoo-real-db-test` skill. Here is what this machine needs, learned
from earlier runs:

- **Compose dir:** `export ODOO_COMPOSE_DIR=/Users/boat/Aginix/kmitl-odoo`. The
  script's default `~/Workspace/kmitl-odoo` does not exist here.
- **Pick a DB (when the user didn't name one): newest first.** Rank the DBs by the date
  in their name:
  ```bash
  $T/odoo_sandbox.sh dbs | $SK/scripts/pick_db.py
  # 2026-11-01  uat-01-11-26
  # 2026-10-15  pre-production-20261015
  # -           devel
  ```
  - The script reads `YYYYMMDD[HHMM]`, `YYYY-MM-DD`, `DD-MM-YYYY`, and `DD-MM-YY`
    (separators `-`, `_`, `.`).
  - It skips `cache-*`, `sbx_*`, and `postgres`.
  - On the same date it prefers `ok_uat` over `pre-production`.
  - Take the first line, then run a read-only `sql` check that the data you need is
    there. If it isn't, move to the next line.
  - Write the chosen DB and its date in the PR.
- **If only `devel` exists** (no dated UAT or prod copy), clone it, `install` the touched modules (demo data comes along), and create the test
  records yourself in an `odoo shell` script. Say in the PR that it ran on demo data.
- **Prove the server side** with a shell script that prints plain markers (`SEL ...`,
  `BODY: ...`). Keep the script in `.context/` so it can be re-run.
- **Reports:** render the template with `env["ir.qweb"]._render(...)`, strip the tags,
  and print the relevant part. Render it **twice**: once with no `lang` on `ir.qweb` and
  once with `th_TH`. Sarabun body fragments render without a language, so a selection
  shown via `t-field` comes out in English there. Odoo 16 translates selection labels
  with the *renderer's* env, not the record's.
- **UI screenshots:** if `node` is missing, use Python Playwright with the installed
  Chrome:
  ```bash
  python3 -m venv /tmp/pwvenv && /tmp/pwvenv/bin/pip -q install playwright
  # in the script: p.chromium.launch(channel="chrome", headless=True)
  ```
  - Log in at `/web/login`.
  - `pg.goto("about:blank")` before opening a `/web#model=...&id=...` URL, because a
    hash-only change does not reload the page.
  - Wait for `.o_form_view`. On a timeout, save a debug screenshot and look at it.
- **Common blocker:** on a demo DB the admin user may lack the analytic groups, and every
  form then fails with an access error. On the sandbox only, grant
  `analytic.group_analytic_accounting`, `account.group_account_readonly`, and
  `account.group_account_user`.
- **PDF:** download it with `pg.request.get("/report/pdf/<report_name>/<id>")`, then
  `sips -s format png file.pdf --out file.png` (page 1). macOS has no `pdftoppm`.
- **Look at every screenshot** with the Read tool before using it.
- **Clean up:** `$T/odoo_sandbox.sh stop sbx_<topic>`, `$T/odoo_sandbox.sh drop sbx_<topic>`,
  and `rm -rf /tmp/pwvenv`.

If testing shows a bug, fix it, re-run the check, and mention the fix in the PR.

## 3. Commit with `--no-verify` and push

- **Never** add `Co-Authored-By: Claude` or a "Generated with Claude Code" footer.
- Message format: `[TYPE] module_name: short description`, then a body explaining what
  changed and why.
- Stage only the module directories you changed. Never stage `.context/`.

```bash
git add <module dirs>
git commit --no-verify -q -F - <<'EOF'
[IMP] purchase_request_kmitl: add deputy secretary committee role

<why and what>
EOF
git push -u origin HEAD
git log -1 --format='%an%n%B'   # verify: no Claude lines
```

## 4. Upload screenshots

The repo is public. Images are hosted on an orphan branch `pr-assets/<branch>`, as in
PR #1677. The helper pushes it with git plumbing and does not touch the worktree:

```bash
$SK/scripts/push_pr_assets.sh "$(git branch --show-current)" .context/a.png .context/b.png
# prints raw.githubusercontent.com URLs
```

`gh` cannot upload images (there is no drag-and-drop API), so this branch is the only
way to get them into the PR. Never end with the screenshots only in `.context/`.

Push only screenshots of demo or test data. Real people's data from a prod or UAT copy
must not go to a public repo. If that is all you have, **don't skip the images
silently**: tell the user and ask whether to crop or blur them, re-shoot on demo
records, or leave them out.

If the PR already exists (for example, testing ran after it was opened), add the results
with `gh pr comment --body-file <file>`, or update the body with `gh pr edit
--body-file <file>`. If you run git
commands by hand in zsh, write `"${c}:refs/..."` with braces: `$c:r` is a zsh modifier
and corrupts the refspec.

## 5. Open the PR (Thai description)

- Title: `[16.0][TYPE] module_name: <Thai description>`
- Write the body to `.context/pr_body.md`, then:

```bash
gh pr create --base 16.0 --head "$(git branch --show-current)" \
  --title "[16.0][IMP] module: ..." --body-file .context/pr_body.md
```

Always pass `--head`. In a Conductor worktree the upstream is often not recorded, and
`gh` then aborts with "you must first push the current branch".

Body template (Thai):

```markdown
## สรุป
- <สิ่งที่เปลี่ยน ทีละข้อ ภาษาที่ผู้ใช้เข้าใจ>

### หมายเหตุทางเทคนิค
<เหตุผลของการออกแบบ / bug ที่เจอระหว่างเทสและวิธีแก้ (ถ้ามี)>

## ผลการทดสอบ (<ฐานข้อมูลที่ใช้ เช่น sandbox clone ของ `devel` + demo data>)
<ขั้นตอนที่ทำ>

```
<ผลลัพธ์จาก odoo shell ที่ยืนยันพฤติกรรม>
```

**<คำอธิบายรูป>**
![...](<raw url>)

ยังไม่ได้ทดสอบ: <สิ่งที่ยังไม่ครอบคลุม เช่น UAT/prod จริง>

## Deploy
`-u <modules ที่ต้อง upgrade>` (และ `-i` ถ้ามีโมดูลใหม่)

## ข้อสังเกต
<ผลกระทบข้างเคียงที่ reviewer ควรรู้ (ถ้ามี)>
```

After it opens, check that the images load
(`curl -sI <raw url> | head -1` → `200`). A link fetched before the push can stay cached
as 404 for a few minutes.

## Report back

Reply to the user in Thai. Include:

- the new branch name
- what was tested, on which DB, with the key output
- the screenshots embedded from `.context/`
- the commit and push result
- the PR URL
- anything not covered, and any leftovers (a server still running, a DB not dropped)
