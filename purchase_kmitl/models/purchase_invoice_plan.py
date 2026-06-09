# -*- coding: utf-8 -*-
import logging
from datetime import timedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class PurchaseInvoicePlan(models.Model):
    _inherit = "purchase.invoice.plan"

    duration_days = fields.Integer(string="Duration (Days)")
    plan_date = fields.Date(required=False)

    @api.onchange("duration_days")
    def _onchange_duration_days(self):
        if self.duration_days and self.purchase_id.work_start:
            self.plan_date = self.purchase_id.work_start + timedelta(
                days=self.duration_days
            )

    @api.depends("percent")
    def _compute_amount(self):
        for rec in self:
            amount_total = rec.purchase_id._origin.amount_total
            # With invoice already created, no recompute
            if rec.invoiced:
                rec.amount = rec.amount_invoiced
                rec.percent = rec.amount / amount_total * 100
                continue
            # For last line, amount is the left over
            if rec.last:
                installments = rec.purchase_id.invoice_plan_ids.filtered(
                    lambda l: l.invoice_type == "installment"
                )
                prev_amount = sum((installments - rec).mapped("amount"))
                rec.amount = amount_total - prev_amount
                continue
            rec.amount = rec.percent * amount_total / 100

    @api.onchange("amount", "percent")
    def _inverse_amount(self):
        for rec in self:
            if rec.purchase_id.amount_total != 0:
                if rec.last:
                    installments = rec.purchase_id.invoice_plan_ids.filtered(
                        lambda l: l.invoice_type == "installment"
                    )
                    prev_percent = sum((installments - rec).mapped("percent"))
                    rec.percent = 100 - prev_percent
                    continue
                rec.percent = rec.amount / rec.purchase_id.amount_total * 100
                continue
            rec.percent = 0

    def _get_amount_invoice(self, invoices):
        """Hook function"""
        return sum(invoices.mapped("amount_total"))
