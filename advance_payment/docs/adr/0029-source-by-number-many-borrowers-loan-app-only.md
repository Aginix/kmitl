# A source is found by its number, backs many borrowers, and never waits on its loans

Status: accepted (2026-10-29 design session; not yet built; pre-production, no migration/version bump). Supersedes ADR-0026 and the cancel guard of `agx_approval` ADR-0003; amends ADR-0023 and ADR-0025.

## Context & Decision

Policy now requires every loan a borrower files to have a Source Reference (AR or PR). The borrower must say which matter they borrow for and how much. A loan with no source is the loan officer's back-office tool only (ADR-0031). Two facts from practice shaped the rest. First, whoever filed the AR/PR is often not the borrower. Anyone may borrow against it in their own name. Second, a person holds only one agreement at a time (ADR-0001), so a project's money is split across several borrowers.

**The borrower types the document number.** The typed pickers (`approval_request_id`, `purchase_request_id`) gave way to a เลขที่เอกสาร box. It matches exactly (case-insensitive, trimmed) and searches with system rights, but only within the loan type's model and its Reference filter. The match shows only the subject, the unit and the remaining Borrowing headroom. The typed Many2one fields stay as stored mirrors of `reference`. Everyone uses the same box, including a drafter who could read the source anyway.

**Many borrowers per source**, AR and PR alike. The PR's one-live-loan constraint becomes a switchable rule, shipped inactive (ADR-0030).

**Borrowing happens only in the loan app.** `advance_payment_disbursement` no longer hides the PR's ใบขออนุมัติจัดซื้อ button until a loan is outstanding. It also stops copying the PR's loan onto Disbursement Requests. Which loan a ใบเบิก clears is decided with the clearing link (ADR-0028). The PR keeps only its read-only สัญญาเงินยืม smart button.

**The source is not held hostage.** An AR, a PR or its budget commitment may be cancelled while loans against it are live. The loan stands, because the money is out and the debt is the borrower's either way. The AR's cancel guard is removed, and none is added for the PR or the commitment.

**Budget control is an extension, `advance_payment_budget_commitment`.** The loan still holds no commitment and no dimensions (ADR-0025). It reaches the source's `budget_commitment_id`:
- **Borrowing headroom** is the commitment amount minus every non-cancelled loan on it. The AR's fallback to the request total is dropped.
- The commitment must be reserved or partly used.
- Both are blocking rules (ADR-0030) and replace `excep_ar_borrowing_headroom`.
- The disbursement voucher takes the commitment header's `analytic_distribution` through `_prepare_account_payment_vals`. A commitment whose lines carry different dimensions is charged as a whole, and accounting may still correct the voucher.

**Related documents** (`advance_payment_related_document`) are a separate extension. A loan may cite any number of further documents. An in-system one is of a **kind the administrators configure** (ชนิดเอกสารอ้างอิง: a model plus its number, subject and date fields — no module per kind; `advance_payment_related_document_sarabun` only seeds the หนังสือสารบรรณ kind). It is found by number like the source, plus ลงวันที่ when the number alone is ambiguous (Sarabun's register restarts every fiscal year). An out-of-system one is given by number/subject. Either may carry a file. They are evidence only.

## Considered options

- *Picker limited to documents naming the borrower.* Rejected: the source does not name the borrower.
- *Picker listing the borrower's own OU.* Rejected: it shows a unit's approved documents to everyone in it, and it cannot borrow across units.
- *Read rules on AR/PR for borrowers.* Rejected: it needs a read ACL for all users and new rules on two live modules, and it grants more than a number lookup.
- *Only the drafter (unit finance) links the source.* Kept as possible, but on its own it makes every borrower depend on staff.
- *Headroom net of what the commitment spent elsewhere.* Rejected: direct payments usually follow the loans. And on a PR the PO and the loan are the same money, so netting both would count it twice.
- *A declared "loan share" on the source.* Rejected: it needs new fields on live AR/PR and data entry on every request. Splitting the reservation is the loan officer's call at Verify.
- *A bridge module per related-document kind.* Rejected: which documents get cited changes with practice, and each new kind would need a release. The cost is that an administrator can expose any model's subjects by configuring it.

## Consequences

- Document numbers are sequential, so anyone can probe the subject and headroom of an approved source. Accepted: the match shows little, and a wrong source is caught at Verify.
- Every read of the source made for a borrower (status checks, prefill, headroom, dimensions) must run with system rights. The borrower usually cannot read the source.
- `purchase.request.advance_payment_id` (one live loan) no longer describes a PR. Consumers move to `advance_payment_ids`.
- Without `advance_payment_budget_commitment` nothing caps a source.
- Cancelling a source after Verify leaves its loans running with a cancelled commitment. That is deliberate. The rules check the commitment only at submit and Verify.
