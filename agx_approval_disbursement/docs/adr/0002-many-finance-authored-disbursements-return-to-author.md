# Many finance-authored disbursements per approval; a returned one goes back to its author

Status: accepted (2026-10) — **supersedes [ADR-0001](0001-return-corrects-approval-in-place.md)**.
Context: [agx_approval ADR-0009](../../../agx_approval/docs/adr/0009-finance-authors-disbursements-from-actuals.md).

An Approval Request no longer generates one Disbursement Request from its own
recipient rows. A finance officer creates as many DRs as needed from a request
in `to_disburse`, each prefilled with the request's header only, and closes the
request (ตั้งเบิกครบแล้ว → `billed`) when done. The DRs together may not exceed
the request's actual total.

Because finance — not the requester — now owns the recipients, banks and lines,
a DR returned for correction at `signed` follows the **base disbursement return**:
the DR goes back to `draft` with a To-Do for its creator (the finance officer),
who resubmits it straight to verification. The approval request is not bounced
to `returned` and has no correction step; `approval.request` stops being a
`disbursement.return.source.mixin`.

We chose this over keeping ADR-0001's correct-in-place flow because its three
correctable fields (payee bank, description, evidence) no longer live on the
request, and the person who can fix a DR is the one who wrote it. Requests
already sitting in the old post-bill `returned` state are migrated back to
`billed`; their DRs stay at `signed` for the officer to return again through
the base flow.
