# A worklist is a list view

Four screens in the payment phase were hand-written OWL client actions — the finance
office's **ตรวจสอบการเบิกจ่าย** and **อนุมัติเบิกจ่าย**, the accounting office's
**ใบขอเบิกรอบันทึกบัญชี** (all three one parametrised action,
`disbursement_finance_kmitl.payment_queue`) and **เจ้าหนี้ ▸ ใบล้างเจ้าหนี้**
(`finance_kmitl.clearing_queue`). All four are now `ir.actions.act_window` over an
ordinary tree.

They were written for one reason a list was thought not to give: a press that acts on
many ticked rows at once. A list gives exactly that — a `<button>` in the tree's
`<header>` appears the moment rows are ticked and calls a method on the selection, which
is the idiom core uses for Confirm on its own payment tree and the idiom this module
already used for **สร้างไฟล์ e-Payment** and **สั่งจ่ายเช็ค**. So the reason bought
nothing, and what it cost was everything a list does that nobody rewrites by hand:
search, group, pivot, export, optional columns, a filter of one's own saved on the view,
and the record rules and column-level access that come with the model's real views.

The screens were also, quietly, wrong in two ways that are properties of the approach
rather than bugs to fix:

- **The dimension filters returned nothing.** Both queues filtered by pushing
  `fund_analytic_id in ids` / `activity_analytic_id in ids` into a domain, and both
  fields are `store=False` with no `search=`
  (`disbursement/models/disbursement_request.py:415-451`). `expression` logs the failure
  and substitutes an empty leaf, so picking a fund changed nothing on screen. Round 1's
  queue avoids the two fields with a comment saying why; these two did not. A search
  view cannot make this mistake — an unsearchable field is refused when the view loads.
- **The Thai office read an English screen.** Web translations reach the client only
  through entries carrying an `odoo-javascript` (or `openerp-web`) marker
  (`odoo/tools/translate.py`, `CodeTranslations._load_web_translations`), and neither
  `finance_kmitl/i18n/th.po` nor `disbursement_finance_kmitl/i18n/th.po` had a single
  one. Every `_t()` label in both files was translated in the `.po` and none of it was
  ever delivered. A view's strings are `model_terms` and need no marker.

## Consequences

- **The three ใบขอเบิก worklists share one tree and one search view**
  (`disbursement_finance_kmitl.view_disbursement_request_queue_tree` and
  `disbursement.view_disbursement_request_search`) and differ only in the domain of the
  action that opens them. They were never three screens; they were one list stopped at
  three states.
- **That tree needs a high `priority`.** `ir.ui.view` is ordered by `(priority, name)`
  and `default_view()` takes the first primary view, so at equal priority a new tree can
  become the default list of every action that does not pin `view_id`. Same guard, same
  reason, as `disbursement.view_disbursement_request_approved_tree`.
- **All the presses live in one `<header>`, gated by `groups` alone.** A header button
  has no record to reference, so it cannot take `attrs`. They can share a header because
  each batch method filters the selection by state itself (`_payment_batch`,
  `account.move.action_submit_batch`) and reports the rows it skipped by name — a press
  only ever acts on rows at its own stage.
- **ใบล้างเจ้าหนี้ shows the finance office's own list and search**
  (`view_account_payment_tree_kmitl`, `view_account_payment_search_kmitl`) with
  `search_default_to_book`, not a second pair of views. The columns the accounting maker
  needs are the columns the treasury needed, and "what has been handed over", "what is
  awaiting approval", "what is booked" are already filters there. The default filter is
  what makes it their register rather than the whole payment ledger.
- **`account.payment` grew an `action_submit_batch` proxy.** The register lists payments
  and the thing submitted is the payment's entry; `_inherits` delegates fields, not
  methods, so the name has to exist on the payment for a list button to reach it.
- **The expandable row is gone** — the journal items of a clearing voucher, the payee
  lines of a request. Both are one press away on the form, which is where the rest of
  the work on that record already happens.
- **Two OWL queues remain and are not covered by this.** `disbursement.approval_queue`
  (round 1) and `accounting_kmitl_workflow.approval_queue` are untouched; the second is
  on the other side of a dependency wall from `disbursement` and was never in reach.

## Rejected alternatives

- **Keep the screens and fix them** — lift round 1's queue into a config-driven base and
  have all of them extend it, which was the plan this replaces. It would have given the
  expandable row for free and left the module maintaining a search bar, a filter set, a
  selection model and a translation path that Odoo ships. The fund filter would have had
  to be re-implemented as a `search=` on two computed fields to do what a search view
  does by refusing to load.
- **A tree per stage.** Three trees whose only difference is a domain, kept in step by
  hand. The action already carries the domain.
- **Keep `clearing_queue` alone, for the journal items.** One screen's worth of the same
  cost, for a detail that is one press away, on the office's register rather than on the
  treasury's — so the two offices would have looked at the same vouchers through two
  different lists with two different sets of columns.
