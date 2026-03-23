# -*- coding: utf-8 -*-
from odoo import fields, models


class WorkAcceptanceLine(models.Model):
    _inherit = 'work.acceptance.line'

    approval_line_id = fields.Many2one(
        'purchase.request.line',
        string='Purchase Request Approval Line',
        ondelete="set null",
        index=True,
        readonly=False,
    )
