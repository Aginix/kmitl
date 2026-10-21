# Procurement Assignment

How responsible procurement officers (เจ้าหน้าที่พัสดุ) are assigned to the three core
procurement documents, so each officer can see the work assigned to them.

## Language

**PR (Purchase Request, พ.1)**: The `purchase.request` document — ใบขอให้จัดหา, a unit's
request to procure, approved by the หัวหน้าส่วนงาน (department head). It is the _ask_;
it does not itself authorise buying.

**PA (Purchase Approval, พจ.1)**: The `purchase.request.approval` document —
ขออนุมัติจัดซื้อจัดจ้าง, the separate step that authorises actually buying, raised after
the PR is approved. Its data is _copied_ from the PR but may legitimately diverge
(vendor, tax, procurement type can be re-edited on the PA) and it has its own approver —
so PA is a **separate model, deliberately never merged into PR**. It carries its **own
copied columns + line model** (ADR-0004) so those edits never mutate the PR. The
procurement flow is PR → PA → PO. _Avoid_: Purchase Agreement; Work Acceptance (WA is a
separate document, ตรวจรับ); treating PA as a mere view/report of the PR.

**PO (Purchase Order)**: The `purchase.order` document — an order to buy/hire
(ใบสั่งซื้อ/สั่งจ้าง).

**Procurement Mode (โหมดจัดหา)**: A flag chosen on the PR for who sources vendor and
price: _ให้พัสดุจัดหา_ (the procurement officer sources them — the requester leaves
vendor/VAT blank, and they are filled later on the PA) or _ผู้ขอระบุเอง_ (the requester
specifies vendor + VAT up front). It replaces the old amount-based vendor-required rule;
budget is never mandatory at PR creation regardless of mode. _Avoid_: deriving "must
specify a vendor" from an amount threshold.

**Requesting Department (ส่วนงานผู้ขอ)**: The ส่วนงาน that asks for the procurement — a
value from the `departments` analytic plan at any level (คณะ / ภาควิชา / หลักสูตร),
chosen by the requester on the PR and carried PR → PA → PO (copied, so the PA may
diverge). It is descriptive only: it drives no budget check and no access. It is **not**
the budget's **Department** (the ส่วนงาน whose money is spent) and **not** the
**Operating Unit** (the access boundary). E.g. ภาควิชาวิศวกรรมไฟฟ้า requests equipment
paid from คณะวิศวกรรมศาสตร์'s central budget: Requesting Department = the ภาควิชา,
Department = `01`, OU = the คณะ. See
[ADR-0009](docs/adr/0009-requesting-department-analytic.md). _Avoid_: หน่วยงาน (that is
the Operating Unit); a bare "department"; assuming it must equal or sit under the
budget's Department; the issuing ส่วนงาน of the หนังสือ (that is the requester's own
employee department).

**Assigned Officer (เจ้าหน้าที่ผู้รับผิดชอบ)**: The procurement officer (เจ้าหน้าที่พัสดุ)
responsible for handling a document's work. Lives on the **PA**. Its default comes
**only** from the **Purchase Buddy** settings: the first Buddy, by order, whose row
covers the PA. Nothing is carried over from the PR. While the PA is still open, a pick
that the settings no longer cover is replaced, and a covered pick is kept. Anyone in
the Purchase Buddy group may be picked by hand. It may stay empty when no row covers the
PA. Naming the officer routes nothing and grants nothing: no Todo, no extra access. See
[ADR-0013](docs/adr/0013-pa-assigned-to-is-assigned-officer-from-purchase-buddy.md).
Not on the PR: the PR's `assigned_to` is the **Designated Verifier**
([ADR-0011](docs/adr/0011-pr-assigned-to-is-designated-verifier.md)). _Avoid_:
Responsible (that's the PR creator, `user_id`), Buyer (PO `user_id`), Approver (the
หัวหน้าส่วนงาน signing through Sarabun), Purchase Representative.

