# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class PurchaseRequestApprovalExceptionConfirm(models.TransientModel):
    _name = 'purchase.request.approval.exception.confirm'
    _description = 'Purchase Request Approval Exception Confirm'
    _inherit = ["exception.rule.confirm"]

    related_model_id = fields.Many2one("purchase.request.approval", "Purchase request approval")

    def action_confirm(self):
        self.ensure_one()
        if self.ignore:
            self.related_model_id.button_draft()
            self.related_model_id.ignore_exception = True
            self.related_model_id.button_submit()
        return super().action_confirm()
