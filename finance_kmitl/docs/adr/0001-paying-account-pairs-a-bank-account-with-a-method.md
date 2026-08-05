# A paying account is a bank account paired with a payment method

A paying account (หัวจ่าย) was the institute's bank account itself, flagged
`is_paying_account` on `res.partner.bank` and carrying the GL account its
payments are booked against. That could not express what KMITL's chart does: a
cheque drawn on the KTB account is booked against **เช็คจ่าย-KTB**, not against
the KTB bank account, because the money does not leave the bank until the cheque
clears weeks later — and those cheque accounts are per bank, not one shared one.
The GL account therefore belongs to the **pair** (bank account × payment method),
so `kmitl.paying.account` is that pair, and the flag, the GL account and the
cheque layout moved off `res.partner.bank`.

This does not reverse the earlier decision that a paying account *is* a bank
account rather than a GL account — the pair points at a `res.partner.bank` on the
company's own partner, and the bank, the account number and the BIC are still
read from there by the bank export, the cheque register and the KTB sending
account rules. What changed is that a bank account alone was too coarse to be
the thing chosen.

## Consequences

- **The payment method stops being a separate choice.** The method was a
  `Selection` on the disbursement payment line and a `default_method` on the
  payment subject, either of which could contradict the chosen account. Picking
  a paying account now settles both, so the Selection is gone and the finance
  office's Payment Review edits two fields instead of three. The subject keeps a
  method (`default_payment_type_id`) for one reason only: to disambiguate which
  of a bank's paying accounts auto-matching should pick.
- **The method is named in one place.** `kmitl.payment.type` was already the
  mechanical operation type (`is_cheque` / `is_cash` / journal), and the
  Selection had to be mapped onto it by hard-coded xmlid at payment-creation
  time. That mapping is deleted; the paying account references the type directly.
- **Known gap — nothing credits the bank GL when a cheque clears.** With a
  separate cheque GL, clearing the disbursement books
  Dr เจ้าหนี้ / Cr เช็คจ่าย-KTB, and the entry that finishes the story —
  Dr เช็คจ่าย-KTB / Cr ธนาคาร-KTB — has no owner in the system.
  `cheque.register.action_clear()` only sets a status; the register remains a
  control log. **The treasury office posts that JV by hand**, using the
  register's `clearing_date` as the trigger. Deliberate: making the register post
  entries turns a control log into an accounting document and belongs in its own
  design pass.
- The seed hook only creates the transfer pairs. A cheque pair needs a
  "เช็คจ่าย" GL account that cannot be guessed from a chart code, so it logs a
  warning naming the subject and leaves it to the treasury office.
