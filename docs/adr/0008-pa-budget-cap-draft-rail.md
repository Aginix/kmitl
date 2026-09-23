# พจ.1 (PA) budget-cap rail at `draft` — display the reserved amount and block edits that overshoot

ADR-0006 introduced a budget-cap rail on the พจ.1 (PA) —
`_check_godmode_amount_within_commitment` — enforcing that the aggregate
`amount_total` of every PA sharing one `budget.commitment` stays inside
`commitment.amount`. That rail is deliberately narrow: it only fires for
holders of `group_pa_godmode` in states `to_approve` / `approved` (the
elevated edit surface that ADR-0006 unlocks).

At `draft`, PA lines (`product_qty`, `price_unit`) are freely editable by
any user with PA write access ([ADR-0005]'s post-sarabun state split does
not lock them). Nothing else on the PA side stops those edits from pushing
the aggregate above the commitment reserved when the parent พ.1 (PR) was
approved. In the KMITL Project shared-commitment case (see budget
[ADR-0007]) — where one `budget.commitment` backs many PRs → many PAs —
this can silently overspend the shared pool.

**Decision.** Add a second, parallel `@api.constrains` on
`purchase.request.approval` in the **base** module,
`_check_amount_within_commitment`, firing only in `state == 'draft'`. Its
rule is the same as ADR-0006's rail:

- Aggregate over sibling PAs whose state is in `('draft', 'to_approve',
  'approved')` and whose PR shares the same `budget_commitment_id`.
- Compare `sum(amount_total)` against `commitment.amount` using the
  commitment's currency rounding.
- On overspend, raise `ValidationError` naming the commitment, the
  aggregate total, and the cap.

No group guard — the rail applies to every user, because `draft` is
where every user edits. Sibling PAs in `to_approve` / `approved` are
included in the aggregate so a draft-time user sees the **real** remaining
headroom (not a ceiling that ignores work already advanced by others /
by god-mode).

Alongside the constraint, a new related field
`budget_commitment_amount` (Monetary, related to
`request_id.budget_commitment_id.amount`) surfaces the cap on the PA form
in the *Procurement Information* group — beside `estimated_cost` — so
the user sees the reserved amount before hitting Save. The field is
hidden when no commitment is linked.

## Alternatives considered

- **Unify with god-mode's rail into one `@api.constrains` in base.**
  Rejected: keeps `purchase_request_approval_godmode` self-contained (its
  own ADR owns the elevated-state rule). Two rail methods with the same
  body is a small, well-understood duplication.
- **Only add the display field, no enforcement.** Rejected: the ask is
  explicitly to block edits that overshoot — a display-only field would
  degrade to advisory text.
- **Enforce at `write()` instead of `@api.constrains`.** Rejected: the
  constrain form fires on both create and write, cannot be silenced by
  `sudo`, and is the same shape god-mode uses. Overriding `write()` also
  fights god-mode's silent-write override.

## Consequences

- Two constraint methods live side-by-side on `purchase.request.approval`:
  the base module's `_check_amount_within_commitment` (this ADR, scope
  `draft`) and `purchase_request_approval_godmode`'s
  `_check_godmode_amount_within_commitment` ([ADR-0006], scope
  `to_approve` / `approved` and god-mode users only). Both encode the same
  rule; changing the rule requires touching both.
- Users see **จำนวนเงินที่จองงบไว้** on the PA form whenever a commitment
  is linked; overspend fails at Save with a Thai `ValidationError`.
- Create-time PA does not need a special-case: PA copies from PR
  (`purchase_request_budget` keeps the PR from exceeding the commitment
  in the first place), and the constraint would fire defensively anyway.

## References

- [ADR-0005] post-sarabun state split (`draft` remains editable by
  requesters)
- [ADR-0006] PA God-Mode edit (elevated-state rail this ADR complements)
- [ADR-0007] ตีกลับ/แก้ไข PA→PR return (revive resyncs from PR; this
  constraint fires normally on the resync write)
- budget ADR-0007 (shared-commitment; KMITL Project case)

[ADR-0005]: 0005-post-sarabun-state-split.md
[ADR-0006]: 0006-pa-godmode-edit.md
[ADR-0007]: 0007-pa-return-for-revision.md
