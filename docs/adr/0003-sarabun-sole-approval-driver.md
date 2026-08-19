# Sarabun is the sole approval driver for พ.1 and พจ.1 — drop manual buttons and tier validation

All approvals in the phase-1 procurement flow — พ.1 "อนุมัติให้จัดหา" (หัวหน้าส่วนงาน) and พจ.1
"อนุมัติจัดซื้อ" — route **exclusively through Sarabun** document routing. Pressing "send to Sarabun"
moves the document to its *await-approval* state; Sarabun completion advances it. The three
competing approval drivers that currently mutate the same `state` — manual buttons
(`button_approved`/`button_validate`), `base_tier_validation` reviews, and Sarabun callbacks (which
already disable tier validation) — collapse to **one owner: Sarabun**.

A manual status button, limited to the "return for minor, non-material edits" case, is **deferred to
a later phase** and deliberately out of scope here.

## Considered options

- **Keep `base_tier_validation` for multi-tier in-system approval** — rejected: the organisation uses
  Sarabun as its real document-routing/approval system; running two mechanisms produces
  install-order (MRO) dependent behaviour and tangles the PA-family dependency graph.

## Consequences

- `base_tier_validation*` dependencies come off the พ.1/พจ.1 approval path (e.g. the
  `purchase_request_egp` → `purchase_request_tier_validation` edge). Work-Acceptance tier validation
  is a phase-2 concern, evaluated separately.
- The state machine gains a single, load-order-independent transition owner, removing the
  `super()`-chain fragility across `purchase_request_approval*`, `purchase_request_verify_state`, and
  `purchase_request_sarabun`.
