# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class PurchaseRequestApprovalFormExceptionConfirm(models.TransientModel):
    _name = 'pr.form.ex.confirm'
    _description = 'Purchase Request Approval Form Exception Confirm'
    _inherit = ["exception.rule.confirm"]

    related_model_id = fields.Many2one("purchase.request.approval", "Purchase request approval form")

    def action_confirm(self):
        self.ensure_one()
        if self.ignore:
            self.related_model_id.button_draft()
            self.related_model_id.ignore_exception = True
            self.related_model_id.button_to_approve()
        return super().action_confirm()
