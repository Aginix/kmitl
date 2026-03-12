from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError


class PurchaseGuarantee(models.Model):
    _inherit = "purchase.guarantee"

    disbursement_request_ids = fields.One2many(
        comodel_name="disbursement.request",
        inverse_name="guarantee_id",
        string="Disbursement Requests",
    )
    disbursement_request_count = fields.Integer(
        compute="_compute_disbursement_request",
    )
    is_disbursement_refund_allowed = fields.Boolean(
        compute="_compute_disbursement_request",
    )
    hide_create_disbursement_button = fields.Boolean(
        compute="_compute_hide_create_disbursement_button",
    )

    @api.depends("disbursement_request_ids", "amount", "amount_returned")
    def _compute_disbursement_request(self):
        for rec in self:
            rec.disbursement_request_count = len(rec.disbursement_request_ids)
            rec.is_disbursement_refund_allowed = (rec.amount - rec.amount_returned) > 0

    @api.depends("state", "is_disbursement_refund_allowed")
    def _compute_hide_create_disbursement_button(self):
        for rec in self:
            rec.hide_create_disbursement_button = (
                rec.state != "lock" or not rec.is_disbursement_refund_allowed
            )

    def _prepare_disbursement_request_vals(self):
        self.ensure_one()
        return {
            "guarantee_id": self.id,
            "partner_id": self.partner_id.id,
            "ref": self.name,
            "analytic_distribution": self.analytic_distribution,
            "line_ids": [
                Command.create(
                    {
                        "name": _("คืนเงินหลักประกัน - %s") % self.guarantee_method_id.name,
                        "account_id": self.guarantee_method_id.account_id.id,
                        "quantity": 1.0,
                        "price_unit": self.amount - self.amount_returned,
                        "analytic_distribution": self.analytic_distribution,
                    }
                )
            ],
        }

    def action_create_disbursement_refund(self):
        self.ensure_one()
        if self.amount - self.amount_returned <= 0:
            raise UserError(_("ไม่มียอดเงินหลักประกันคงเหลือที่จะคืน"))
        disbursement = self.env["disbursement.request"].create(
            self._prepare_disbursement_request_vals()
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": "disbursement.request",
            "res_id": disbursement.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_view_disbursement_requests(self):
        self.ensure_one()
        requests = self.disbursement_request_ids
        if len(requests) == 1:
            return {
                "type": "ir.actions.act_window",
                "name": _("Disbursement Request"),
                "res_model": "disbursement.request",
                "res_id": requests.id,
                "view_mode": "form",
                "target": "current",
            }
        return {
            "type": "ir.actions.act_window",
            "name": _("Disbursement Requests"),
            "res_model": "disbursement.request",
            "view_mode": "tree,form",
            "domain": [("id", "in", requests.ids)],
            "target": "current",
        }
