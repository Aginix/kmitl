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
  หนังสือ can be created; `action_reserve_budget` will find the previous
  commitment still live, since a return does not cancel it.
- **Downstream bridges that call `button_to_approve()` directly**
  (`kmitl_project_purchase_request`, `purchase_request_procurement_plan`)
  needed no code change — they already call it right after writing
  `budget_commitment_id`, which happens while the record sits at
  `to_verify_budget`, exactly where the relocated
  `_compute_to_approve_allowed` now expects them.
- **`statusbar_visible` is maintained as one list on `purchase_request_kmitl`'s
  view** rather than three modules each appending their own state. A widget
  silently drops any value in the list that isn't in the field's current
  selection, so this is safe even though `to_verify_budget` and `sent` are
  declared by other modules — same pattern the repo already used for the
  pre-existing list.

[ADR-0005]: 0005-post-sarabun-state-split.md
[ADR-0007]: 0007-pa-return-for-revision.md
