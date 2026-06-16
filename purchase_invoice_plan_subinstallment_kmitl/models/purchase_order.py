# -*- coding: utf-8 -*-
from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_round


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    @api.depends("invoice_plan_ids")
    def _compute_ip_total(self):
        """Count only root-level installments to avoid double-counting subs."""
        for rec in self:
            installments = rec.invoice_plan_ids.filtered(
                lambda l: l.installment and not l.parent_id
            )
            rec.ip_total_percent = sum(installments.mapped("percent"))
            rec.ip_total_amount = sum(installments.mapped("amount"))

    @api.constrains("invoice_plan_ids")
    def _check_ip_total_percent(self):
        for rec in self:
            installments = rec.invoice_plan_ids.filtered(
                lambda l: l.installment and not l.parent_id
            )
            ip_total_percent = sum(installments.mapped("percent"))
            if float_round(ip_total_percent, 0) > 100:
                raise UserError(_("Invoice plan total percentage must not exceed 100%"))
