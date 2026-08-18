# Cash & revenue handover is raised from the disbursement request, and then let go

Government-budget money is held centrally, but it is spent by faculties, so the
cash and the recognised revenue have to end up under the spending unit's
dimensions. KMITL funds this **just in time**: exactly what is being spent, at the
moment the payable is registered — so the handover is drawn in
`_create_bill()`, one entry per disbursement request, for the gross request total.
Once drawn it is **completely decoupled**: created in `draft`, taken through the
ordinary accounting Submit → Approve by the accountant, and cancelled or reversed
by the accountant too. Nothing in this module follows the request's lifecycle
afterwards.

## Considered options

- **A standalone document central raises when it allocates**, mirroring
  `budget.transfer` on the GL side. Rejected: KMITL does not pre-allocate cash to
  faculties, so there would be no business event to hang it on, and a unit's cash
  would drift from what it actually spent.
- **One batched entry per day or period covering many requests.** Rejected for now;
  it lowers entry volume but makes "which handover funded this disbursement"
  unanswerable from either document.
- **Due-to / due-from accounts between units instead of re-tagging cash.**
  Rejected: it is the cleaner interfund treatment and would leave bank
  reconciliation alone, but it is not the treatment KMITL's accountants use.
- **Coupling the handover to the bill** — posting it when the bill posts, cascading
  cancellation, auto-reversing on cancel. Rejected: a posted GL entry should not be
  reversed without someone deciding to, and the accountant already owns every other
  correction on these documents.

## Consequences

- **A bill can be posted while its handover is still `draft`**, which books the
  expense unfunded — the exact thing the feature exists to prevent. Accepted, with a
  non-blocking `exception.rule` warning on bill submission and a smart button from
  the request. Nothing blocks, so a request never becomes unbillable.
- **The handover needs its own link field.** `account.move.disbursement_request_id`
  is the inverse of the request's `bill_ids`, which carries no `move_type` filter, so
  reusing it would make the handover *be* a vendor bill — blocking bill creation and
  advancing the request to `bills_posted` the moment the handover posted. Hence
  `cash_revenue_handover_request_id`.
- **`analytic_distribution` is written per line, never on the header.**
  `accounting_kmitl` propagates a header distribution onto every line, which would
  collapse the two sides of the entry onto one set of dimensions and leave an entry
  that moves nothing.
- **No source of funds is named in code.** Eligibility is "a Central Funding Profile
  exists for this source", so widening scope — another government source, or
  institute revenue — is configuration. The repo's only other government-budget
  discriminator (`BUDGET_SOURCE_CODES` in `budget_appropriation_summary_f3`) is
  deliberately not reused.
- **Central's department, fund and activity are all plain configuration.** An earlier
  design derived central's activity by walking the disbursement's activity up to a
  configured depth, on the reading that central always holds the money one level
  above the spender. It does not: central parks every receipt of a source on one
  activity (e.g. `090070101`), which need not be an ancestor of what the money is
  spent on. A fixed Many2one is both correct and simpler, and the depth machinery is
  gone.
- **The profile is not scoped by fiscal year.** One standing row per source of funds,
  edited in place when accounts or dimensions change, rather than a row to create
  every year — so `disbursement.request.account_fiscal_year_id` plays no part in
  resolving a handover. The trade-off is that a handover for a back-dated
  disbursement uses today's configured accounts, not the ones in force that year.
- **The budget ledger is untouched.** Budget is already obligated and consumed at
  the request's final approval; the handover creates no `budget.move`.
