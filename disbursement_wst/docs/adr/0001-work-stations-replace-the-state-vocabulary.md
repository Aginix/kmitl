# Work stations replace the shared state vocabulary

The disbursement request's pipeline is a fixed sequence in code: every step is a value
of a `fields.Selection` that core and every bridge module must extend (`selection_add`),
so core ends up naming states it does not own, and no module can be installed or removed
alone.

## Decision

After the head signs, the request walks a **route** of **work stations** (data, one
module per station) instead of advancing a state value. Core keeps a closed six-value
`state` for the slip's own lifecycle; the current station is `station_code`.
Authority is enforced at one gate, `disbursement.step.act()`.

## Considered options

- **Keep `selection_add` per module (rejected)** — the status quo; the cost above.
- **A sub-status beside the existing `state` (rejected elsewhere)** — purchase ADR-0005
  and ADR-0008 rejected this for the purchase request. That reasoning does not carry
  over: (a) the disbursement request never uses `states=` in views, only `attrs`, so
  there is no per-field readonly coupling to the status values; (b) this proposal
  *moves* the existing vocabulary out of core, it does not stack a second one on top.
- **`base_tier_validation` / `base_substate` (rejected)** — see disbursement ADR-0001;
  a substate is a label with no actor and no gate.

## Consequences

- A station is one small module; the engine knows none of them.
- `pipeline_status`, `display_status`, `approval_state`, the approver stamps and the
  signature model are gone from core; the signature snapshot lives on `disbursement.step`.
- Capability modules (billing, payment lines) keep their capabilities and lose their
  workflow ordering.
