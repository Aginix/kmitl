# พ.1 gains a ธุรการ review step; each module owns the state it writes

Before this ADR, พ.1 (`purchase.request`) ran `draft → to_verify (รอจองงบ) →
to_submit (จองแล้ว รอส่งหนังสือ) → to_approve (หนังสือเดินอยู่) →
in_egp / in_approval`. `to_verify → to_submit` was driven by
`action_reserve_budget` calling a `button_to_submit()` defined in
`purchase_request_kmitl` purely for `purchase_request_budget` to call;
`to_submit → to_approve` was driven by the Sarabun circulating callback.

Two problems fell out of that shape:

- There was no ธุรการ (clerical) review step before a request reached the
  budget officer — every request went straight from the requester to
  whoever holds `budget.group_budget_commitment`.
- `to_approve` was misleading: the label says "awaiting approval" but the
  real meaning was "a Sarabun document is circulating for signature" — and
  `purchase_request_budget` had silently redefined `_compute_to_approve_allowed`
  to gate on `state == "to_submit"`, so any bridge module that called
  `button_to_approve()` right after reserving budget (`kmitl_project_purchase_request`,
  `purchase_request_procurement_plan`) hit `to_approve_allowed_check()`'s
  "purchase request which is empty" error — both bridges were broken on
  `16.0` before this ADR.

**Decision.** Shift every state's meaning one step later and let the module
that writes a state also own its `selection_add` entry, instead of
`purchase_request_kmitl` declaring every state up front and downstream
modules silently repurposing them:

| Old | Meaning | New | Owner |
|---|---|---|---|
| — | ธุรการตรวจ | `to_verify` | `purchase_request_kmitl` |
| `to_verify` | รอจองงบประมาณ | `to_verify_budget` | `purchase_request_budget` |
| `to_submit` | จองแล้ว รอสร้างหนังสือ | `to_approve` | base (`purchase_request_kmitl`) |
| `to_approve` | หนังสือเดินอยู่ | `sent` | `purchase_request_sarabun` |

Full chain: `draft → to_verify → to_verify_budget → to_approve → sent →
in_egp / in_approval / approved`. `in_egp` / `in_approval` and the
`_transition_after_sarabun_approve` dispatcher ([ADR-0005]) are unchanged —
they still fire off whatever state Sarabun completion lands on, which is
now `sent` instead of `to_approve`.

The old `to_verify → to_submit` transition is now `purchase_request_budget`
overriding the base's own `button_to_approve()`: when a record is still at
`to_verify` (the ธุรการ's own ส่งต่อ click), the override diverts it to
`to_verify_budget` instead of letting the base write `to_approve`; when the
record is already at `to_verify_budget` (the budget officer's
`action_reserve_budget` calling `button_to_approve()` after reserving),
the override's filter is empty and it falls through to the base write,
which is exactly where `_compute_to_approve_allowed` was recentered — the
same fix that unblocks the two previously-broken bridges.

`to_submit` is retired outright rather than kept as an unused alias:
`button_to_submit()` is deleted, and its `selection_add`/`ondelete` entries
are dropped from `purchase_request_kmitl` (see Consequences for the
migration-ordering hazard that creates).

## Considered options

- **Add a sub-status field alongside the existing states** — rejected, same
  reasoning as [ADR-0005]: every state-gated compute (`is_editable`,
  `is_budget_editable`, `hide_reserve_budget_button`, `to_approve_allowed`,
  `can_reset_to_draft`) would branch on `state + sub_status` instead of
  `state` alone, and the button-visibility `states=` attrs in views can't
  express a sub-status at all without duplicating the whole view.
- **Keep `purchase_request_kmitl` as the sole owner of the full selection
  list** — rejected. That's what produced the `to_submit` collision in the
  first place: `purchase_request_budget` needed a budget-officer-only phase
  and had no state of its own to put it in, so it repurposed `to_verify`'s
  gate condition instead. Letting each module `selection_add` the state it
  actually writes keeps the gate condition and the state declaration in the
  same file.
- **Rename `to_verify`/`to_submit`/`to_approve` in place instead of
  reassigning meaning** — rejected. These values are referenced by view
  `states=` attrs, dashboard state lists, and Todo scheduling across seven
  modules; a bare rename requires the exact same fan-out as reassigning
  meaning, but reassigning meaning additionally lets the ธุรการ step reuse
  `to_verify`'s existing exception-check plumbing (`button_to_verify` →
  `detect_exceptions()`) instead of inventing a fifth state.

## Consequences

- **`ondelete` on the retired `to_submit` key must be dropped, not just the
  `selection_add` entry, and the SQL data move must run before `-u`.** On
  upgrade, Odoo removes the `ir_model_fields_selection` row for `to_submit`
  via `ir.model.data._process_end`, whose `unlink()` triggers
  `_process_ondelete`. If the `ondelete={"to_submit": "set default"}` key
  is still present, any row still holding the string `'to_submit'` gets
  written to `state`'s field default — `draft` — silently, mid-upgrade,
  through the full `write()` MRO including mail tracking. Dropping the key
  without first moving the data instead leaves those rows stuck on a string
  absent from every selection (blank statusbar, `state in (...)` checks
  quietly false). The only safe order is: SQL-migrate existing rows off
  `to_submit`/`to_verify`/`to_approve` by hand (see the workflow's
  implementation notes), *then* upgrade with the key already gone.
