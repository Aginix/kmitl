# A remittance is scoped by funding source, and the cheque is booked through both bank accounts

## Context

Two facts about how the office actually files came out of testing the first
working cut (ADR-0002):

- ภ.ง.ด. is filed **per funding source** (แหล่งเงิน), not just per form per
  month. One cheque covers one form, one month, one source — money from
  งบประมาณแผ่นดิน and from เงินรายได้ never travel on the same cheque.
- The cheque is written against the **savings** account, but a cheque cannot
  clear from a savings account: the bank moves the cheque amount into the
  university's **current** account and the cheque is honoured from there.

## Decisions

### `source_analytic_id` is part of the document's identity

The remittance gains a required `source_analytic_id`
(`root_plan_id.code = "sources"`), and the uniqueness constraint from ADR-0002
grows a fifth key: `(company, ภ.ง.ด., period_month, period_year,
source_analytic_id)`. Same form, same month, different source = a second,
legitimate document.

Certificates are selected by source, not just by form and period. The source
is read off the certificate's source WHT line, the same
`analytic_distribution` ADR-0002 already reads the JE lines' dimensions
from — `withholding.tax.cert` has no analytic field of its own, in this module
or upstream, so there is nothing else to read. That means the filter cannot be
a domain (the dimension lives on `account.move.line`, one hop away through
`cert.move_id`, inside a JSON column), so `action_load_pending_certs` filters
in Python after the SQL domain has narrowed by form, period, company and
"not already claimed".

A certificate whose WHT lines carry **more than one** source is rejected
outright rather than split across two remittances. `remittance_id` is a
Many2one: a certificate is remitted whole or not at all (the rule README has
stated since v1). Supporting a partial remittance would mean a Many2many plus
per-source partial amounts on the link — a different, much larger design, and
one the office does not need because a payment is made from one source.

### The clearing JE books both bank movements

Each certificate-and-distribution group posts **four** lines instead of two:

| | Dr | Cr |
|---|---|---|
| the cheque | WHT payable | current account |
| the bank's sweep that funds it | current account | savings account |

The current account is debited and credited the same amount, so it nets to
zero and the money genuinely leaves the savings account — but both accounts
now show the movement, which is the point: each one has to reconcile against
its own bank statement. Collapsing this to `Dr` WHT payable / `Cr` savings
would be arithmetically identical and would leave the current account's
statement unexplainable.

All four lines carry the group's `analytic_distribution`, so dimensions still
net to zero within the entry (ADR-0002). The transfer pair carries **no
partner**: it is the bank moving the university's own money between its own
accounts, not a transaction with กรมสรรพากร, and labelling it
"โอนจากบัญชีออมทรัพย์" keeps it readable in the GL next to the cheque line it
funds.

## Consequences

- `bank_account_id` is gone, replaced by `savings_account_id` and
  `current_account_id`; both are required at `action_post`.
- The JE has `4 × (certificates × distinct distributions)` lines. The two
  bank accounts must be different accounts for the entry to say anything; the
  module does not enforce that, because an office that points both fields at
  one account gets a self-cancelling pair which is visibly wrong rather than
  silently wrong.
- The module now depends on `account_analytic_kmitl` — it owns the `sources`
  plan code the domain and the source lookup are written against.
