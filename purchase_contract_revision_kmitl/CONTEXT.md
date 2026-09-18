# Purchase Contract Revision

Redesigned PO amendment flow. Replaces the ``purchase_order_change`` wizard by
splitting the "sanctioned agreement" from the "static hub": each amendment is
its own ``purchase.contract`` record — a full snapshot of the agreed contract
at a moment in time. External approval evidence (paper / สารบรรณ) is required
as an attachment before the record can apply back to the PO; there is
deliberately **no in-system approval cycle**.

## Language

**PO / Purchase Order (`purchase.order`)**:
The static reference hub. Owns the PO number, vendor, department, fiscal year,
payment type, budget commitment, and all external references (guarantee, work
acceptance, disbursement, ครุภัณฑ์). Its mutable "contract-shaped" fields
(``fines_rate``, ``supervision_cost``, ``work_start``, ``contract_period_days``,
``order_line``, ``invoice_plan_ids``, committees) are read-through of the
current applied contract revision. External docs never reference a Contract
directly; they always point to the PO.
_Avoid_: agreement, สัญญา (that is the Contract).

**Contract Revision (`purchase.contract`)**:
One record per revision. Rev 0 is the *original* — auto-created at
``purchase.order.button_confirm`` and immediately in state ``applied``. Rev N
(N ≥ 1) is a user-initiated *amendment* — created draft from the current
applied revision, edited, and applied on demand. Each record snapshots the
full contract state at the moment it was applied: header fields + lines
(``purchase.contract.line``) + งวดงาน (``purchase.contract.invoice.plan``) +
committee members. Historical revisions are immutable audit records.
_Avoid_: purchase.order.change (the deprecated wizard), amendment (Rev N only),
snapshot (that is the technical mechanism).

**Current Contract (`purchase.order.current_contract_id`)**:
The latest ``applied`` revision on a PO — computed, stored. All read-through
fields on the PO resolve against this record. During a Rev N draft cycle,
``current_contract_id`` still points at Rev N-1 (the last applied); it only
advances when Rev N successfully applies.
_Avoid_: latest revision (may include drafts — this filters to ``applied`` only).

**Applied / Draft / Cancelled**:
The three lifecycle states of a contract revision. ``draft`` = user is editing;
``applied`` = terminal, immutable, drives the PO's read-through fields;
``cancelled`` = terminal, kept for audit. There is deliberately **no** approval
state (see ADR-0003). Rev 0 is created directly in ``applied`` at PO confirm;
Rev N transitions ``draft → applied`` via ``action_apply`` (or ``draft →
cancelled`` via ``action_cancel``).
_Avoid_: to_approve, approved (from the earlier e-Saraban proposal — rejected).

**Approval Attachment (`approval_attachment_ids`)**:
External approval evidence — the paper document or สารบรรณ record that
authorised this amendment. Stored as ``ir.attachment`` records linked M2M to
the revision. The **only gate** on ``action_apply`` beyond the value-level
constraints; ≥ 1 file must be present. No metadata (number / date / signer) is
required at this stage — see the open item in ADR-0003.
_Avoid_: signature, e-signature, approver (approval happens outside the system;
the record only carries the evidence).

**Frozen งวด (`purchase.contract.invoice.plan.is_frozen`)**:
An งวด is *frozen* when its live counterpart (``purchase.invoice.plan``) has a
``disbursement.request`` created against the parent PO. Frozen rows are
readonly in the revision form: their amount / plan_date / installment must
match the previous revision exactly, and they cannot be deleted. See ADR-0002
for why the freeze trigger is disbursement rather than WA acceptance.
_Avoid_: paid งวด (frozen is a stricter earlier moment — the disbursement may
still be in draft), locked งวด.

**รหัสงบประมาณ (analytic_distribution match)**:
The rule that every contract line must carry an ``analytic_distribution``
that appears somewhere on the *previous* revision's line set. This blocks
"budget-shifting" through amendments — reducing scope or reallocating between
existing budget codes is allowed, moving money to a new code is not. Current
implementation compares the entire 6-dimensional distribution dict exactly;
the "adjust % between existing keys" case is not yet supported (open item).
_Avoid_: budget account (that is a different level — the analytic distribution
carries the full 6D framework, of which budget account is one dimension).

**Case Detection (`purchase.contract.case`)**:
Three-way discriminator that drives the revision form's editing rules:
``single`` (no งวด — case 1 in the requirement), ``phased_none_disbursed``
(งวด exist but none are frozen — case 2.1, all rows editable freely), and
``phased_partial_disbursed`` (≥ 1 งวด frozen — case 2.2, the strictest case
with the 2-tab locked flow). Computed on the revision, not the PO, so the
detection re-runs each time a new revision opens.
_Avoid_: hardcoding the case as PO-level state — it depends on the current
disbursement footprint which can grow over time.

## Known limitations (accepted, revisit later)

- **Committee snapshot doesn't sync back to `procurement.committee`.** The
  form lets you edit the committee members on a revision (M2M of
  `hr.employee`), but ``action_apply`` doesn't currently rewrite the PO's
  ``procurement.committee`` records to match. In practice, edits made on the
  revision are historical/audit only until the sync bridge lands.
- **``analytic_distribution`` exact match is strict.** Adjusting the split
  percentage between two existing analytic accounts on the same line is not
  distinguishable from moving to a new account; both are rejected by the
  current check.
- **Legacy `purchase.order.change` records are gone.** The
  ``purchase_order_change`` / ``purchase_order_change_committee`` modules
  were removed entirely as part of this redesign; their tables (and any
  data in them) disappear when a database uninstalls those modules through
  the Apps UI, which must happen before this module is deployed on top.
  No migration of the old field-level diff into ``purchase.contract`` was
  attempted — the old wizard stored only diffs, not full snapshots, so a
  faithful reconstruction was not possible.
- **Freeze detection is coarse.** A งวด is currently classified as frozen when
  *any* disbursement.request exists on the parent PO and the งวด is
  ``invoiced``. When ``disbursement.request`` gains an explicit
  ``installment_id`` field the check will tighten to per-งวด linkage.
