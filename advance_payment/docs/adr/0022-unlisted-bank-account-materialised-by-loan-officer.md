# An unlisted bank account is materialised by the loan officer at verify

Status: accepted (2026-10 UAT feedback; pre-production, no migration/version bump). Amends ADR-0005.

## Context & Decision

ADR-0005/0015 assume the borrower already has a `res.partner.bank` on their work contact: `bank_id` is a picker over those accounts. UAT showed borrowers whose account is not in the system yet — new staff, or a borrower who wants the money paid into a different account. They had no way to submit, because the missing-bank exception blocked them and they cannot create an account themselves.

The borrower now ticks **บัญชีธนาคารนอกรายการ** (`use_unlisted_bank`). That hides `bank_id` and asks for three things instead: the bank (`unlisted_bank_id`, `res.bank`), the account number (`unlisted_acc_number`) and a Book Bank image (`book_bank_file`). Ticking clears `bank_id`. While the box is ticked, the borrower change no longer refills `bank_id`.

- **At submit** the blocking `excep_missing_bank_account` rule (`advance_payment_exception`) passes when `bank_id` is set, **or** the box is ticked with all three fields filled.
- **At `to_verify`** the loan officer presses **สร้างบัญชีธนาคาร**. It opens a wizard prefilled from the three fields, which the officer may correct against the Book Bank. Saving reuses the borrower's existing account with the same sanitised number, or creates one on the borrower's work contact under `sudo()`. It then sets `bank_id`, clears the tick and logs to the chatter.
- **`action_verify` refuses** a loan whose `bank_id` is still empty. The money path (`_prepare_account_payment_vals`) never sees an unlisted account.

The three unlisted fields are treated like `bank_id`: material once submitted, correctable by the loan officer through `to_verify` and by an admin at any time (`_PROTECTED_FIELDS` / `write()`).

The button and wizard live in a **separate module**, `advance_payment_partner_bank`, which follows the `disbursement_partner_bank` pattern.

## Why

- `group_user` can only read `res.partner.bank`, so the borrower cannot create the account. Granting write would let any employee edit any partner's bank details.
- ADR-0005 already makes the loan officer the person who checks bank details against the evidence. Creating the account is the same check, done once, at the step where the officer already holds the paper.
- Blocking verify instead of approve keeps the rule at the officer's own step. The approver never sees a loan with no payable account.
- A separate module keeps the core free of bank-account write logic. A deployment that manages bank accounts some other way can leave it out; the core still blocks verify without `bank_id`.

## Consequences

- Without `advance_payment_partner_bank` installed, an unlisted-bank loan stops at `to_verify` until someone with bank-account rights creates the account and the officer picks it in `bank_id`.
- `bank_id`'s edit window is unchanged (the officer may still correct it up to the transfer). The unlisted fields are only meaningful until the account is materialised; they are kept afterwards as the audit trail of what the borrower declared.
