# The head signature is not a station

## Decision

Stations begin when the request arrives at the central offices. Submitting and the
head-of-unit signature belong to the requester's side and remain core `state`
(`draft → submitted → signed`); signing seeds the route and enters the first station.

## Considered options

- **Make the head signature the first station (rejected)** — the head acts for the
  requesting unit, not for a central office, and is already routed through e-Saraban
  (`disbursement_sarabun` drives `action_sign`). Folding it in would couple the engine
  to the correspondence system.

## Consequences

- With no station module installed, a signed request stops at `signed`: nobody picks
  it up, which is honest.
- `disbursement_sarabun` is unaffected.
