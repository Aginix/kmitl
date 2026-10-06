# Core declares the facts downstream asks about

Four modules outside the disbursement family — the project, the procurement plan, the
พ.1 approval, the advance payment — need to know whether a request has committed its
budget and whether it is still outstanding. Each had answered by listing the request's
state values, including values owned by bridges they do not depend on, so every new
downstream phase silently broke their arithmetic.

## Decision

Core publishes the fact itself as a **stored field**, and whichever bridge actually
knows the answer computes it. `is_settled` is declared on `disbursement.request` with a
default of `False`; `disbursement_finance_kmitl` overrides the compute once the money
has left. "Has it committed budget" needs nothing new — `budget_consumed_amount` is
already core's and already stored.

A stored field, not a helper method: these are used in `search()` domains, and a method
cannot appear in a domain.

## Considered options

- **A helper method on the engine (rejected)** — cannot be used in a domain, and it
  would make every downstream module depend on the work-station engine and learn the
  station vocabulary: the same coupling in a new costume.
- **The field on the finance bridge (rejected)** — downstream would have to depend on
  the finance office's whole app, accounting and bank export included, to ask one
  yes/no question.

## Consequences

- Without the finance bridge installed, `is_settled` stays `False` for every request,
  which is the honest answer: nothing can have been paid.
- This is the same shape as `_on_bills_posted` — core names the event or fact in its own
  vocabulary and leaves it empty; whoever knows fills it in. Core never learns the
  downstream vocabulary.
