# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, models
from odoo.exceptions import UserError


class DisbursementRequestLine(models.Model):
    _inherit = "disbursement.request.line"

    # A line without an account takes the one sharing its request's budget code;
    # the user may still pick another one.
    @api.model_create_multi
    def create(self, vals_list):
        Request = self.env["disbursement.request"]
        for vals in vals_list:
            if not vals.get("account_id") and vals.get("request_id"):
                request = Request.browse(vals["request_id"])
                account = request._budget_account_default_account()
                vals["account_id"] = account.id
                vals.setdefault("name", account.name)
        self._check_budget_not_consumed(Request.browse(
            [vals["request_id"] for vals in vals_list if vals.get("request_id")]
        ))
        return super().create(vals_list)

    def write(self, vals):
        # The consumed amount is the request's total, taxes included.
        if {"amount", "tax_ids"} & set(vals):
            self._check_budget_not_consumed(self.request_id)
        return super().write(vals)

    def unlink(self):
        self._check_budget_not_consumed(self.request_id)
        return super().unlink()

    @api.model
    def _check_budget_not_consumed(self, requests):
        """The budget was consumed for the request's amount: its lines cannot be
        added, removed or re-priced until the request is cancelled, or the ledger
        and the bills would disagree."""
        if requests.filtered("budget_consumed_amount"):
            raise UserError(
                _(
                    "The budget of this request is already consumed for its "
                    "amount: its lines can no longer be added, removed or "
                    "re-priced. Cancel the request to release the budget."
                )
            )

    # A new row's first onchange runs this too (account_id is in the line
    # list), so the row opens on the budget code's own account.
    @api.onchange("account_id")
    def _onchange_default_budget_account(self):
        if self.account_id:
            return
        self.account_id = self.request_id._budget_account_default_account()
        if not self.name:
            self.name = self.account_id.name
