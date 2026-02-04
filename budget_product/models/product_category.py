import logging

from odoo import _, api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ProductCategory(models.Model):
    _inherit = "product.category"

    @api.ondelete(at_uninstall=False)
    def _unlink_except_default_category(self):
        super()._unlink_except_default_category()
        for rec in self:
            account_id = self.env["budget.account"].search(
                [("code", "=", rec.code)], limit=1
            )
            if account_id:
                raise UserError(
                    _(
                        "You cannot delete the %s product category.",
                        f"[{account_id.code}] {account_id.name}",
                    )
                )
        return
