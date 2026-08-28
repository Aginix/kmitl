# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ReceiptKmitlException(models.Model):
    _name = "kmitl.receipt"
    _inherit = ["kmitl.receipt", "base.exception"]

    @api.model
    def _exception_rule_eval_context(self, rec):
        res = super()._exception_rule_eval_context(rec)
        res["today"] = fields.Date.context_today(rec)
        return res

    @api.model
    def test_all_draft_orders(self):
        receipt_set = self.search([("state", "=", "draft")])
        receipt_set.detect_exceptions()
        return True

    @api.model
    def _reverse_field(self):
        return "kmitl_receipt_ids"

    def action_draft(self):
        res = super().action_draft()
        for rec in self:
            rec.exception_ids = False
            rec.main_exception_id = False
            rec.ignore_exception = False
        return res

    def action_confirm(self):
        if self.detect_exceptions() and not self.ignore_exception:
            return self._popup_exceptions()
        return super().action_confirm()

    @api.model
    def _get_popup_action(self):
        return self.env.ref(
            "receipt_kmitl_exception.action_receipt_kmitl_exception_confirm"
        )
