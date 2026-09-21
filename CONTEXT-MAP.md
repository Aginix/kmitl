# Context Map

This is a multi-module Odoo monorepo. Each custom module is its own bounded context,
documented by a `CONTEXT.md` (glossary) and an optional `docs/adr/` (architecture
decisions) inside the module folder.

This map is seeded lazily — modules are listed here as they get a `CONTEXT.md`, not
upfront.

## Contexts

- [KRIS Project](./kris_project/CONTEXT.md) — revenue tracking for projects run under
  the KRIS unit (operating unit `99`); external academic-service and research work
  channelled through KRIS.
- [KRIS Project — In Cash / In Kind](./kris_project_in_cash_in_kind/CONTEXT.md) —
  optional split of a research project's `project_value` into `in_cash` (cash KRIS
  receives) and `in_kind` (matching funds that never touch KRIS's cash accounts);
  anchors every cash-flow compute on `in_cash` when installed.
- [Budget](./budget/CONTEXT.md) — appropriation, reservation and disbursement tracking;
  appropriated pool (`budget.move`) consumed through a reserve→obligate→consume
  commitment pipeline (`budget.commitment`).
  - **`budget_transfer`** (no own glossary — part of the Budget context): houses the
    budget-transfer feature (การโอนงบ) split out of core `budget`. `budget.transfer` is
    a 1:1 delegated `budget.move` (the `account.payment` ↔ `account.move` pattern) with
    its lines folded into `budget.move.line`; see budget ADR-0013.
  - **`purchase_request_budget`** + its source bridges `kmitl_project_purchase_request`
    and `purchase_request_procurement_plan` (no own glossary — part of the Budget
    context): give a ใบขอซื้อ (พ.1) its **แหล่งงบประมาณ** — reserve anew from the
    ผังงบประมาณ, or draw the reservation of a โครงการ or a แผนจัดซื้อจัดจ้าง. Each bridge
    owns its own answer; a source-less ใบจองงบประมาณ is not an option here (budget
    ADR-0015).
- [Budget Appropriation Summary](./budget_appropriation_summary/CONTEXT.md) —
  institution-wide roll-up of unit appropriations for one fiscal year × source
  (สรุปภาพรวมสถาบัน gathering รวมเล่มหน่วยงาน), rendering the F-series summary reports
  and ending in one authoritative **Published Final** = the re-uploaded **Final
  Document** with a transparent **Watermark PDF** overlaid on every page.
- [Budget Revenue Comparison](./budget_revenue_comparison/CONTEXT.md) — configurable
  report setting **budgeted revenue** (`budget.move`, revenue codes) beside **actual
  revenue** (`account.move.line`, income types) row by row; each row carries two
  independent selectors because the budget chart and the CoA have no stored link.
- [Procurement Plan](./procurement_plan/CONTEXT.md) — annual procurement planning; a
  plan stands on its own (budget-free core), optionally reserves budget when verified,
  and may originate from a posted appropriation. Realised through one purchase request;
  its installments (งวด) track actual disbursement (see the Disbursement bridge below).
- [Procurement Plan — Disbursement](./procurement_plan_disbursement/CONTEXT.md) —
  tracking-only bridge that manually links each งวด (`procurement.plan.payment`) to the
  disbursement request paying it, so the plan can compare planned งวด against budget
  actually consumed. The plan authors no disbursement; money goes out through the PO.
- [KMITL Project](./kmitl_project/CONTEXT.md) — institutional project/activity planning
  (โครงการ/กิจกรรม); งานแผน allocates budget into the project's own dimension
  (ปรับเข้าแผน), the project reserves that allocation, then spends like a procurement
  plan (ADR-0006).
- [Accounting Reports](./accounting_kmitl_reports/CONTEXT.md) — financial-statement
  reports (Trial Balance, P&L, Balance Sheet, Cash Flow) over the GL
  (`account.move.line`), filterable by the KMITL accounting dimensions.
- [Accounting Workflow](./accounting_kmitl_workflow/CONTEXT.md) — two-step maker-checker
  approval every `account.move` passes before posting (Submit by ผู้จัดทำ/ผู้ตรวจสอบ →
  Approve by ผู้อนุมัติ = post); a custom `workflow_state` + computed `display_state`
  overlaid on the existing `draft→submitted→posted` flow, plus a journal-items voucher
  report with a signature block.
- [Identity & Access](./iam/CONTEXT.md) — standalone app that delegates backend
  user/role/group/OU/access-right/record-rule administration without granting full
  Settings (`base.group_system`); a single `IAM Manager` group implying `erp_manager`
  plus one escalation guard.
- [Todos](./mail_activity_todo/CONTEXT.md) — cross-cutting unified inbox (สิ่งที่ต้องทำ)
  of everything a user must act on; each Todo is a native `mail.activity` on its source
  record, surfaced in one consolidated page with a jump-to-source button. Owns no
  business state.
- [Attachment Document Type](./web_attachment_document_type/CONTEXT.md) — patches the
  stock `many2many_binary` widget to add always-on drag-and-drop plus optional
  Document-Type classification driven by a shared `ir.attachment.document_type_id`
  field; consumers turn classification on for a model by shipping data XML
  (`ir.attachment.document.type.config` + `ir.attachment.document.type.rel`), no
  Python/JS per consumer.
- [e-Saraban](./agx_sarabun/CONTEXT.md) — electronic official-correspondence
  (งานสารบรรณ); a registered, numbered หนังสือ routed through an approval/endorsement
  chain. Other modules attach as origin records that spawn a Document.
- [Approval Request (Expense Plan)](./agx_approval/CONTEXT.md) — expense-approval form
  reframed as proposing an _expense plan_ (what is planned to be spent + who is
  involved); the payee is deliberately **not** on the plan — the recipient is settled
  later at disbursement. Routed for approval through e-Saraban.
- [Approval ↔ Disbursement Bridge](./agx_approval_disbursement/CONTEXT.md) — links an
  Approval Request to the Disbursement Request it is billed into; returning a
  disbursement keeps it intact (at `signed`) and bounces the approval request to
  `returned`, where the requester corrects a limited set of fields and confirms to push
  them back onto the disbursement.
- [KMITL Finance](./finance_kmitl/CONTEXT.md) — the finance office's side of paying
  money out: the **ใบจ่ายเงิน** (which _is_ an `account.move`), its **money side** /
  **booking side** split, the finance office's own `finance_state`, and the instrument
  that carries the money — the **ไฟล์ e-Payment** one bank is sent, or the **เช็ค** one
  payee collects. Ends at the **Hand-over**.
- [KMITL Finance Reports](./finance_kmitl_reports/CONTEXT.md) — the กองคลัง's reports
  on money in both directions. Out: **รายงานการจ่ายเงิน**, one row per voucher paid, on
  the day the money left rather than the day it was authorised, and
  **รายงานเจ้าหนี้ถึงกำหนดชำระ**. In: **รายงานการรับเงิน** over the receipts that have
  reached the treasury (`kmitl.receipt` at `done`), plus **รายงานการตั้งลูกหนี้** and
  **รายงานลูกหนี้ถึงกำหนดชำระ** over the **ใบตั้งหนี้** — which a receipt never settles,
  so the two money-in populations never mix. The ถึงกำหนดชำระ pair is deliberately not
  the backward-looking Aged Payable/Receivable next door in `accounting_kmitl_reports`,
  and รายงานการรับเงิน is deliberately not `receipt_kmitl_summary_report`: that one is
  the issuing department's register, this one the treasury's. Defines no document —
  every term is `finance_kmitl`'s or `receipt_kmitl`'s.
- [Disbursement ↔ KMITL Finance](./disbursement_finance_kmitl/CONTEXT.md) — the
  post-bill payment-execution phase of a disbursement request (audit → authorize → pay →
  clear); owns the payee-level **รายการจ่ายเงิน** and keeps apart the several records
  that all sound like "what this payment is" (เรื่องที่จ่าย, ประเภทธุรกรรม,
  ลักษณะการจ่าย, หัวจ่าย, วิธีจ่าย, ใบสำคัญ).
- [Cash & Revenue Handover](./disbursement_cash_revenue_handover/CONTEXT.md) — the
  **โอนเงินและรายได้** entry that re-recognises centrally-held government-budget cash
  and revenue under the dimensions of the unit actually spending it; the first bridge in
  the repo between the budget side and the General Ledger, driven entirely by a
  **Central Funding Profile** per source of funds.
- [Disbursement — Cash Movement](./disbursement_cash_movement_kmitl/CONTEXT.md) — the
  **การโยกเงินระหว่างบัญชี** legs, added to a disbursement voucher's own journal entry,
  that trace its money from source account down to the หัวจ่าย that pays the payee — the
  trail a bank auto-sweep leaves that accounting never otherwise books. Driven entirely
  by **Cash Route** (`kmitl.cash.route`), one row per (paying account × sources of
  funds); a row naming no intermediate account means "pays directly", a missing row is a
  setup gap.
- [Advance Payment](./advance_payment/CONTEXT.md) — employee cash-advance loans
  (สัญญายืมเงิน); a single-disbursement loan to one borrower, tracked from request
  through clearing to closure. A borrower may hold only one active agreement at a time,
  so multi-activity needs are met by serial borrowing.
- [Receipt KMITL](./receipt_kmitl/CONTEXT.md) — cash receipting and central-posting
  workflow (ใบเสร็จรับเงิน สจล.); a department issues receipts and bundles them into
  a Receipt Remittance (รายงานนำส่งคลัง) that treasury posts, generating one journal
  entry per receipt with a Remit to Treasury (นำเงินส่งคลัง) leg into the payment
  method's deposit account, alongside the 6D dimensions on every line.
- [Purchase Contract Revision](./purchase_contract_revision_kmitl/CONTEXT.md) — PO
  amendment flow as first-class ``purchase.contract`` revision records (N per PO;
  Rev 0 auto at confirm, Rev N user-initiated). Each revision is a full snapshot of
  header + lines + งวด + committee; approval happens outside the ERP and enters the
  record as a required file attachment. Fully replaces the removed
  ``purchase_order_change`` + ``purchase_order_change_committee`` modules.

## Relationships

- **Budget → Procurement Plan**: posting a `budget.appropriation` line creates a
  `procurement.plan` and reserves its `budget.commitment` for the full amount
  (ADR-0005).
- **Procurement Plan → Budget**: the plan's single purchase request, and the
  disbursement requests that flow from its purchase order, draw that one shared
  commitment down (obligate+consume per DR) (ADR-0004, ADR-0006). The disbursements are
  created and operated on the PO, not the plan; the plan only **tracks** them, linking
  each งวด to its DR by hand (`procurement_plan_disbursement`).
- **Budget → KMITL Project**: posting an appropriation on an `is_project` budget code
  leaves the pool _floating_ — it does **not** auto-create a project or reserve
  (contrast Procurement Plan). งานแผน then **allocates** a slice into the project's own
  dimension (a `budget.transfer`, ปรับเข้าแผน); the `kmitl.project` reserves its
  `budget.commitment` for that project-dimensioned `budget_amount` at its จองงบ step
  (kmitl_project ADR-0006, superseding ADR-0007's direct floating-reserve).
- **KMITL Project → Budget**: the project's purchase requests (พ.1) and disbursements
  draw that one shared commitment down (obligate+consume); a project may hold many PRs,
  capped at the commitment (ADR-0007).
- **Disbursement ↔ Finance (paying account)**: a **หัวจ่าย** is one of Odoo's own
  `account.payment.method.line` records — bank account × method × voucher × GL — seeded
  by `account_kmitl` on ใบสำคัญจ่าย (PV) and administered in `finance_kmitl`
  (`finance_kmitl` ADR-0001). A disbursement picks one **เรื่องที่จ่าย**
  (`kmitl.payment.subject`), which derives a paying account for every payee, optionally
  matching each to the account held at their own bank; the auditor overrides individual
  payees by hand (`disbursement_finance_kmitl` ADR-0002/0003). One e-payment file debits
  one paying account, and the file's sending account is read from it.
- **Disbursement / Finance → Accounting Workflow**: disbursement vendor bills and
  payments no longer post directly — their `account.move` enters the approval and is
  posted by Approve. A payment voucher is held by the **two offices in turn, on two
  fields of one document** (designed docs-first, **not yet built** —
  `disbursement_finance_kmitl` ADR-0005, superseding ADR-0004): the finance office works
  entirely on its own `finance_state` (**ยืนยันพร้อมส่งธนาคาร** → e-payment file →
  **ยืนยันจ่ายสำเร็จ**) while `account.move.state` stays `draft` and belongs to the
  accounting office alone; **จ่ายครบ** on the request is the **Hand-over**, after which
  the voucher waits in `draft` for the accounting **maker** to correct the booking and
  submit it and the **approver** to approve = post = ล้างหนี้. The lock is per side —
  the money side (amount, payee, หัวจ่าย, date) freezes when finance confirms; the
  booking side (dimensions, ประเภทธุรกรรม, description) stays open for the maker — but
  the **surface** is per form: the payment voucher form is the finance office's and
  closes whole at ยืนยันพร้อมส่งธนาคาร, the maker correcting the booking on the journal
  entry instead (`finance_kmitl` ADR-0002). The bank's result file is never imported:
  exceptions are settled outside the system and vouched for by the single จ่ายครบ
  confirmation. **How** a payee is settled decides which record carries the finance
  office's work between confirming and paying — an **ไฟล์ e-Payment** for a transfer, a
  **เช็ค** (`cheque.register`, one per voucher) for a cheque, and nothing at all for
  cash (`finance_kmitl` ADR-0006). A cheque is also the one thing that can fail after
  the payee holds it, so cancelling one takes its voucher back to `confirmed` while the
  request stays `paid` — the only way backwards in the whole phase (`finance_kmitl`
  ADR-0007).
- **Disbursement → Approval (return)**: returning a `disbursement.request` at `signed`
  keeps it untouched (still `signed`, budget unchanged) and bounces the linked
  `approval.request` to `returned`; the requester corrects only the payee bank,
  description and disbursement evidence, then **Confirm Correction** pushes those onto
  the kept disbursement and moves the AR back to `billed` (`agx_approval_disbursement`
  ADR-0001).
- **Approval Request ↔ Advance Payment**: once a request is `approved`, each participant
  who is an internal employee may **pull** their own สัญญายืม and pick the request on
  the loan form — the request never pushes loans out. A request may back several loans,
  capped by its Borrowing Headroom. The loan clears **itself**; an `advance` allocation
  row only _names_ the Funding Loan it was paid from, which need not be the recipient's
  own. No cancellation cascades in either direction (`agx_approval` ADR-0003). Budget
  consumption for borrowed money is **parked**.
- **All contexts → Todos**: a workflow schedules/clears a `mail.activity` (a Todo) at
  its own state transitions; Todos only aggregates and surfaces them and holds no
  business state (`mail_activity_todo` ADR-0001). Sources today include Procurement
  Plan, Purchase Request (พ.1) and the Accounting Workflow; **e-Saraban** is designed
  next (see below — docs-first, not yet built); the next actor is either a single user
  or a role-in-unit group (`base_user_role` role ∩ operating unit, resolved live —
  `mail_activity_todo` ADR-0002); dynamic `tier.validation` routing is deferred.
- **e-Saraban → Todos** (designed docs-first, **not yet built** — `agx_sarabun`
  ADR-0013/0014): e-Saraban will raise a native `mail.activity` per active routing-step
  holder — **gating and รับทราบ / CC alike** — instead of its own systray; the bespoke
  Action tray + `sarabun_inbox` bus are **to be dissolved** and an `agx_sarabun_todo`
  bridge will tag each activity as `execution` (a step that gates or signs) or
  `acknowledgement` (a pure รับทราบ), so all e-Saraban work lands in the one Todo inbox
  (a read-only involved user opens it via `_mail_post_access='read'`, ADR-0013). A
  separate opt-in `mail_activity_todo_sound` add-on plays a per-user notification sound,
  which the bridge refines into per-source (sarabun vs general) on/off toggles.
- **KRIS Project → In Cash / In Kind**: `kris_project_in_cash_in_kind` inherits
  `kris.project` and, on research projects, turns `project_value` into a derived sum of
  `in_cash + in_kind`; every cash-flow compute repoints from `project_value` to a
  `cash_target` that equals `in_cash` on research and `project_value` elsewhere. Base
  module behaviour is unchanged when the add-on is not installed.
- **Disbursement → Cash & Revenue Handover**: registering the payable for a disbursement
  that spends centrally-held money drafts one `account.move` moving the gross request
  total of **cash and recognised revenue** out of central's dimensions and into the
  spending unit's — same GL accounts on both sides, so nothing but the dimensions
  change. Which sources of funds this applies to, and central's own
  department/fund/activity (all three fixed, never derived from the disbursement), come
  entirely from a **Central Funding Profile** (`kmitl.central.funding`) per source of
  funds; a source with no profile is never handed over. The entry is then **fully
  decoupled** — accounting posts, corrects and cancels it on its own, and the budget
  ledger is untouched (budget was consumed at the request's final approval). A
  non-blocking exception warns if the bill is submitted while the handover is still
  draft (`disbursement_cash_revenue_handover` ADR-0001).
- **Disbursement → Cash Movement**: a disbursement voucher's `account.move` already
  correctly books `Dr เจ้าหนี้ / Cr หัวจ่าย`; registering it grows the missing legs in
  between, in the **same entry**, tracing the money from its source account down to the
  หัวจ่าย that pays the payee — one **Cash Route** per (paying account × sources of
  funds), keyed by the underlying GL account rather than by หัวจ่าย because one bank
  account's transfer and cheque หัวจ่าย must already book against the same GL
  (`account_kmitl`). A route naming no intermediate account means "pays directly"; a
  paying account with no route at all for a voucher's source of funds is a setup gap,
  surfaced as a non-blocking warning at Submit. Scoped to vouchers raised from a
  disbursement request; the budget ledger and the bank reconciliation view are both
  untouched by design (`disbursement_cash_movement_kmitl` ADR-0001/0002).
- **Budget ↔ Operating Units (cross-OU reservation)**: a standalone `budget.commitment`
  (ใบจองงบประมาณ) may be reserved by one OU (the **Owning Unit** / funder — normally
  central) _for_ another (the **Beneficiary Unit** — the requesting unit); both OUs see
  the slip, the beneficiary draws it down through its own พ.1 / disbursement, and the
  spend counts against the **funder's `department`** dimension while the
  พ.1/`budget.move` carries the **beneficiary's OU** (budget ADR-0010, ADR-0011).
  Consuming documents (`purchase.request`, `approval.request`) may **pick** any drawable
  commitment — standalone, plan or project — instead of reserving their own.
- **Receipt KMITL → GL**: posting a `kmitl.receipt.remittance` (treasury action)
  creates one `account.move` per receipt directly — no budget or disbursement layer
  in between. Every line carries the receipt's 6D `analytic_distribution`, including
  the Remit to Treasury (นำเงินส่งคลัง) pair that moves the cash received into the
  payment method's Deposit Bank Account; that pair shares its dimensions with the
  revenue line it mirrors, so its analytic balance nets to zero by design
  (`receipt_kmitl` ADR-0004).
