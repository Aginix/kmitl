# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class ExceptionRule(models.Model):
    _inherit = 'exception.rule'

    pr_approval_form_ids = fields.Many2many(
        comodel_name="purchase.request.approval.form",
        string="Purchase Request Approval Forms",
    )
    model = fields.Selection(
        selection_add=[
            ("purchase.request.approval.form", "Purchase request approval form"),
            ("purchase.request.approval.form.line", "Purchase request approval form line"),
        ],
        ondelete={"purchase.request.approval.form": "cascade", "purchase.request.approval.form.line": "cascade"},
    )
