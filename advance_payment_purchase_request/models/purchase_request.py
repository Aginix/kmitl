import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    advance_payment_ids = fields.One2many(
        "advance.payment",
        "purchase_request_id",
        string="Advance Payments",
    )
    advance_payment_count = fields.Integer(
        compute="_compute_advance_payment_count",
    )
    hide_create_advance_payment_button = fields.Boolean(
        compute="_compute_hide_create_advance_payment_button",
    )

    @api.depends("advance_payment_ids")
    def _compute_advance_payment_count(self):
        for rec in self:
            rec.advance_payment_count = len(rec.advance_payment_ids)

    @api.depends("state", "payment_type", "advance_payment_count")
    def _compute_hide_create_advance_payment_button(self):
        for rec in self:
            rec.hide_create_advance_payment_button = not (
                rec.payment_type == "loan"
                and rec.state == "approved"
                and rec.advance_payment_count == 0
            )

    def _prepare_advance_payment_vals(self):
        self.ensure_one()
        return {
            "purchase_request_id": self.id,
            "borrower_id": self.requested_by.id,
            "department_id": self.department_id.id,
            "loan_type": "procurement",
            "loan_reason": self.description,
            "loan_amount": self.estimated_cost,
            "analytic_distribution": self.analytic_distribution,
        }

    def button_create_advance_payment(self):
        self.ensure_one()
        if self.advance_payment_count > 0:
            raise UserError(
                _("An advance payment has already been created for this request.")
            )
        advance = self.env["advance.payment"].create(
            self._prepare_advance_payment_vals()
        )
        advance_link = "/web#id=%d&model=advance.payment&view_type=form" % advance.id
        self.message_post(
            body=_(
                'Advance Payment <a href="%(link)s">%(name)s</a> created.'
            )
            % {"link": advance_link, "name": advance.name},
            subtype_xmlid="mail.mt_note",
        )
        return {
            "name": _("Advance Payment"),
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "advance.payment",
            "res_id": advance.id,
            "target": "current",
        }

    def action_view_advance_payment(self):
        self.ensure_one()
        action = {
            "name": _("Advance Payments"),
            "type": "ir.actions.act_window",
            "res_model": "advance.payment",
            "view_mode": "tree,form",
            "domain": [("purchase_request_id", "=", self.id)],
        }
        if len(self.advance_payment_ids) == 1:
            action.update({
                "view_mode": "form",
                "res_id": self.advance_payment_ids.id,
            })
        return action
