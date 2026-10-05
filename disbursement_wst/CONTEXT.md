# Disbursement Work Stations

The engine that walks a signed ใบขอเบิก (disbursement request) through the central
offices' work stations. Think of the request as a hospital **route slip**: it is
issued at the counter (the requester's side) and then travels between stations.

## Language

**Work Station** (สถานีงาน):
One central-office duty a request must pass — verification, an approval, billing,
a payment step. Declared by its own `disbursement_wst_<station>` module as one
`disbursement.station` record. Adding a station is installing a module; removing one is
uninstalling it, which is refused while the station still holds work.
_Avoid_: Stage, Status, Approval step.

**Route** (ใบนำทาง / เส้นทาง):
The ordered list of stations a request walks, an admin-editable template
(`disbursement.route` + `disbursement.route.line`). Seeded onto a request once,
when it is signed; later edits never touch a request already on its way.

**Step**:
One visit of one request to one station (`disbursement.step`): who may act, who did,
when, and the frozen signature snapshot. A step is **self-contained** — it carries its
own copy of the station's name and code, so it still reads correctly after the station
module that produced it has been uninstalled.

**Disposition**:
How a step ends, and why. **Forward** (ส่งต่อ) is the ordinary hand-off: this station's
work is done and the request goes to the next station on its route. **Divert** (ส่งไปยัง
สถานี) says something is wrong and names the station that must look at it — it is a
claim about the request, not about the route, so it is recorded separately and carries
a reason.

**Detour**:
A station a request visits because it was diverted there, not because the route said so.
The request's route is unchanged underneath; the diverting station chooses whether the
request comes back to it when the detour is done.

**Requirement** (`requires_codes`):
A station's declared "I must come after these stations", by **code**. A required
station that is absent from the route, or not installed, imposes nothing.

**Bridge** (สะพาน):
A module that owns the link between a request and a document in another app — the
columns, the one2many back, the lookups. It names no station and knows no route; a
station depends on a bridge, never the other way round.
_Avoid_: Capability module, integration.

**Station queue** (คิวงาน):
A list view of the requests whose `station_code` is that station's — a worklist is a
list view, not a screen of its own. Each station module adds its own menu entry under
**Work Queues**; **Proceed** on a selection runs `action_act_batch()`.

## Boundary

Stations start when the request reaches the central offices. The requester's side —
submit and the head-of-unit signature — stays core `state`, and is not a station.
