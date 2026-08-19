# Routing targets are personnel (hr.employee), resolved to a user for acting

Refines ADR-0003. The routing targets — a Position's holders, a Person (บุคลากร) step, and a ธุรการหน่วยงาน (unit clerk) — are configured as **`hr.employee`** so e-Saraban binds to HR personnel data rather than raw login accounts. The engine still acts by the logged-in user, so at step activation each target employee is resolved to its **linked `res.users`** (via `employee.user_id`) and that user-set is snapshotted onto the step.

## Consequences

- A person can only *act* on a step if their `hr.employee` has a linked user account; personnel without a user may be configured and previewed as holders but never become actors (the step would resolve to an empty actor set).
- Non-HR sarabun users need read access to `hr.employee` to pick and display personnel targets — granted via an ACL; field-level groups still protect private HR fields.
