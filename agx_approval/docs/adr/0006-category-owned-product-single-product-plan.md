# ADR-0006: Category-owned product; single-product plans collapse to a bare amount

## Status

Accepted

## Context

An `approval.request.line` (ค่าใช้จ่าย) forced the requester to pick a
`product_id` from the category's `allowed_product_ids` (M2M). User testing
found this wrong: a request is filled **one expense type at a time**, and for
the overwhelming majority of the ~90 fine-grained expense types the product is
a foregone conclusion — the category itself names the expense type, so making
the user pick it again on the line is redundant friction. Only a handful of
travel/training categories (5 of them) legitimately let the user choose among
a small set of sub-items (ค่าหลักสูตร/ค่าเดินทาง/ค่าเบี้ยเลี้ยง/ค่าที่พัก/อื่นๆ).

The old seed also mis-modelled this: `approval.category` was a broad *request
kind* (travel, honorarium, ...) with many allowed products bundled under one
name, not a one-to-one mapping to the government's per-code expense chart.

## Decision

- `approval.category` now owns its product: a boolean `multi_product` flag
  (default off) plus the existing `allowed_product_ids` M2M — reused rather
  than adding a `default_product_id` field. Off means exactly one product is
  required; on means at least two.
- Single-product categories drop the line table entirely: the plan page shows
  a bare `plan_amount` (Monetary) + `plan_description` (Text) pair on the
  header, mirrored behind the scenes onto a single `approval.request.line`
  (product = the category's sole product). `line_ids` stays the one source of
  truth everywhere it already was consumed (budget reserve, total amount,
  plan/actual comparison) — the header fields are a compute+inverse UI
  convenience over it, not a parallel store.
- Multi-product categories (the 5 travel/training types) are unchanged: the
  line table with its product picker stays, scoped to that category's
  children via the existing `allowed_product_ids` domain.
- The seed data was rewritten from ~40 broad "request kind" categories to
  ~130 fine-grained ones (one per government expense code, plus the 5
  multi-product parents), grouped under 5 หมวด (compensation / expense /
  utility / support / other) instead of the old 10 request-kind groups.

## Consequences

- A single-product request needs zero product knowledge from the user beyond
  picking the (already specific) category — faster entry, fewer mis-picks.
- The 5 multi-product categories keep their existing UX unchanged.
- The category catalogue is now ~3x larger and per-code; adding a new
  government expense code means adding one category record, not editing an
  M2M on a broad bucket.
- Four codes from the source taxonomy (5101020128, 5101020129, 5104010221,
  5104020009) have no matching `budget.account`/`product.product` in this
  repo and were dropped from the seed rather than crash on an empty
  `allowed_product_ids` (the new constraint requires exactly one product for
  a single-product category). They can be added once their budget accounts
  exist.
- Demo data (`kmitl_demo/data/approval.request.xml`) was repointed to the new
  per-code xmlids; a few multi-line demo requests that mixed several products
  under one category were collapsed to their first line, since a
  single-product category now allows exactly one.

## Alternatives considered

- **`default_product_id` field instead of reusing `allowed_product_ids`**:
  rejected — would need two fields to express the same "which product(s) can
  this category use" concept, and the picker's existing domain
  (`allowed_product_ids`) would need to special-case the single/multi split
  anyway.
- **Reduce every category to exactly one product, drop `multi_product`
  entirely**: rejected — the 5 travel/training types genuinely need a
  sub-item pick-list (ค่าเดินทาง vs ค่าที่พัก vs ค่าเบี้ยเลี้ยง etc. differ
  trip to trip), so collapsing them to a single line would lose real
  information the plan/actual comparison depends on.
