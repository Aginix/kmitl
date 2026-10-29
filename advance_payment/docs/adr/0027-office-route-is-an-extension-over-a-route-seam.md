# Office approval route is an extension over a core route seam

Status: proposed

KMITL has two approval routes. Faculties/colleges (the **Standard route**) go
`draft → to_endorse → to_verify → to_director → to_approve → approved`; offices under
the Rector's Office (the **Office route**) skip the supervisor's Endorse:
`draft → to_verify → to_director → to_approve → approved`, and the director's signature
fills the contract's เสนอ block instead. We keep the Standard route as the only route core
`advance_payment` knows, and add one seam — `_get_route_states()`, the ordered list of
pre-disbursement states every workflow button advances through instead of hard-coding its
target. The Office route lives in a separate module that owns its Settings (which
operating units use it, stored on `res.company`), snapshots the route onto the request at
submit, overrides the seam to drop `to_endorse`, and overrides `_contract_signatures()`
for the เสนอ block.

## Considered Options

- **Route setting in core** (a per-OU or per-loan-type flag in `advance_payment`) —
  rejected: the user explicitly wants the core free of route configuration, and the Office
  route is KMITL-organisational, not part of the generic loan lifecycle.
- **Separate state machines per route** — rejected: both routes share every state; only
  one step is skipped, so a filtered list of the same states is enough.
- **Recompute the route live from the OU** — rejected: a settings change would re-route
  in-flight requests and strand To-Dos; the route is snapshotted at submit.
