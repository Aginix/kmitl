from odoo import _, api, fields, models


class ApprovalRequest(models.Model):
    _inherit = "approval.request"

    # A request may back several loans — one per person who chose to borrow
    # (ADR-0003). Loans are pulled from the loan side; the request never creates
    # them, so there is no create button here. A loan is not itemized against
    # the request's Expenses: the per-row Funding Loan went with the
    # actual-expense step (agx_approval ADR-0010).
    advance_payment_ids = fields.One2many(
        comodel_name="advance.payment",
        inverse_name="approval_request_id",
        string="สัญญายืมเงิน",
        readonly=True,
        copy=False,
    )

    advance_payment_count = fields.Integer(
        compute="_compute_advance_payment_count",
    )

    @api.depends("advance_payment_ids")
    def _compute_advance_payment_count(self):
        for rec in self:
            rec.advance_payment_count = len(rec.advance_payment_ids)

    def action_view_advance_payment(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("สัญญายืมเงิน"),
            "res_model": "advance.payment",
            "view_mode": "tree,form",
            "domain": [("id", "in", self.advance_payment_ids.ids)],
            "target": "current",
        }
