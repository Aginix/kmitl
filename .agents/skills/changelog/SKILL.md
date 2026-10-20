---
name: changelog
description:
  Write the KMITL release changelog (สรุป changelog / release notes / มีอะไรใหม่) for a
  commit range into docs/changelog/<พ.ศ.-date>.md — a plain-Thai section for end users
  plus an admin section with deploy steps (new modules needing -i, migrations, version
  bumps). Use whenever the user asks to summarise changes "ตั้งแต่ commit X", what
  changed since the last deploy, release notes, a changelog to publish/announce to
  users, or an HTML version of one — even if they don't say "changelog".
---

# KMITL changelog

Turns a range of commits on this repo into one changelog file that serves two readers:
**end users** (what changed in their daily work, in plain Thai) and **the people
deploying** (what to install, migrate and check). The rules live in
`docs/changelog/README.md` — read it first; if it disagrees with this skill, the README
wins (the team edits it).

## 1. Pin down the range

- "ตั้งแต่ commit X" **includes X** (`X^..HEAD`). The user corrected this once — they
  expect the named commit in the list. Say which range you used.
- No range given → open the newest file in `docs/changelog/`, take the end of the last
  range in its `## สำหรับผู้ดูแลระบบ` section, and continue from the commit after it
  (exclusive). Confirm with the user if it's ambiguous.
- `<to>` defaults to `HEAD`; diff against `origin/16.0` only if asked.

## 2. Collect the facts

```bash
python3 .agents/skills/changelog/scripts/collect.py <from> [<to>] [--exclusive]
```

It prints commits with PR numbers and touched modules, version bumps, new modules (with
`auto_install` and `depends`), changed-but-unbumped modules, added migrations and added
ADR/README files.

That gives the _what_, not the _why_. For each commit, read enough to describe the
user-visible effect: the commit's ADR / README.rst / CONTEXT.md changes first (they
state intent in prose), then `git show <sha>` on models and views when the docs are
thin. Read diffs yourself or hand them to subagents in parallel for big ranges — but
verify any claim that ends up in the admin section against the code.

## 3. Write the user section

This is the part that gets published, so write for an officer who uses Odoo daily and
has never seen the code.

- **Group by the user's area of work, not by module.** Bridges go under the feature a
  user would look for. A guide:

  | modules                                            | หัวข้อ                                 |
  | -------------------------------------------------- | -------------------------------------- |
  | `budget*`, `budget_transfer*`                      | 💰 งบประมาณ                            |
  | `kmitl_project*`, `kris_project*`                  | 📁 โครงการ/กิจกรรม                     |
  | `procurement_plan*`                                | 🛒 แผนจัดซื้อจัดจ้าง                   |
  | `purchase_request*`, `purchase_*`, `agx_approval*` | 📝 ใบขอซื้อขอจ้าง (พ.1) และคำขออนุมัติ |
  | `agx_sarabun*`                                     | 📨 สารบรรณ                             |
  | `disbursement*`, `advance_payment*`                | 💸 เบิกจ่ายและยืมเงิน                  |
  | `receipt_kmitl*`, `account_*`                      | 🧾 การเงินและบัญชี                     |
  | `stock_*`, `hr_*`, `web_*`/`theme_*`               | 📦 พัสดุ / 👥 บุคลากร / 🖥️ หน้าตาระบบ  |

- One `###` per item, prefixed **ใหม่ — / ปรับปรุง — / แก้ไข —** (from the commit's ADD
  / IMP / FIX, but judge by effect: an IMP that only fixes wrong numbers is แก้ไข).
- Say what the user can now do or see, using on-screen labels in bold (ปุ่ม
  **"การเคลื่อนไหวงบ"**, รายงาน **ตรวจสอบงบประมาณ**). No module, field, model, group or
  state names, no PR/ADR numbers, no commit hashes.
- Collapse internals. "แก้ bug การคำนวณ 4 จุด (H1/H2/H3/Case B)" becomes
  "การคำนวณงบคงเหลือแม่นยำขึ้น ป้องกันการจองเกินงบ". A changed rule that may surface a
  **new error** for users stays in, phrased as the rule ("ระบบจะไม่อนุญาตให้…") — it
  saves support calls.
- Leave out what no user notices: tests, refactors, i18n, demo data,
  `kmitl_depends_dev`, docs-only commits, dev hooks.

## 4. Write the admin section

Below a `---`, under `## สำหรับผู้ดูแลระบบ`, one `### รอบที่ N` per deploy with the
commit range and PR list, then only the subsections that apply:

- **ก่อน deploy** — data checks or scans a migration asks for, and changes that alter
  existing figures. Read each added `migrations/**` file to see whether it fixes data or
  only logs.
- **ติดตั้ง module ใหม่ด้วย `-i`** — every new module. `-u` never installs a new module,
  even `auto_install` ones. Note `auto_install` per module, and flag a non-auto_install
  module that others depend on: without it the dependants (and their feature) never
  appear.
- **เวอร์ชันที่เปลี่ยน (`-u`)** — the bump table, plus modules changed without a bump
  that still need `-u` (views/JS).

## 5. Save the file

- Path: `docs/changelog/<YYYY-MM-DD in พ.ศ.>.md` (CE + 543), dated by the deploy day,
  default today. Title `# มีอะไรใหม่ — <D> <เดือนไทย> <พ.ศ.>`.
- File already exists for that day → it's another deploy round: merge the new user items
  into the existing areas and add `### รอบที่ N+1`. If the new round reverts or corrects
  something already announced, edit the original text instead of appending — readers
  must not see contradictions.
- Don't commit unless asked. If asked, branch per CLAUDE.md
  (`16.0-add-...`/`16.0-imp-...`).

## 6. HTML (only when asked)

Fill `assets/changelog.html` from the **user section only** (never the admin section —
it's for publishing), save to `.context/changelog.html`, and `open` it. Tag classes:
`add`=ใหม่, `imp`=ปรับปรุง, `fix`=แก้ไข.

## 7. Report back

Tell the user the range used, the file path, and anything to verify before publishing —
especially features that live in a module that is not `auto_install` (users won't see
them unless it's installed on prod), and new user-facing errors from tightened rules.
