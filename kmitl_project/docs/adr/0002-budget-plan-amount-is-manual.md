# Project Budget Plan line `amount` is entered manually, not computed

A **Budget Item** (`project.budget.item`) carries a standard `unit` (หน่วยนับ) and
`unit_price` (ราคาต่อหน่วย). A **Project Budget Plan** line (`project.budget.line`)
shows those two as **read-only reference** (related from the chosen item) and keeps
its `amount` (จำนวนเงิน) as a **plain, manually entered** figure. There is
deliberately **no `quantity` field and no `amount = quantity × unit_price`
computation**. The breakdown (แตกตัวคูณ) is written free-form in the line's
`description`.

## Why

- The real breakdowns are frequently **multi-factor** — e.g. `50 คน × 200 บาท × 3 วัน`.
  A single `quantity × unit_price` (two factors) cannot express them, so forcing a
  computed amount would push users to fudge the quantity. Free-text `description`
  captures any number of factors.
- `unit` / `unit_price` are still worth showing as the item's **standard rate**
  reference while the planner types the amount — informational, not authoritative.
- Chosen explicitly as the "start flexible first" option over the computed
  alternative; the computed path was considered and deferred.

## Consequences

- Seeing both `unit_price` and a manual `amount` **looks like a missing
  multiplication** — it is not. Do **not** wire `amount` to `unit_price`; that would
  break the multi-factor breakdown and silently overwrite existing manual figures.
- If structured computation is wanted later, it is an additive change: introduce a
  `quantity` field and an opt-in computed `amount`, then migrate existing manual
  amounts. This record exists so that future change is a conscious one.
- The plan is for internal management only and is **not** reconciled against the
  project's reserved **Project Budget** (`budget_amount`) or the `budget` engine
  (see CONTEXT.md » Project Budget Plan).
