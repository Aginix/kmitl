# A plan reserves the budget it received, not its Plan Amount

The plan's reservation is sized to its **Plan Budget** (`budget_amount`, the net posted budget at the plan's own dimension) instead of its **Plan Amount** (`total_price`, วงเงินตามแผน). Reserving the ask let a plan earmark money it had never been given, and left the reservation stale when the money actually received differed. This follows KMITL Project (kmitl_project ADR-0006/0010), where the reservation is always the received amount. Decision D3 of the 2026-10-24 review.

## Consequences

- Verify reserves only once Plan Budget ≥ Plan Amount, and then reserves the whole Plan Budget. **Amended 2026-10-30:** an under-funded plan cannot be reserved at all — not even by a budget user — until it has received its full Plan Amount; the form says how much is still missing.
- Later transfers into the plan's dimension top the reservation up through the existing pool-owner commitment lookup.
- Plan Amount and Plan Budget are two quantities shown side by side and never reconciled automatically.
- Production: reservations already made at the old (Plan Amount) size are left as they are; only new plans follow this rule.
