# Every credit on a voucher has its own debit

A voucher whose payee is withheld tax on books a single lump debit on the payable, sized
to the full amount owed, against two credits — the bank paid and the tax withheld.
Reading what the payable was actually cleared by means reading the withholding-tax line
beside it; the payable's own line says nothing on its own.

This decision splits that single debit into one per credit: the payable now carries a
debit of 1,869.16 against the bank credit and a second debit of 130.84 against the
withholding-tax credit, so the entry itself — no other line needed — says the payable
was cleared by 1,869.16 paid out and 130.84 withheld.

## Why it is a module of its own

The split is how KMITL prefers to _read_ an entry, not something the payment stretch
needs to work: a voucher books the same money either way, the bank is told the same
thing, and the certificate and the ภ.ง.ด. report are made of the withholding-tax line,
which is untouched. `finance_kmitl` keeps working, unchanged, with this module
uninstalled — so the preference lives where it can be taken out again, and the module
that owns paying money out does not carry it.

What `finance_kmitl` does carry is two seams this module writes through, both phrased
against "a module that adds a write-off line of its own" rather than against withholding
tax: `_preserved_write_off_lines` (which write-off lines a rebuild must not flatten) and
`_adjust_write_off_line_vals` (the last point at which the write-off values can be
rewritten, after any preserved ones are restored and before core computes the
counterpart from their sum).

Those seams are also why the dependency is on `finance_kmitl` even though the people the
module is _for_ are the accounting office: the finance office never opens a voucher's
journal items (`finance_kmitl` ADR-0002), so the extra line is read by the office that
posts the entry — but the machine that builds the line is `account.payment`'s, and
`finance_kmitl` is the module that owns it. Because neither office's name would be
honest, the module is named for the **model** instead
(`account_payment_wht_counterpart_kmitl`), and the audience is written down in
`CONTEXT.md`.

## Why this fights core on purpose

Odoo's own rule is one and only one receivable/payable line per payment
(`account_payment.py` raises "must include one and only one receivable/payable account"
the moment a second one turns up). This decision puts a second payable line on every
voucher that has withholding tax, which is why it cannot be the obvious reading of the
change: the leg is deliberately kept out of `counterpart_lines` by reclassifying it into
`writeoff_lines` in `_seek_for_lines` — the same trick
`disbursement_cash_movement_kmitl` already uses for its own extra Dr/Cr leg — so that
core still sees exactly one counterpart and never learns there are two payable lines at
all.

## Consequences

- **The write-off preservation has to widen its net, or the rebuild loses money, not
  just identity.** Once the leg is a write-off line to core, core's own rebuild (any
  accounting-maker correction after the money has left, `disbursement_finance_kmitl`
  ADR-0005) folds every write-off line into one dict, taking the first one's
  name/account/partner/currency and summing every line's amount into it. A tax line of
  −130.84 and its leg of +130.84 sum to 0.00, and core would create a single 0.00 line
  in their place — the certificate's `wht_tax_id` gone (as it already was, which is what
  `finance_kmitl`'s existing preservation was for) **and the 130.84 itself never
  booked**. `_preserved_write_off_lines` is therefore widened here to name the legs too.
  If a maker clears a line's `wht_tax_id` outright, the voucher **degrades to the plain
  3-line entry** — the amount survives, only the identity that produced the extra line
  is lost — rather than losing the money.
