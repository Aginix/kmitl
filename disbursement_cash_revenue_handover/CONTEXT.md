# Cash & Revenue Handover

Government-budget money arrives in a central bank account and is recognised as
revenue under central's dimensions. When a unit other than central spends it, the
cash and the revenue have to be re-recognised under that unit's dimensions, or the
unit's financial statements read as expense with nothing funding it. This context
raises that entry from the disbursement request at the moment the payable is
registered — the first thing in the repo to bridge the budget and the General
Ledger.

## Language

**โอนเงินและรายได้ (Cash & Revenue Handover)**:
The `account.move` (ใบสำคัญทั่วไป / JV) that moves **cash and recognised revenue**
from central's dimensions to those of the unit that is spending, using the **same
GL account on both sides** — the money does not go anywhere, only its dimensions
change. Four lines: central gives up the cash and reverses its revenue, the unit
recognises both again. Its **header** dimensions are the funded request's, shown
read-only and carried for identification only — the truth of the entry is on the
lines, whose two sides differ, so the usual header-onto-lines propagation is
suppressed here.
_Avoid_: **การโอนงบ** (`budget.transfer` — moves the budget *pool*, touches no GL;
see [budget](../budget/CONTEXT.md)), **ปรับเข้าแผน** (a tagged budget transfer into
a project/plan sub-pool), **จัดสรรงบประมาณ** (`budget.appropriation` — the
year-start pool build-up), **Internal Transfer** (Odoo's `is_internal_transfer`,
hidden in `finance_kmitl`), payment (the handover settles nothing and pays nobody).

**ผังเงินงบประมาณส่วนกลาง (Central Funding Profile)**:
`kmitl.central.funding` — one row per (source of funds × company) saying which bank
account the money sits in, which revenue account recognised it, and which
**department, fund and activity** central holds it under. **The row's existence is
the rule**: a source with no row is never handed over, so bringing a new source of
funds into scope is a configuration change, not a code change. Deliberately **not**
scoped by fiscal year — one standing profile per source, edited in place when the
accounts or dimensions change.
_Avoid_: หัวจ่าย (`account.payment.method.line` — the account money goes *out* of,
a different thing entirely; see
[disbursement_finance_kmitl](../disbursement_finance_kmitl/CONTEXT.md)),
เรื่องที่จ่าย, ประเภทธุรกรรม, chart of accounts mapping.

**Central Dimensions (มิติของส่วนกลาง)**:
The three dimensions on the profile — **department, fund and activity** — under which
central holds the money. All three are **fixed configuration, never derived from the
disbursement**: central parks every receipt of a source on the same three, whatever
the money is later spent on. Only the fourth dimension, source of funds, is read off
the disbursement, and it is identical on both sides because a handover never crosses
แหล่งเงิน. The spending unit's side of the entry takes the disbursement's own
`analytic_distribution` whole.
_Avoid_: rolling central's activity up from the disbursement's (an earlier design —
central's activity is normally a coarser node such as `090070101` กิจกรรมหลัก while
the disbursement sits at a กิจกรรมย่อย, but it is not required to be an ancestor at
all), Control Node (the `budget` notion of the nearest ancestor that *carries
appropriation* — nothing here is discovered from a balance).

**Central Department (ส่วนงานส่วนกลาง)**:
The department on the profile — the one holding the money. A disbursement raised by
this department, or by any department beneath it, is already spending where the
money is held and gets no handover.
_Avoid_: Operating Unit (an access boundary, not a financial dimension),
ส่วนกลาง used loosely (say which department, since sub-units of central count too).

## Known limitations (accepted, revisit later)

- **The bill can be posted while the handover is still `draft`.** The handover is
  deliberately decoupled (see [ADR-0001](docs/adr/0001-dr-triggered-decoupled-handover.md)),
  so nothing enforces the order. A non-blocking `exception.rule` warns the
  accountant when submitting such a bill; ignoring it books the expense unfunded.
- **Nothing follows the request's lifecycle.** Cancelling a request or its bills
  leaves the handover standing; reversing it is accounting's job. Equally, a
  handover posted for a request later cancelled is not auto-reversed.
- **Bank reconciliation carries the two cash lines.** The cash account is
  reconcilable, so each handover leaves a debit and a credit of equal amount in the
  reconciliation view. They net to zero but are not statement lines.
- **The account the money arrives in is not the account it leaves from.**
  Government-budget money is received into one bank account and paid out of the
  หัวจ่าย's, which is a different one. The handover moves whichever account the
  profile names, so a unit's cash nets to zero per *dimension* but not per *bank
  account* unless the treasury's own inter-bank transfer carries matching
  dimensions. Configuration decides which account is moved; no code change is
  needed to switch.
- **Withholding tax leaves a residue at the unit.** The handover is gross, so the
  unit keeps cash equal to the withheld amount against the withholding liability it
  now carries, until central remits it tagged at the unit's department.
- **Actual revenue reads negative at central.** Reports over income-type GL lines
  (e.g. [budget_revenue_comparison](../budget_revenue_comparison/CONTEXT.md)) see
  central's revenue reduced and the unit's raised. That is the intent — revenue
  follows the spender — but the unit's actual revenue has no budgeted counterpart,
  because the revenue budget chart carries no code for government-budget money.
