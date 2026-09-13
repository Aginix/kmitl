# Budget Ledger reads separate books; reserve/obligate stay off `budget.move`

## Context

KMITL needs a **budget movement report** (รายงานความเคลื่อนไหวทางบัญชีงบประมาณ). Today, seeing
overall activity means opening `budget.move` / `budget.commitment` records one at a
time — there is no at-a-glance ledger. While designing it we asked whether `budget.move`
should be extended to carry reserve/obligate too — i.e. promote `budget.commitment.line`
rows into `budget.move.line` — so every kind of activity lives in one book.

## Decision

**No — keep separate books; do not add reserve/obligate to `budget.move`.** The system
already models two books the way government budget accounting does:

- `budget.move` = **main ledger** (บัญชีแยกประเภทงบ) — actual money moving: appropriation /
  transfer / disbursement (carries debit/credit/balance).
- `budget.commitment` = **encumbrance register** (สมุดทะเบียนคุมเงินจอง/ผูกพัน) — reservation /
  obligation; money only *earmarked*, not yet spent.

The Budget Ledger report is a **read-only view over these books, opened per book**, starting
with the main ledger (`budget.move`). Reserve/obligate are reported from the register, never
merged into the main ledger.

## Considered options

- **Denormalize reserve/obligate into `budget.move` (promote commitment lines to move lines)**
  — *rejected.*
  1. **Double-count via nesting**: locked = `reserved` only, with obligate/consume a waterfall
     *under* reserve (ADR-0001, ADR-0005). Flattening reserve+obligate into one `balance` column
     breaks any running total.
  2. **Dual-write**: the commitment must still exist for its cap + workflow + invariants
     (`cap ≥ reserved ≥ obligated ≥ consumed`, cross-charge, return-leftover, carry-over), so
     move↔commitment would need constant syncing.
  3. **Blast radius**: `budget.commitment` is referenced by ~54 files across 21+ modules
     (procurement_plan, kmitl_project, disbursement, agx_approval, purchase_*_budget) and KMITL
     is in production — this is a domain migration, not a report.
- **Consolidated read-model** (`budget.ledger.line` as a `_auto=False` SQL view UNION-ing both
  books) — *viable, deferred.* Gives one merged timeline without touching the domain (CQRS:
  read model ≠ write model). If a single interleaved stream is ever wanted, build it **here** —
  never by changing `budget.move`. It must still resolve the consume double-count (consume
  appears in both books: as a commitment line **and** as its auto-created mirror `budget.move`)
  by taking consume from one side only.
- **Separate books, per-book report** — *chosen.* Matches encumbrance accounting, keeps each
  book's running balance meaningful (main = งบคงเหลือ; register = ยอดจอง/ผูกพันคงเหลือ), avoids
  nesting math, touches no domain code.

## Consequences

- Phase 1 = a movement report over the **main ledger** (`budget.move`) only: จัดสรร / โอน /
  เบิกจ่าย, filtered by fiscal year + the six dimensions, with a running งบคงเหลือ. It will
  **not** show reserve/obligate — those live in the register (a later book/phase).
- `budget.move.move_type` deliberately stays `{appropriation, entry, consume}`; there is no
  `reserve`/`obligate` move type.
- **Revisit trigger**: if users need one interleaved timeline of actual + encumbrance, build the
  consolidated read-model above. This ADR is the pointer back to *why* it must not be done by
  editing `budget.move`.
