# Pools never nest; a reservation may draw at any descendant of the funded code

Once money is appropriated (จัดสรร) at a node, a reservation (จอง) may name **any descendant of it on every axis** — budget account and the hierarchical analytic dimensions (ส่วนงาน / กิจกรรม / กองทุน). Appropriated at `090070101` (กิจกรรมหลัก) → reserve at `09007010110` (กิจกรรมรอง) or deeper. This was always the documented intent (Control Node, ADR-0005/0006); the engine walked up each axis but the reservation picker could only list codes that already had facts, so a descendant with no entries of its own had no row to pick.

The change makes the descendant draw reachable **and** closes four correctness gaps that opening descendants would otherwise make easy to hit, by establishing one invariant: **budget pools never nest (กองงบไม่ซ้อน)**.

## The invariant

A **pool** is one coordinate — a budget account plus every controlled dimension value (`_DIM_COLUMNS`) — whose net posted appropriation+entry is not zero (company-currency rounding), per company × fiscal year, expense only. Two coordinates **conflict** when they are comparable on **every** axis (equal, or one an ancestor of the other; `False` only equals `False`) and are not identical. The guard (`budget.controller._check_pool_nesting`) forbids a posting that would leave two conflicting pools; it runs when appropriations and transfers post. A transfer's FROM and TO lines must therefore sit on a pool's own coordinate, or on a coordinate that overlaps no pool.

With the invariant in place, at most one funded coordinate ever covers a reservation, so the control-node resolver is one grouped `read_group` (account + used dims ∈ self-and-ancestors, unused dims pinned `False`) that keeps the non-zero group. Zero groups → uncovered → 0 available.

## The four correctness gaps closed

- **H1 (downward leak, pre-existing).** When nothing funded a node at/above the reservation, the old resolver defaulted to the reservation's own node and summed every pool *below* it (a pool at a child, 100k, was seen in full by both parent and child → 200k reserved against 100k). Now an uncovered reservation resolves to *no* pool and gets 0 available.
- **H2 (reserve check per account, not per pool).** `_check_reserve_availability` summed amounts per budget account; two child codes drawing one coarse pool each passed on their own. It now groups the reserve amounts by the resolved pool and checks once per pool.
- **Case B (nested pools double-count).** ADR-0005 assumed a chain never has two funded levels and never enforced it. The nesting guard now enforces it at post time; `scan_pool_overlaps` reports legacy overlaps.
- **H3 (`used` under the OU fence).** `_sum_used` ran under the operating-unit record rules and missed reservations other OUs made on a shared pool. It now runs `sudo()` (this can only *lower* Available; the appropriation side keeps its OU fence, ADR-0011).

## Considered options

- **A new module owning the engine/guard/picker** — rejected. The rule is core `budget`'s documented design; H1/H2 are core bugs that must be fixed in core regardless; an extension would have to override `_resolve_control_nodes`, the reserve check and the picker wholesale (no `super`), reviving the "two definitions of available" fork ADR-0005 rejected; and the nesting guard is the invariant the engine relies on, so it cannot live in an uninstallable module. Edited core `budget` in place; other modules were touched only where they own the code (`budget_transfer`, `budget_transfer_sarabun`, `agx_approval`, `budget_demo`). Fallback if prod `budget` must barely change: keep engine+guard+reserve-check in core and move only the picker UX into `budget_reservation_descendant`.
- **Separate earmarked pools / one merged pool per chain / child-first overflow (ADR-0005 Case B)** — rejected in favour of the single "pools never nest" rule.

## Consequences

- **Picker.** The dimension filters show pools **covering** the typed code (its ancestors *and* descendants — always on, no parameter). The reservation pins the finer of the filter value and the picked row (via `filter_ancestors`). Picking a coarse pool row whose account is outside the host's domain (`narrow_required`) forces a "รหัสงบประมาณ" autocomplete limited to that subtree before confirm; a pool row that *is* pickable but has selectable descendants (`account_narrowable`) offers it optionally. An "งบที่จองได้ … (คุมงบที่ …)" line shows the engine's Available for the final selection.
- **Consumption is unchanged** (ADR-0010 lock): consume copies the reservation's codes; to spend at a finer code, reserve at it.
- **Projects and plans are unchanged** (exact tagged sub-pool, ADR-0012 / kmitl_project ADR-0006). A descendant draw on those happens on the allocation transfer's FROM side, which must sit on the floating pool's coordinate.
- **Reports.** The monitoring dashboard and the picker read every figure at the pool: usage at a Descendant Code is folded onto its pool's row, and a filter finer than a pool surfaces that pool with its whole usage (see the ADR-0008 amendment). Follow-up: the same fold plus account/fund roll-up in `budget_report`.
- **agx_approval** category pin changed from `=` to `child_of` (a category pins a budget *branch*).
- **Migration** `16.0.2.3.0/post-migration.py` only logs `scan_pool_overlaps` for open fiscal years. Before deploy, run the scan on a production copy: the H1 fix and the net≠0 rule change the figures for uncovered codes and zero lines.

## Known limitations (pre-existing, noted)

- Un-posting a posted move (`button_draft`) can leave reservations with no pool behind them (follow-up: manager-only or shrink check).
- Tagged reservations are subtracted twice from untagged pools (`_sum_used` leaves tags unpinned).
- Re-parenting accounts after posting bypasses the guard; the scan detects it.
- Two conflicting postings at the same instant can race (no lock); the scan detects it.