- **`purchase_request_todo`'s per-transition Todo scheduling collapses onto
  one override.** `button_to_submit()` no longer exists to hang a hook off
  of, so the จองงบประมาณ and สร้างหนังสือ Todos — previously raised in
  `button_to_verify()` and `button_to_submit()` respectively — now both
  raise from a single `button_to_approve()` override, disambiguated by
  which state the record actually landed on (`to_verify_budget` vs
  `to_approve`) rather than by which method ran.
- **`purchase_request_approval`'s ตีกลับ/แก้ไข ([ADR-0007]) now returns the
  PR to `to_verify`, not `to_submit`.** A returned request re-enters at the
  ธุรการ step and must walk ธุรการ → จองงบ → to_approve again before a new
  หนังสือ can be created. Reserving is the *only* way forward out of
  `to_verify_budget`, and a return leaves the previous commitment live, so
  `action_reserve_budget`'s reserve-new branch now short-circuits on a live
  `budget_commitment_id`: it logs to the chatter and advances, instead of
  minting a second slip and orphaning the first one still eating budget.
  (Cancelled/draft commitments are untouched — they still take the
  `_reuse_cancelled_commitment` path.)
- **Downstream bridges that reserve on their own source's commitment**
  (`kmitl_project_purchase_request`, `purchase_request_procurement_plan`)
  swap their `button_to_submit()` call for `button_to_approve()`. They make
  the call right after writing `budget_commitment_id`, which happens while
  the record sits at `to_verify_budget`, exactly where the relocated
  `_compute_to_approve_allowed` now expects them — so the one-line swap is
  the whole change, and it also unblocks the two bridges that ADR-0006 left
  raising "purchase request which is empty".
- **`purchase_request_verify_state` is retired.** Its `to_examine` was an
  opt-in (config-parameter gated) review step for the procurement officer
  sitting between `draft` and `to_verify` — exactly the slot the ธุรการ step
  now occupies unconditionally, so keeping both meant two review states with
  one purpose. The module's directory is deleted and the same
  `purchase_request_kmitl` pre-migration purges it: rows still at
  `to_examine` are moved to `to_verify` (both mean "submitted, awaiting a
  reviewer"). The move has to be explicit — the module's
  `ondelete={'to_examine': 'set default'}` cannot fire, because
  `_process_ondelete` reads `ondelete` off the field in the *registry*, which
  no longer declares the value at all.
- **Statusbar order and statusbar visibility are two different mechanisms, and
  each module owns its own entry in both.** `statusbar_visible` is a *set*, not
  an order: the widget uses it to filter the field's `selection`, so what the
  user sees is ordered by the selection, and a value listed but absent from the
  selection is silently dropped. Each module therefore appends its own state
  with `<attribute name="statusbar_visible" add="..." separator=","/>` instead
  of one central list — order-independent, so it does not matter which view is
  applied first. `purchase_request_kmitl` adds `to_verify` and removes OCA's
  `approved` (the KMITL flow skips it); `purchase_request_budget` adds
  `to_verify_budget`; `purchase_request_sarabun` adds `sent`.
- **Order is pinned by `selection_add` anchors, and the anchor must be the
  value that would otherwise slip in front.** `merge_sequences` is a
  topological sort whose only constraints are the adjacent pairs of each
  `selection_add` list, so a bare `("x",)` tuple is an ordering anchor. Anchor
  a new state on *both* sides. `("to_approve",), ("sent", …), ("in_progress",)`
  looked right but let OCA's `approved` — which already sits between
  `to_approve` and `in_progress` — and both branch states slip in front of
  `sent`; the anchor has to be `("approved",)`. `purchase_request_egp` cannot
  anchor `in_egp` behind `sent` because it does not depend on
  `purchase_request_sarabun`, and anchoring on a value the module does not know
  raises `KeyError` while the field is built, so `purchase_request_approval` —
  the only module depending on both branches — pins
  `sent < in_egp < in_approval < approved` for both.
- **The e-GP dual statusbar is collapsed into one.** The two bars differed only
  in `in_egp` vs `in_approval`, i.e. the branch a given พ.1 takes, which is why
  neither can sit in a shared list. Both are left out of `statusbar_visible`
  entirely and surface through the widget's "the current value is always shown"
  rule, so each appears exactly while the request is in it. Two bars would have
  meant every module appending its state twice — they had already drifted
  (`to_verify_budget` present in one, missing from the other). Accepted cost: a
  request at `in_progress`/`done` no longer shows the branch step it passed
  through.

[ADR-0005]: 0005-post-sarabun-state-split.md
[ADR-0007]: 0007-pa-return-for-revision.md
