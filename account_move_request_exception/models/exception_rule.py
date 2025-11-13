# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class ExceptionRule(models.Model):
    _inherit = 'exception.rule'

    move_request_ids = fields.Many2many(
        comodel_name="account.move.request",
        string="Account Move Requests",
    )
    model = fields.Selection(
        selection_add=[
            ("account.move.request", "Account Move Requests"),
            ("account.move.request.line", "Account Move Requests line"),
        ],
        ondelete={"account.move.request": "cascade", "account.move.request.line": "cascade"},
    )
