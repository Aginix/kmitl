# Budget

Budget appropriation, reservation and disbursement tracking for KMITL. Money is appropriated to budget accounts (`budget.move`), then reserved → obligated → consumed against those accounts (`budget.commitment`). Availability is the appropriated pool minus what the commitment pipeline has locked.

## Language

### Access & scope

**Operating Unit (OU, หน่วยงาน)**:
The access-control boundary (`operating.unit`, from OCA). A user only sees budget moves/commitments whose `operating_unit_id` is among their allowed OUs (central-planning staff are granted all). It gates *visibility* — it is not a financial dimension and is never summed or shown as a report axis.
_Avoid_: department, faculty (those name the financial dimension)

**Owning Unit (หน่วยงานเจ้าของ/ผู้จอง, `operating_unit_id`)**:
On a Budget Reservation, the OU that reserved the money and whose pool it draws from — the *funder* (normally central). This is the plain `operating_unit_id`.
_Avoid_: beneficiary, requester

**Beneficiary Unit (หน่วยงานผู้รับการสนับสนุน/ผู้ใช้, `beneficiary_operating_unit_id`)**:
On a Budget Reservation, the single OU the reservation is made *for* — the unit that requested support and will spend the slip. A separate Many2one (one unit per slip). A user sees a reservation when their OU matches **either** the Owning Unit **or** the Beneficiary Unit. Kept single (not M2m) but explicit so the funder need not always be central — a unit may in future reserve for another unit.
_Avoid_: owner, funder (that is the Owning Unit)

**Department (ส่วนงาน, `department_analytic_id`)**:
One of the six financial dimensions (the `departments` analytic plan), carried on move/commitment lines and used as a report **filter**. Mirrors the Operating Unit in meaning but is a separate field used for financial breakdown, not for access.
_Avoid_: operating unit, OU

### Budget structure

**Budget Account (รหัสงบประมาณ)**:
A node in the hierarchical chart of budget codes (`budget.account`). Carries a `budget_type` (revenue / expense) and rolls up parent→child. The default (innermost) row axis of budget reports; the monitoring dashboard can optionally nest it under a financial dimension such as Activity.
_Avoid_: account (ambiguous with `account.account`), category

**Activity (กิจกรรม, `activity_analytic_id`)**:
One of the six financial dimensions (the `activities` analytic plan) — a hierarchical program classification whose levels read ด้าน → แผนงาน → กิจกรรม → กิจกรรมย่อย, so a node's kind depends on its depth. Carried on move/commitment lines; used as a report filter and as the optional outer row axis of the monitoring dashboard.
_Avoid_: ด้าน/แผนงาน/กิจกรรม (the descriptive long form — prefer the short label "กิจกรรม"), program, task

**Budget Pool**:
The appropriated money available on a budget account for a fiscal year, before any commitment activity. Built up from appropriation and transfer moves.
_Avoid_: allocation (reserve "allocation" for the initial act of appropriating)

**Floating Budget (เงินลอย)**:
The appropriated pool on a *project-type* budget account (`is_project`) that has been posted but not yet moved onto any specific project. It carries the four dimensions (activities/departments/funds/sources) but **no `kmitl_project` dimension**. It is the **source** งานแผน draws from when it does a **Project Allocation** (ปรับเข้าแผน) — transferring a slice into a project's own dimension; the project then reserves *that* slice, never the floating pool directly ([kmitl_project ADR-0006](../kmitl_project/docs/adr/0006-project-allocation-before-reserve.md), superseding ADR-0007's direct-reserve). The procurement-plan path has no floating stage (it reserves the instant its appropriation posts); the project path deliberately does (ADR-0007).
_Avoid_: unallocated budget, งบคงเหลือ (that is Remaining (f), a different quantity)

