# ผล (actual) is derived from the execution chain, not stored on the plan

The report shows each item as แผน (planned) beside ผล (actual). The plan model holds only the แผน side. We source ผล by **deriving it from the plan's linked execution chain** — พ.1 (`purchase.request`) → สัญญา/ใบสั่ง → เบิกจ่าย — rather than re-keying a parallel set of "actual" fields onto `procurement.plan`. Only the few actual values that genuinely have no home in that chain (e.g. the variance เหตุผล) are added as plain fields on the plan.

## Considered options

- **Full plan-vs-actual data model on the plan** (actual amount, actual milestone dates, an "actual installments" o2m). Self-contained and controllable, but duplicates data the execution documents already own and forces users to key actuals twice. Rejected.
- **Derive everything from the chain.** Correct source-of-truth, no double entry — but the chain cannot supply every cell (notably per-งวด actual disbursement date / amount / เลขที่เบิกจ่าย). Insufficient alone.
- **Derive + thin gap fields (chosen).** Derive what the chain knows; add plain fields only for the residue.

## Consequences

- Per-installment actual disbursement (วันเบิกจ่ายจริง / จำนวนเงินจริง / เลขที่เบิกจ่าย) is owned by the **disbursement layer**, implemented on a separate in-flight branch. The report consumes it **optionally** (guarded by model presence): until that branch lands, those ผล cells render blank.
- ผล for an item only materialises as its พ.1/สัญญา/เบิกจ่าย progresses; a fresh-year submission prints แผน with an empty ผล column, which is correct.
