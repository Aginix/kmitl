# Station ordering requirements are codes, not xmlids

An admin may reorder a route freely, which opens the door to an accounting-invalid
order (booking the payable before the budget is committed). Each station therefore
declares, in code, which stations it must follow.

## Decision

`requires_codes` is a comma-separated string of station **codes**, checked by a
constraint on the route. A required code that is not in the route — including a station
whose module is not installed — imposes nothing.

## Considered options

- **A many2many to the required stations by xmlid (rejected)** — the dependency has to
  resolve at install time, so station *n* would depend on station *n−1*: an eight-deep
  linear chain, and no station in the middle could ever be uninstalled.

## Consequences

- Stations never depend on each other; any may be removed and the rest still install.
- The check only sees stations that are in the route, so it protects order, not presence.