**Pool Tag (ป้ายกำกับเจ้าของ — โครงการ/แผน, `kmitl_project` / `procurement_plan`)**:
The two supplementary dimensions, treated as *ownership tags* that mark which project or plan owns a reserve drawing on a pool — as opposed to the four core dimensions that define the pool itself. In the availability engine they are pinned absent (`= False`) on the appropriation/**Current** side but left unconstrained on the **Used** side (`budget.controller`), so a four-dimension (untagged) query counts only untagged appropriation as Current yet subtracts *every* reserve on the pool whatever tag it carries. Consequence: money a project/plan has reserved is **not** part of the untagged Floating Budget remainder and **cannot be moved by a plain (four-dimension) Budget Transfer** — to move it, its reservation must first be released back to the pool (ADR-0009). The two tags are **not symmetric**: a `procurement_plan` appropriation *is* itself tagged (a real five-dimension bucket, ADR-0005), whereas a `kmitl_project` appropriation stays untagged/floating and the tag lives only on the reservation (ADR-0007).
_Avoid_: dimension (the four core dims define a pool; a Pool Tag names an owner, not a pool), reservation

**Budgetable (ระบุงบประมาณได้, `budgetable`)**:
A budget account where budget may be specified — both reserved against and appropriated to. Reservations are restricted to budgetable accounts; it is the flag that marks a node as a legitimate place to control budget.
_Avoid_: leaf, allocatable

**Cross-charge (ถัวจ่าย, `cross_chargeable`)**:
Pooling more than one budget code inside a *single* reservation. A reservation normally carries one budget code; it may carry several reserve lines only when every line's budget account is flagged `cross_chargeable`. The flag alone governs eligibility — flagged codes may be pooled together regardless of category. Lives in the **`budget_cross_charge`** extension module (ADR-0014): core `budget` blocks >1 code outright; the extension carries the flag, the `is_cross_charge` manual line grid on the slip, and the picker as a browse/edit tool.
_Avoid_: transfer (that is `budget.transfer`, a balanced move *between* accounts; cross-charge moves nothing — it spends several pools in one reservation), virement

**Control Node (โหนดคุมงบ)**:
The budgetable account at which a reservation's pool is actually controlled — the nearest budgetable ancestor-or-self of the reserved account that carries appropriation. A reservation draws from its control node, and all usage in that node's subtree rolls up to it. Mostly the control node *is* the reserved account itself; for coarsely-budgeted lines (personnel, project) it is an ancestor. Appropriation may sit at or above the reservation node, **never below** it (one-way, up only). The same nearest-funded-ancestor rule applies independently on each hierarchical analytic dimension (resolved from `account.analytic.account` parent paths; flat dimensions like Source match exactly).
_Avoid_: parent, category (those name tree position, not the control role)

**Available (งบที่จองได้)**:
Remaining (f) evaluated at the control node — the amount a new reservation may draw. The figure the reservation check enforces and the picker shows on a row.
_Avoid_: remaining (keep "remaining" for the report column; "available" is the reservation-time check at the control node)

### Appropriation side (`budget.move`)

**Initial Appropriation (งบประมาณจัดสรรต้นปี)**:
The budget allocated at the start of the fiscal year, excluding any later adjustment or transfer. Identified by `appropriation_type = 'initial'`.
_Avoid_: original budget, opening budget

**Current Budget / งบประมาณ (a)**:
The budget pool after all latest adjustments = initial + supplementary appropriations + net transfers in/out. The denominator for "remaining". Defined as the net of every posted move that raises or lowers the pool (appropriation and entry/transfer moves), **excluding** consumption.
_Avoid_: total budget, final budget

**Budget Transfer (การโอนงบ)**:
A balanced move (`budget.transfer` → `budget.move` of type `entry`) that shifts pool between `(budget.account × dimension combination)` buckets — increasing Current Budget at the destination, decreasing it at the source. Driven by the line's full `analytic_distribution` across all active dimensions **including a Pool Tag when present**, with `sources` (แหล่งเงิน) locked to the transfer header (no cross-source). It is a **pure budget move** at the `(budget.account × analytic_distribution)` level: it does **not** reserve, release, or create any `budget.commitment` — reserving/releasing budget is a separate, manual step (ADR-0009). A tagged line moves money in or out of a five-dimension tagged sub-pool (see Budget Allocation to a plan/project); an untagged line moves the four-dimension floating/base pool. Part of "adjustments", so it is reflected in Current Budget (a). Its **approval is gated through e-Saraban**: once the data is confirmed, an official letter (see หนังสือขออนุมัติโอนงบประมาณ) is issued and routed for signature, and the transfer posts to the ledger only when that letter is signed (ADR-0014). A Budget Manager may still approve-and-post directly, without a letter, as a controlled fallback.
_Avoid_: reallocation, virement (that is cross-charge / ถัวจ่าย — pooling pools in one reservation, which moves nothing), **โอนเงินและรายได้** (that is a General Ledger entry moving real cash and recognised revenue between departments' dimensions — see [Cash & Revenue Handover](../disbursement_cash_revenue_handover/CONTEXT.md); a Budget Transfer moves the pool and never touches `account.move`)

**แบบ งปม. 303 (แบบประกอบการขออนุมัติโอน/เปลี่ยนแปลง/ปรับเพิ่ม-ลด)**:
The printable supporting form for a Budget Transfer (`budget_transfer_pdf`): a งปม. 303-styled document listing the FROM (ปรับลด) and TO (ปรับเพิ่ม) lines with their dimensions, amounts, and reason. It is the *attachment* (สิ่งที่ส่งมาด้วย) that accompanies the หนังสือขออนุมัติโอนงบประมาณ so a signer sees exactly which buckets move; it is not itself the letter of approval.

**หนังสือขออนุมัติโอนงบประมาณ (e-Saraban document for a transfer)**:
The official correspondence (`sarabun.document`) issued from a confirmed Budget Transfer to obtain approval. Its body is plain text ("ด้วย … มีความประสงค์ขออนุมัติโอน เปลี่ยนแปลง …") referencing the attached แบบ งปม. 303; its signature is the transfer's approval. Signing it auto-posts the transfer (ADR-0014). Distinct from the transfer's own **BTR** number: the letter carries its own e-Saraban register number, assigned when signed.

**Budget Allocation to a plan/project (ปรับเข้าแผน, a tagged Budget Transfer)**:
A Budget Transfer whose destination carries a Pool Tag (`kmitl_project` / `procurement_plan`), moving money out of the four-dimension Floating Budget and into that project's/plan's five-dimension **tagged sub-pool** — committing an abstract floating envelope to a *specific* project or plan once that record exists (its analytic account minted). After allocation the sub-pool is reachable only by naming the same tag: a plain four-dimension transfer/query no longer sees it (that is the Pool Tag netting), so the money "อยู่ในกอง" of the project/plan and can be moved again only tag-in-hand. It moves pool between buckets and **locks nothing** — the project/plan still reserves separately (ADR-0012). The transfer itself never mints the analytic account; the record is expected to exist first (its lifecycle mints it before allocation).
_Avoid_: reserve/จอง (that locks money in the commitment ledger, a different operation), appropriation (the initial year-start pool build-up), cross-charge

**Adjustment (ปรับปรุง/ปรับโอน)**:
The in-year movement on the pool = Current Budget − Initial Appropriation = supplementary appropriations + net transfers. Shown as its own column between (1) and (a).
_Avoid_: change, revision

### Disbursement side (`budget.commitment`)

A commitment holds one cap and a ledger of lines; each line is a reserve/obligate/consume entry. The three operations are **independent primitives** — a flow may fire them at different times (procurement instalments) or together (PO disbursement).

**Budget Reservation / ใบจองงบประมาณ (a standalone `budget.commitment`)**:
A `budget.commitment` created **directly** as a first-class document — reserved up front against a budget pool with no originating source document — and later **picked up** by consuming documents (PR / disbursement) that obligate/consume against it. Generalises the shared-commitment pattern: previously only a `procurement.plan` or `kmitl.project` could own a pre-reserved commitment, now a commitment may also stand alone. The reservation slip and the consuming document may belong to **different Operating Units** (central reserves, a unit spends).
_Avoid_: allocation, earmark (use "reserve"); BC on its own is the *reservation slip*, not the spend.

**Draw down (หยิบใบจองไปใช้)**:
The act of a consuming document (PR / disbursement) **linking to an existing reservation** (`budget_commitment_id`) instead of reserving its own — after which its spend obligates/consumes against that shared commitment. A drawing document never re-reserves and inherits the reservation's dimensions + fiscal year locked. One reservation may be drawn by many documents up to its cap (plan keeps its one-active-PR rule; project and standalone allow many).
_Avoid_: consume (that is only the final leg); draw-down is the linking, obligate/consume are what follow.

**Approved Spending Limit (วงเงินอนุมัติ) / ขอใช้ทั้งหมด (3)**:
The per-commitment cap (`commitment.amount`) — the amount a request was approved to spend. Dashboard column (3) = sum of caps over commitments still active (not cancelled). May exceed what is actually reserved.
_Avoid_: budget, reserved amount

**Reserve (จองงบ)**:
Earmarking pool against a commitment; a `reserve` ledger line. **Timing depends on the allocation path.** For a *procurement plan* it fires the moment its source budget **appropriation is posted** — reserving the full `total_price` at once (not at *ready*; see ADR-0005). For a *project* the appropriation leaves the pool **floating** (see Floating Budget); งานแผน then does a **Project Allocation** into the project's own dimension, and the reserve fires at the project's จองงบ step against *that* project-dimensioned slice, reserving its full `budget_amount` — a deliberate divergence from the procurement-plan timing in ADR-0005 (see ADR-0007, and [kmitl_project ADR-0006](../kmitl_project/docs/adr/0006-project-allocation-before-reserve.md) for the allocation step). A commitment may also be reserved **directly** as a standalone ใบจองงบประมาณ (Budget Reservation), independent of any plan/project/source document.
_Avoid_: allocate, commit

**Obligate (ผูกพัน)**:
Binding earmarked money to an obligation (contract / PO / disbursement request). An `obligate` ledger line, posted before its matching consume.
_Avoid_: encumber, commit

**Consume (ตัดงบ / เบิกจ่าย)**:
The actual disbursement — money leaves the pool for good. A `consume` ledger line.
_Avoid_: spend, pay, disburse (pick "consume" in code, "เบิกจ่าย" in UI)

**Return Unused Reservation (ส่งคืนเงินเหลือจ่าย / คืนจอง)**:
Releasing the reserved-but-**unobligated** remainder of a commitment (`total_reserved − total_obligated` = `available_to_obligate`, the form's **คงเหลือ**) back to the pool, when the reservation was never fully bound to an obligation. It is the **คืนจอง** reversal: a negative `reserve` ledger line that lowers the commitment's reserved total down to its obligated level so Available / Remaining (f) rises — **without cancelling** the commitment, which stays intact for audit. Returns only the *uncommitted earmark*: never money already disbursed, and never the obligated-but-unpaid portion (**ผูกพัน**), which stays reserved until its obligation is itself reversed. Because current flows fire obligate and consume together (ADR-0001), this equals the not-yet-disbursed remainder (`total_reserved − total_consumed`); the two diverge only once a flow obligates ahead of disbursement.
_Avoid_: คืนเงิน (refunding an already-consumed/disbursed amount — a negative `consume` line, a different operation), cancel (releases the whole commitment, not just the leftover)

**Reserved (b) / Obligated (c) / Disbursed (d) / Used (e) / Remaining (f)**:
The disbursement waterfall for an account (**pool scope** — the dashboard and budget report): `b` = reserved-but-not-yet-obligated (`total_reserved − total_obligated`); `c` = obligated-but-not-yet-disbursed (`total_obligated − total_consumed`); `d` = disbursed (`total_consumed`); `e` = total locked = `b + c + d = total_reserved`; `f` = `Current Budget (a) − e`. Both KMITL flows fire obligate and consume **together** — the PO flow, and the procurement-plan flow (per งวด at each disbursement request) — so `c` stays ~0 in practice. The not-yet-disbursed remainder of a reserved procurement plan therefore sits in `b` (reserved-but-not-obligated), **not** `c`. `c` only carries a standing balance if some flow posts an obligate without an immediate matching consume (a capability the ledger supports but no current flow uses).
_Avoid_: spent (ambiguous between c, d, e)

**Commitment display — จองเงิน / ผูกพัน / เบิกจ่าย / คงเหลือ (document scope)**:
How a single `budget.commitment` form and tree present its money — a four-part waterfall over the commitment's own ledger. **จองเงิน** = `total_reserved`, the fixed headline total this commitment reserved. **ผูกพัน** = `available_to_consume` (`total_obligated − total_consumed`) = obligated but not yet disbursed; a disbursement's consume nets off its obligate, so it falls back toward 0 as งวด are paid. **เบิกจ่าย** = `total_consumed`, disbursed so far. **คงเหลือ** = `available_to_obligate` (`total_reserved − total_obligated`) = reserved but not yet obligated. Invariant: `จองเงิน = คงเหลือ + ผูกพัน + เบิกจ่าย`. These three slices are the same waterfall as the pool-scope bands b/c/d, so the form's **ผูกพัน** (= band c) and **เบิกจ่าย** (= band d) match the dashboard/picker column headers exactly. Scope caution on the two labels that do *not* match: the form's **คงเหลือ** is this commitment's `reserved − obligated` (band b), whereas the dashboard/picker column **คงเหลือ** is the pool's Remaining (f) = `Current Budget − Used`; and the form headline **จองเงิน** is the commitment's total reserve, whereas the dashboard's near-homonym **เงินจอง** is band b (`reserved − obligated`). Because current flows fire obligate and consume together (ADR-0001), **ผูกพัน** reads 0 on today's real commitments and **คงเหลือ** carries the not-yet-disbursed remainder — the split only separates once a flow obligates ahead of disbursement.
_Avoid_: **ยอดผูกพัน** = `total_obligated` (cumulative) shown as a form figure — it mirrors เบิกจ่าย and reaches the cap when done, the misleading display this entry replaced; a single `reserved − consumed` "เงินผูกพันคงเหลือ" number that fuses คงเหลือ and ผูกพัน (the earlier three-number design, now split into the two).
