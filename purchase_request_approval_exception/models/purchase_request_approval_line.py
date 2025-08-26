# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class PurchaseRequestApprovalLine(models.Model):
    _inherit = ["purchase.request.approval.line", "base.exception.method"]
    _name = "purchase.request.approval.line"

    ignore_exception = fields.Boolean(
        related="approval_id.ignore_exception", store=True, string="Ignore Exceptions"
    )

    def _get_main_records(self):
        return self.mapped("approval_id")

    @api.model
    def _reverse_field(self):
        return "approval_ids"

    def _detect_exceptions(self, rule):
        records = super()._detect_exceptions(rule)
        return records.mapped("approval_id")
