# The Finance app is the treasury office's house

A disbursement request is approved twice, and the two rounds sit in **different apps**:
round 1 (ผอ.กองคลัง, then the rector's delegate) in **การขอเบิก**, round 2
(ตรวจสอบการเบิกจ่าย, then อนุมัติเบิกจ่าย) in **การเงิน**. The same document, the same
delegate signing twice, two places to sign.

The split follows from what an app is taken to answer here: **whose desk is this**, not
which document is this. การขอเบิก is the requesting unit's — raising the request,
the head's signature, หมวดตรวจ's verification, and the approvals that turn a request
into a commitment. การเงิน is the treasury office's (กองคลัง) — everything done to a
request once the accounting office has billed it: the audit that decides which หัวจ่าย
each payee is served from, the authorisation that raises the vouchers, the e-payment
file, the cheque register, the withholding-tax certificates. Round 2 is that stretch's
own approval, so it belongs where the stretch is.

Sorting by document instead would put both rounds in การขอเบิก, and the treasury's app
would then be a payments app that its central navigation document — the ใบขอเบิก, which
everything in the payment phase leads back to — is missing from.

## Consequences

- **The rector's delegate works in two apps.** Accepted: the two presses answer
  different questions (may this request be committed / may this money be paid), they are
  weeks apart, and each has its own Todo. A single merged queue was rejected in
  `disbursement/CONTEXT.md` for the same reason.
- **`ตรวจสอบการเบิกจ่าย` sits under การเงินจ่าย, not under ผู้อนุมัติ.** The audit is a
  clerk's step in the paying run, not an approval — round 2 uses *audit* and *authorize*
  precisely so it never reads as round 1's *verify* and *approve*.
- **การเงิน carries menus owned by three modules.** `disbursement_finance_kmitl` defines
  ผู้อนุมัติ and its two queues, because it owns both the approver group and the screens;
  `finance_kmitl` cannot reference them the other way round. The dependency runs
  disbursement → finance, so menus may be pushed up into this app but never pulled.
- **The Disbursement app keeps its own root.** It is not folded into การเงิน: หน่วยงาน
  and หมวดตรวจ are not treasury staff, and giving them a treasury app to look at would
  say they were.

## Rejected alternatives

- **One money app.** Fold การขอเบิก and ใบเสร็จ into การเงิน and shrink the app switcher.
  It reads well until you ask who opens it: a faculty officer raising a request would
  land in the treasury's app, among screens they may not touch.
- **Both approval rounds in การขอเบิก.** Keeps the document whole, and leaves the
  treasury without the authorisation that raises the vouchers it then has to send —
  the one step in their run that they would have to leave the app for.
- **A single "ใบขอเบิกรอการอนุมัติ" queue** filtered by state. Four queues, two rounds
  and four different groups collapse into one list where no approver can tell which
  rows are theirs to press.