**Purchase Buddy (เจ้าหน้าที่ Buddy พัสดุ)**: A central procurement officer and the
documents they look after. Each coverage row names one Buddy, one document type and a
condition, usually "ส่วนงานผู้ขอ is under ส่วนงาน X". One document may be covered by
several Buddies, and one Buddy may hold several rows. Coverage only supplies the
**Assigned Officer** default. It is not authority and not access. _Avoid_: Budget Buddy
(budget's own group and list, kept separate on purpose); Designated Verifier.

**ผู้ตรวจสอบ พ.1 (Verifier)**: The ธุรการ who checks a submitted PR at `to_verify`. They
enter its รหัสงบประมาณ and dimensions, and either press ตรวจสอบ to pass it to the budget
step or ตีกลับ it to `draft`. After ตรวจสอบ they may ดึงกลับ it from `to_verify_budget`
to fix a mistake, as long as nothing is reserved yet. They do not reserve money. See
[ADR-0010](docs/adr/0010-pr-split-verify-and-budget-commit-direct-entry.md). _Avoid_:
ผู้อนุมัติ (that is the หัวหน้าส่วนงาน signing through Sarabun); Assigned Officer.

**ผู้ยืนยันตรวจสอบ (Designated Verifier)**: The one **ผู้ตรวจสอบ พ.1** the requester names
on a PR, from the PR's own Operating Unit. They receive the PR's Todo whenever it enters
`to_verify`. Naming them routes the work but does not restrict it: any Verifier may still
press ตรวจสอบ or ตีกลับ. The Todo counts as done only when the named person verifies.
Anyone in the PR's workflow may rename them until the PR ends. See
[ADR-0011](docs/adr/0011-pr-assigned-to-is-designated-verifier.md). _Avoid_: Assigned
Officer; ผู้ตรวจสอบ alone (that is the whole group, and `verified_by` is who actually
pressed ตรวจสอบ).

**ผู้จองงบประมาณ พ.1 (Budget Committer)**: The holder of the PR-specific budget-commit
duty at `to_verify_budget`. They may still correct the code and dimensions, then either
press Reserve (which checks completeness and availability and creates the ใบจองงบประมาณ)
or ตีกลับ the PR one step to `to_verify`. This is a separate, independent duty from the
Verifier. The PR names one of them as its **ผู้ยืนยันงบประมาณ**. _Avoid_: the generic
role จองงบประมาณ, which reserves คำขออนุมัติ but no longer a พ.1.

**ผู้ยืนยันงบประมาณ (Designated Budget Committer)**: The one **ผู้จองงบประมาณ พ.1** named on
a PR, from the PR's own Operating Unit. They may be named from `draft` and must be named by
the time ตรวจสอบ is pressed. They alone receive the PR's reserve Todo while it waits at
`to_verify_budget`. Naming them routes the work but does not restrict it: any Budget
Committer may still Reserve or ตีกลับ. See
[ADR-0012](docs/adr/0012-pr-designated-budget-committer.md). _Avoid_: ผู้อนุมัติงบประมาณ
(ผู้อนุมัติ is the หัวหน้าส่วนงาน); `budget_committed_by` (who actually reserved);
agx_approval's ผู้ยืนยันงบประมาณ, which is a whole group there, not one named person.

**God Mode (PA edit while `to_approve` / `approved`)**: An elevated, narrow edit surface
on the พจ.1 (PA) while the record is in state `to_approve` or `approved` (never
`rejected` / `cancelled`). Members of the security group
`purchase_request_approval_godmode.group_pa_godmode` may amend six PA header fields
(`partner_id`, `procurement_type_id`, `procurement_method_id`, `payment_type`,
`vat_included`, `tax_id`) and three line fields (`product_qty`, `price_unit`, `name`) on
`purchase.request.approval.line` **without transitioning the PA state**. Adding/removing
lines is not allowed; `product_id`, `product_uom_id`, `title`, `description`, the
Assigned Officer (`assigned_to`) and audit columns (`verified_by`, `approved_by`,
`date_verified`, `date_approved`) stay locked. An `@api.constrains` rail enforces
`sum(open PAs.amount_total) ≤ budget_commitment.amount` at the elevated states —
covering the KMITL Project shared-commitment case — paired with a mirror rail in the
base module that owns `draft` state for all users (see **Budget-cap rail (พจ.1)** below
and [ADR-0008](docs/adr/0008-pa-budget-cap-draft-rail.md)). God-Mode writes are
**silent**: no chatter entry, no field tracking, no follower notification is emitted
(for either direct edits or workflow buttons the god-mode user presses). When a god-mode
edit touches a field visible in the พจ.1 PDF, the stored `<pa.name>.pdf` `ir.attachment`
is unlinked and re-rendered so Sarabun's export/print serves the corrected document.
Downstream PO/DR/bill artefacts are **not** re-derived — God Mode is a surgical PA
correction, not a re-issue. Sarabun sync of God-Mode edits is owned by a separate branch
which detects changes by diffing the `vals` dict inside its own `write()` override. See
[ADR-0006](docs/adr/0006-pa-godmode-edit.md). _Avoid_: treating God Mode as a
re-approval, a cancel-and-reissue, or a way to add/remove line items; assuming
`title`/`description` are editable in God Mode (they are not).

**Budget-cap rail (พจ.1)**: A pair of `@api.constrains` on `purchase.request.approval`
enforcing the same rule —
`sum(sibling PAs in same commitment, state ∈ (draft, to_approve, approved) .amount_total) ≤ budget_commitment.amount`
— split by state scope so each user surface is covered. The base module's
`_check_amount_within_commitment` owns `state == 'draft'` for all users
([ADR-0008](docs/adr/0008-pa-budget-cap-draft-rail.md));
`purchase_request_approval_godmode`'s `_check_godmode_amount_within_commitment` owns
`to_approve` + `approved` for god-mode users only
([ADR-0006](docs/adr/0006-pa-godmode-edit.md)). Aggregate — matters for the KMITL
Project shared-commitment case where one `budget.commitment` backs many พ.1 → many พจ.1.
The related display field `budget_commitment_amount` ("จำนวนเงินที่จองงบไว้") on the PA
form surfaces the cap in the Procurement Information group so the user sees it before
Save. _Avoid_: treating the two rails as one (they duplicate on purpose for module
isolation); expecting a per-PA cap (the rule is aggregate); adding a `write()` override
to enforce this (it would fight god-mode's silent-write override).

**ตีกลับ/แก้ไข (PA-to-PR return, keep-number)**: A negative-path lifecycle transition
from พจ.1 (PA) `draft` back to พ.1 (PR) `to_verify` for revision, initiated by the PA
manager via the "ตีกลับ/แก้ไข" button (wizard collects only a mandatory reason). Effect:
PA parks in `pending_pr` (name/number **preserved** for reuse), PR's active sarabun is
**soft-voided** (see below), PR moves to `to_verify` (budget commitment intact), and the
user is redirected to the PR form. When the same PR's sarabun re-completes,
`_transition_after_sarabun_approve` **re-syncs all copied PA fields from the (possibly
edited) PR** and flips `pending_pr → draft`. Cross-model return (PA → PR), deliberately
distinct from Sarabun-side ตีกลับ
([agx_sarabun ADR-0006](agx_sarabun/docs/adr/0006-recall-split-pullback-vs-cancel-send.md))
which stays inside `sarabun.document`. The full resync **contradicts
[ADR-0004](docs/adr/0004-pa-owns-copied-data.md)'s "free to diverge" intent** on purpose
— return = restart, not tweak. See [ADR-0007](docs/adr/0007-pa-return-for-revision.md).
_Avoid_: confusing with Sarabun ดึงกลับ / ตีกลับ (those don't cross model boundaries);
assuming God-Mode edits on the PA survive a return (they don't — resync overwrites);
assuming this cancels the PA (it doesn't — `name` is kept for reuse).

**`pending_pr` (PA state — waiting-for-PR-revision)**: A PA lifecycle state indicating
"parked, waiting for PR revision cycle to complete". Not in the drawio v2 model
referenced by [ADR-0005](docs/adr/0005-post-sarabun-state-split.md) — a scoped extension
for the ตีกลับ/แก้ไข negative path. The PA's `name` (registered พจ.1 number) is retained
across the parking so the same document is reused when it flips back to `draft`. Hidden
from the statusbar (`statusbar_visible` does not include it). _Avoid_: confusing with
`sarabun_returned` (that's a Sarabun-approver return via the PA's OWN sarabun cycle);
confusing with `cancelled` (terminal); leaving the state key unqualified (`pending_pr`
says explicitly "waiting on PR", distinguishing it from a bare `returned`).

**Soft-void sarabun (`state=cancelled` with the number kept)**: Writing
`sarabun.document.state = 'cancelled'` directly via `sudo` write, **without** calling
`_void_register` — so the register number stays `used`, and the doc can later be revived
by `_restart_chain + state=draft`. Used by `_cancel_request_sarabun` on the PA to park
the PR's sarabun during a ตีกลับ/แก้ไข cycle. Semantically distinct from
[agx_sarabun ADR-0006](agx_sarabun/docs/adr/0006-recall-split-pullback-vs-cancel-send.md)'s
"cancelled = terminal + voided number"; a real `action_recall` cancel and a soft-void
look identical at the `state` field. This is a known semantic quirk accepted for
pragmatic UX — see [ADR-0007](docs/adr/0007-pa-return-for-revision.md). _Avoid_:
assuming `state=cancelled` on a sarabun implies its number is voided (check
`register_number_id.state` if it matters); using this pattern outside the ตีกลับ/แก้ไข
flow (real cancels go through `action_recall`).

## Known limitations (accepted, revisit later)

- **`_resume_returned_sarabun` picks the latest cancelled sarabun by `id`.** If a PR has
  multiple cancelled sarabun documents from unrelated histories (e.g., a real
  `action_recall` earlier in the record's life), the revive picks whichever has the
  highest id. Real-world rare because a real recall requires `not has_signed`, but the
  search is not tightened to identify only soft-voided ones. Acceptable today.
- **PA `draft` has no direct Cancel button.** After the ตีกลับ/แก้ไข wizard was
  simplified to keep-number only, cancelling a PA that is still in `draft` requires:
  click ตีกลับ/แก้ไข first (PA → `pending_pr`, PR → `to_verify`), then Cancel from the
  PR side. The PA stays orphaned in `pending_pr` unless an admin explicitly cleans it
  up. Acceptable today; a future iteration may auto-cascade PA `pending_pr` →
  `cancelled` when the PR cancels.
- **A general requester cannot choose a โครงการ/กิจกรรม (`kmitl.project`) on a PR.** A
  project PR is created only from the project form, which most requesters cannot open.
  User feedback says requesters should be able to pick the project by name when buying
  under a project. Deferred.
