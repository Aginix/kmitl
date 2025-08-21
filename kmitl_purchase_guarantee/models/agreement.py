# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class Agreement(models.Model):
    _inherit = 'agreement'

    purchase_guarantee_count = fields.Integer(
        string="Guarantee Count",
        compute="_compute_purchase_guarantee_count",
    )

    @api.depends("purchase_order_id", "purchase_order_id.purchase_guarantee_ids")
    def _compute_purchase_guarantee_count(self):
        for rec in self.sudo():
            if rec.purchase_order_id:
                rec.purchase_guarantee_count = len(rec.purchase_order_id.purchase_guarantee_ids)
            else:
                rec.purchase_guarantee_count = 0

    def action_view_purchase_guarantee(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "l10n_th_gov_purchase_guarantee.purchase_guarantee_action"
        )
        action["domain"] = [("purchase_id", "=", self.purchase_order_id.id)]
        action["context"] = {
            "default_reference": "purchase.order,%s" % (str(self.purchase_order_id.id),),
        }
        return action