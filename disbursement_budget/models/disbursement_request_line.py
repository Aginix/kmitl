# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, models


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
        return super().create(vals_list)

    # A new row's first onchange runs this too (account_id is in the line
    # list), so the row opens on the budget code's own account.
    @api.onchange("account_id")
    def _onchange_default_budget_account(self):
        if self.account_id:
            return
        self.account_id = self.request_id._budget_account_default_account()
        if not self.name:
            self.name = self.account_id.name
