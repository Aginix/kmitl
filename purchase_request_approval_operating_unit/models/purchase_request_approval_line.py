# -*- coding: utf-8 -*-

from odoo import _, api, fields, models


class PurchaseRequestApprovalLine(models.Model):
    _inherit = 'purchase.request.approval.line'

    operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
        related="approval_id.operating_unit_id",
        string="Operating Unit",
    )