- **The flag is `copy=True`, not `copy=False`.** `account.payment`'s `line_ids` is an
  inherited field made `copy=True` by `_inherits`, so Action ▸ Duplicate copies every
  line including the leg's. If the flag itself did not copy, the duplicate would carry
  two lines core reads as equally payable and nothing to tell them apart — the next edit
  that triggers `_synchronize_to_moves` (any of core's own trigger fields, e.g.
  correcting the payee's bank account) hits `Command.update(counterpart_lines.id, ...)`
  where `counterpart_lines` has two records, and `.id` on a multi-record recordset
  raises. Before that ever surfaces, the duplicate can already be saved, confirmed and
  paid with a silently wrong pair of payable lines, because `_synchronize_from_moves` is
  never triggered by a plain `create` — nothing catches it until the first rebuild.
- **The leg's account is `destination_account_id`, not a fixed "the payable account".**
  Some operation types override the counterpart account entirely
  (`kmitl.payment.type.override_account_id`); the leg has to land wherever this
  voucher's real counterpart lands, or it would explain a different account than the one
  it is meant to explain.
- **The WHT accounts (`2120000010` / `2120000099`) stay `reconcile=False`.** This
  decision is only about the payable side of the entry; it does not touch
  `withholding_tax_remittance_kmitl` ADR-0001, whose ภ.ง.ด. filing entries remain plain,
  unreconciled journal entries. Opening reconciliation on the tax accounts is a
  different decision, for that module to make.
- **No backfill.** Every voucher already posted keeps its 3-line shape; only vouchers
  created or rebuilt with this module installed get the extra debit.

## Rejected alternatives

- **Put it in `finance_kmitl`.** Where it first landed. It makes the split a fact of
  paying money out rather than a preference about reading the books, and it leaves no
  way to have the one without the other. The seams it needed turned out to be worth
  keeping in `finance_kmitl` on their own terms; the preference did not.
- **Treat the split as an `account.move`-level concern and move the module to the
  `accounting_kmitl` family**, on the reasoning that the accounting office is who reads
  it. Rejected on two counts, neither of them about the reasoning, which is right. There
  is no `account.move` seam to move to: every line of a payment's entry is built by
  `account.payment._prepare_move_line_default_vals` on create _and_ on every rebuild,
  and core's one-counterpart rule is enforced through `account.payment._seek_for_lines`,
  which has no `account.move` equivalent — `disbursement_cash_movement_kmitl` has an
  `account_move.py` and even it only calls `payment._synchronize_to_moves(...)` rather
  than building anything itself. Doing it from `account.move.create` / `write` would
  mean unpicking `line_ids` Command tuples, recomputing the counterpart by hand instead
  of letting core derive it from the write-off sum, and intercepting every journal entry
  in the database for something that can only happen on a payment. And the family would
  lie: `accounting_kmitl` touches no `account.payment` at all, so an
  `accounting_kmitl_*` module would still have to depend on `finance_kmitl` — a name
  pointing one way and a dependency pointing the other. What the reasoning did change is
  the name: since `finance_kmitl_*` claims the wrong office and `accounting_kmitl_*`
  claims an office the dependency contradicts, the module is named for the model it
  extends and the ownership point is recorded in `CONTEXT.md` instead.
- **Leave `_synchronize_to_moves`'s preservation alone.** The original shape of the
  change, on the reasoning that the existing `wht_tax_id`-only filter already keeps _a_
  write-off line alive across a rebuild. It does not survive contact with the leg: the
  moment the leg is itself a write-off line (which it has to be, to stay out of core's
  one-counterpart rule), an unwidened filter lets core merge the tax line and its leg
  into a 0.00 dict and silently drops 130.84 from the entry. A design that changes "lose
  the identity" into "lose the money" is not a smaller version of the same risk.
- **Reconcile the WHT accounts so the payable and the tax line net to zero on their
  own.** A real alternative reading of "make the payable line legible," but it is
  `withholding_tax_remittance_kmitl` ADR-0001's decision to make, not this one's — it
  changes what the tax accounts mean company-wide, not just how one voucher's entry is
  laid out.
- **Fold `wht_tax_id` / `tax_base_amount` into `MONEY_LINE_FIELDS` at the same time.**
  Arguable, since the withheld amount is the difference between the full amount and what
  the bank actually paid — but it changes what the accounting maker may still correct
  after the money has left, which is `finance_kmitl` ADR-0002 /
  `disbursement_finance_kmitl` ADR-0005 territory and deserves its own decision.
