from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ApprovalRequest(models.Model):
    _inherit = "approval.request"

    # A request may back several loans — one per person who chose to borrow
    # (ADR-0003). Loans are pulled from the loan side; the request never creates
    # them, so there is no create button here.
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

    show_create_disbursement_button = fields.Boolean(
        compute="_compute_show_create_disbursement_button",
    )

    @api.depends("advance_payment_ids")
    def _compute_advance_payment_count(self):
        for rec in self:
            rec.advance_payment_count = len(rec.advance_payment_ids)

    @api.depends("state", "has_active_disbursement")
    def _compute_show_create_disbursement_button(self):
        """เงินยืม rows never enter a disbursement (ADR-0002), so the direct and
        prepaid recipients must not be gated on anyone's loan state (ADR-0003)."""
        for rec in self:
            rec.show_create_disbursement_button = (
                rec.state == "to_disburse" and not rec.has_active_disbursement
            )

    @api.constrains("allocation_ids", "state")
    def _check_advance_rows_have_funding_loan(self):
        """Billing an `advance` row without naming the loan it came out of would
        claim payment from a สัญญายืม that may not exist (ADR-0003)."""
        for rec in self.filtered(lambda r: r.state == "billed"):
            orphans = rec.allocation_ids.filtered(
                lambda a: a.payment_type == "advance" and not a.advance_payment_id
            )
            if orphans:
                raise ValidationError(
                    _("กรุณาระบุสัญญายืมเงินที่เป็นแหล่งเงินของทุกแถวเงินยืมก่อนส่งเบิก: %s")
                    % ", ".join(orphans.mapped("partner_id.name"))
                )

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
