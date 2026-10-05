# Disbursement Work Stations

The engine that walks a signed ใบขอเบิก (disbursement request) through the central
offices' work stations. Think of the request as a hospital **route slip**: it is
issued at the counter (the requester's side) and then travels between stations.

## Language

**Work Station** (สถานีงาน):
One central-office duty a request must pass — verification, an approval, billing,
a payment step. Declared by its own `disbursement_wst_<station>` module as one
`disbursement.station` record. Adding a station is installing a module; removing
one is uninstalling it.
_Avoid_: Stage, Status, Approval step.

**Route** (ใบนำทาง / เส้นทาง):
The ordered list of stations a request walks, an admin-editable template
(`disbursement.route` + `disbursement.route.line`). Seeded onto a request once,
when it is signed; later edits never touch a request already on its way.

**Step**:
One visit of one request to one station (`disbursement.step`): who may act, who did,
when, and the frozen signature snapshot. Superseded rounds are archived, not deleted.

**Disposition**:
How a step ends — `complete` (proceed to the next station) or `return` (archive the
round and walk the route again, `attempt_seq` + 1).

**Requirement** (`requires_codes`):
A station's declared "I must come after these stations", by **code**. A required
station that is absent from the route, or not installed, imposes nothing.

**Station queue** (คิวงาน):
A list view of the requests whose `station_code` is that station's — a worklist is a
list view, not a screen of its own. Each station module adds its own menu entry under
**Work Queues**; **Proceed** on a selection runs `action_act_batch()`.

## Boundary

Stations start when the request reaches the central offices. The requester's side —
submit and the head-of-unit signature — stays core `state`, and is not a station.
