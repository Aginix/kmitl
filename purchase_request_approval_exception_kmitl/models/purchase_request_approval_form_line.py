# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class PurchaseRequestApprovalFormLine(models.Model):
    _inherit = ["purchase.request.approval.form.line", "base.exception.method"]
    _name = "purchase.request.approval.form.line"

    ignore_exception = fields.Boolean(
        related="pr2_id.ignore_exception", store=True, string="Ignore Exceptions"
    )

    def _get_main_records(self):
        return self.mapped("pr2_id")

    @api.model
    def _reverse_field(self):
        return "pr_approval_form_ids"

    def _detect_exceptions(self, rule):
        records = super()._detect_exceptions(rule)
        return records.mapped("pr2_id")
