# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class TierDefinition(models.Model):
    _inherit = 'tier.definition'

    has_approve_comment = fields.Boolean(string="Approve Comment", default=False)
    has_reject_comment = fields.Boolean(string="Reject Comment", default=False)

    @api.onchange("has_comment")
    def _onchange_has_comment(self):
        for rec in self:
            if rec.has_comment:
                rec.has_approve_comment = True
                rec.has_reject_comment = True
            else:
                rec.has_approve_comment = False
                rec.has_reject_comment = False

    @api.onchange("has_approve_comment", "has_reject_comment")
    def _onchange_approve_reject_comment(self):
        for rec in self:
            if not rec.has_approve_comment and not rec.has_reject_comment:
                rec.has_comment = False
            else:
                rec.has_comment = True
