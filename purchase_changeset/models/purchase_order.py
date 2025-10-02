# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    changeset_ids = fields.One2many(
        comodel_name="changeset",
        inverse_name="purchase_id",
        string="Line test",
    )
    def action_open_committee_wizard(self):
        self.ensure_one()
        return self.env['purchase.committee.wizard'].action_open_wizard(self.id)
