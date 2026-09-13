# Budget Ledger — Design Notes

Captured from the design session for `budget_ledger`. This is the "why", so the
next person (or future us) doesn't re-litigate the decisions. Glossary term:
`budget/CONTEXT.md` → **Budget Ledger**. Architecture decision:
`budget/docs/adr/0010-budget-ledger-separate-books.md`.

## Problem

Seeing overall budget movement meant opening `budget.move` / `budget.commitment`
records one at a time — no at-a-glance ledger.

## Mental model: separate books (accounting)

The system already keeps **separate books**, the way government budget
accounting does — this report does not change that:

| Book | Model | Records |
|------|-------|---------|
| สมุดบัญชีหลัก (main ledger) | `budget.move` | เงินจริง: จัดสรร / โอน / เบิกจ่าย |
| สมุดทะเบียนคุมเงินจอง/ผูกพัน (encumbrance register) | `budget.commitment` | จอง / ผูกพัน (earmark, not yet spent) |

**Phase 1 (this module) reads the main ledger only.** Reserve/obligate stay in
the register (a later book/phase). We explicitly rejected adding reserve/obligate
to `budget.move` — that would double-count (obligate/consume nest *under* reserve),
force move↔commitment dual-write, and ripple across ~54 files / 21+ modules in
production. See ADR-0010.

## Decisions

- **Grain** = `budget.move.line` (line level). A transfer document nets to 0 and
  hits many pools at once, so it must be split into per-line rows (โอนออก / รับโอน)
  for the ledger and the running balance to read correctly.
- **Kinds** (canonical terms, matching the glossary): **จัดสรร** (`appropriation`),
  **โอน** (`entry`, split by sign into รับโอน / โอนออก), **เบิกจ่าย** (`consume`).
  Deliberately *not* "รับเงิน" (collides with revenue budget / รับโอน).
- **Amount** = one signed column with +/− and colour — no debit/credit split
  (user preference).
- **Running balance** = งบปัจจุบัน − Σ เบิกจ่าย = *accounting remaining, before
  encumbrance*. This is **not** Remaining (f), which also nets เงินจอง held in the
  other book. A single book cannot produce (f) as a running figure — that would
  require interleaving the register (a future consolidated read-model, ADR-0010).
- **Summary bar** surfaces the real (f): reused verbatim from `budget.dashboard`
  (รายงานตรวจสอบงบประมาณ), so the netted-of-จอง figure is always exact even though
  the per-row running column is the accounting-only remaining.
- **State** = posted only (it is a ledger). Draft/review is an optional filter and
  is excluded from the running balance.
- **Tech** = custom OWL client action (running balance + rich ControlPanel can't be
  done in a native list; consistent with `budget_overview` / `budget_dashboard`).
- **Module** = new `budget_ledger` (depends `budget` only) — isolated, doesn't touch
  the production `budget` core.

## Layout

```
[summary bar: งบปัจจุบัน · จอง · เบิกจ่าย · คงเหลือ(f)]
▼ <เดือน> พ.ศ.                                     +เดบิตรวม  −เครดิตรวม
   <วันที่> [badge kind] <รหัสงบ ชื่อ>        <±จำนวน>   <คงเหลือสะสม> ▸
      chips: ส่วนงาน · แหล่งเงิน · กองทุน · กิจกรรม · โครงการ · จัดซื้อ
      (รับโอน → "← รับโอนจาก: <ต้นทาง>"  /  โอนออก → "→ โอนไป: <ปลายทาง>")
      ▾ expand: เลขที่ใบ · อ้างอิง · หมายเหตุ · เอกสารต้นทาง
```

Dimensions are shown inline (chips), not hidden behind expand — a dimension that
is filtered to a single value hides its own chip. Expand is only for
audit detail (เลขที่ใบ / เอกสารต้นทาง / หมายเหตุ).

## Implementation notes / gotchas

- **Transfer counterparty** ("รับโอนจาก / โอนไป"): `budget.move` has no
  `transfer_id`. We resolve the opposite-side department by scanning *all* lines
  of the same transfer move (`budget.ledger._transfer_counterparties`), reading the
  whole move so it still resolves when a dimension filter hides the opposite leg.
  If a stronger link is ever needed, add `transfer_id` to `budget.move`.
- **Consume source document**: taken from `move.commitment_line_id.res_model/res_id`
  (the consume move is auto-created from the commitment line, which carries the
  source doc).
- **OU**: reads go through the ORM only → `budget_operating_unit` `ir.rule` applies
  automatically. Never switch to raw SQL without re-adding the OU filter.
- **Summary bar scope**: `budget.dashboard` understands four dimensions
  (dept/source/fund/activity) + a single root account. Project / procurement-plan
  filters and multi-account selections narrow the *timeline* but leave the summary
  bar a best-effort context snapshot.
- **Performance**: the running balance needs the whole filtered scope in date
  order, so it's computed server-side (one `search` + Python loop) rather than
  paginated. A fiscal-year + filters scope keeps this bounded in practice.

## Post-review refinements

After the first UAT:
- **Expense-only** — revenue budget is out of scope; the budget-type toggle was
  removed and the backend forces `expense`.
- **Dimension chips** show `[code] complete_name` — code + full hierarchy, not just
  the leaf (mirrors the analytic account's standard name_get).
- **Record time** — `date` is a `fields.Date` (no time), so each row also surfaces
  the `create_date` clock time (user tz): when the entry was recorded.
- **Excel export** (`report_xlsx`) — `budget.ledger.action_export_xlsx(fy, options)`
  renders the on-screen scope to XLSX through a throwaway carrier wizard
  (`budget.ledger.export.wizard`); filters travel in the report `data` (WYSIWYG).

## Not done (future phases)

- The encumbrance-register book (จอง / ผูกพัน over `budget.commitment`).
- A consolidated read-model (`budget.ledger.line` as an `_auto=False` SQL view)
  interleaving both books into one running-available timeline — **if** ever needed,
  build it there, never by editing `budget.move` (ADR-0010).
