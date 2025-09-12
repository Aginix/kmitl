# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseGuarantee(models.Model):
    _inherit = 'purchase.guarantee'

    _STATES = [
        ("draft", "Draft"),
        ("lock", "Lock")
    ]

    state = fields.Selection(
        selection=_STATES,
        string="Status",
        index=True,
        tracking=True,
        required=True,
        copy=False,
        default="draft",
    )

    is_editable = fields.Boolean(compute="_compute_is_editable", readonly=True)

    @api.depends("state")
    def _compute_is_editable(self):
        for rec in self:
            if rec.state in (
                "lock",
            ):
                rec.is_editable = False
            else:
                rec.is_editable = True

    def button_draft(self):
        return self.write({"state": "draft"})
    
    def button_lock(self):
        return self.write({"state": "lock"})