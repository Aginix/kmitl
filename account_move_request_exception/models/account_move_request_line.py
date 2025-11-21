# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AccountMoveRequestLine(models.Model):
    _inherit = ["account.move.request.line", "base.exception.method"]
    _name = "account.move.request.line"

    ignore_exception = fields.Boolean(
        related="request_id.ignore_exception", store=True, string="Ignore Exceptions"
    )

    def _get_main_records(self):
        return self.mapped("request_id")

    @api.model
    def _reverse_field(self):
        return "move_request_ids"

    def _detect_exceptions(self, rule):
        records = super()._detect_exceptions(rule)
        return records.mapped("request_id")
