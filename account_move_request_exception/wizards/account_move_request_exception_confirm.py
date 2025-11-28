# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AccountMoveRequestExceptionConfirm(models.TransientModel):
    _name = 'account.move.request.exception.confirm'
    _description = "Account Move request exception wizard"
    _inherit = ["exception.rule.confirm"]

    related_model_id = fields.Many2one("account.move.request", "Account Move request")

    def action_confirm(self):
        self.ensure_one()
        if self.ignore:
            self.related_model_id.action_draft()
            self.related_model_id.ignore_exception = True
            self.related_model_id.action_submit()
        return super().action_confirm()
