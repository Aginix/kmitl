# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


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

    @api.constrains(
        "date",
        "partner_id",
        "is_walkin",
        "payment_type",
        "payment_method_id",
        "department_analytic_id",
        "fund_analytic_id",
        "source_analytic_id",
        "activity_analytic_id",
        "analytic_distribution",
        "amount_total",
        "line_ids",
        "ignore_exception",
    )
    def _check_receipt_blocking_exceptions(self):
        """Detect exceptions on save and block only for *blocking* rules.

        The receipt no longer has a confirm step (numbers are minted at
        creation), so exception rules are evaluated whenever the receipt is
        created or edited. Non-blocking exceptions are still detected and
        stored on ``exception_ids`` for visibility, but do not prevent
        saving — only ``is_blocking`` rules raise.
        """
        exception_ids = self.detect_exceptions()
        if not exception_ids:
            return
        blocking = (
            self.env["exception.rule"].browse(exception_ids).filtered("is_blocking")
        )
        if blocking:
            raise ValidationError(
                _("This receipt cannot be saved due to blocking exception(s):\n%s")
                % "\n".join("- %s" % name for name in blocking.mapped("name"))
            )

    def action_draft(self):
        res = super().action_draft()
        for rec in self:
            rec.exception_ids = False
            rec.main_exception_id = False
            rec.ignore_exception = False
        return res
