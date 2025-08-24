# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class ExceptionRule(models.Model):
    _inherit = 'exception.rule'

    approval_ids = fields.Many2many(
        comodel_name="purchase.request.approval",
        string="Purchase Request Approval",
    )
    model = fields.Selection(
        selection_add=[
            ("purchase.request.approval", "Purchase request approval"),
            ("purchase.request.approval.line", "Purchase request approval line"),
        ],
        ondelete={"purchase.request.approval": "cascade", "purchase.request.approval.line": "cascade"},
    )
