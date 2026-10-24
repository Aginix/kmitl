# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _get_disbursement_expense_account(self):
        """GL account a disbursement line charges for this product: its own or
        its category's expense account, else the account sharing its code.
        Budget-code products (budget_product) carry the budget code, which is
        also the GL code, and often have no expense account set."""
        if not self:
            return self.env["account.account"]
        self.ensure_one()
        account = (
            self.property_account_expense_id
            or self.categ_id.property_account_expense_categ_id
        )
        if not account and self.default_code:
            account = self.env["account.account"].search(
                [
                    ("code", "=", self.default_code),
                    ("company_id", "=", self.env.company.id),
                    ("deprecated", "=", False),
                ],
                limit=1,
            )
        return account
