# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    purchase_guarantee_ids = fields.One2many(
        comodel_name="purchase.guarantee",
        inverse_name="request_id",
        string="Guarantee",
    )
    purchase_guarantee_count = fields.Integer(
        string="Guarantee Count",
        compute="_compute_purchase_guarantee_count",
    )

    @api.depends("purchase_guarantee_ids")
    def _compute_purchase_guarantee_count(self):
        for rec in self.sudo():
            rec.purchase_guarantee_count = len(rec.purchase_guarantee_ids)

    def action_view_purchase_guarantee(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "l10n_th_gov_purchase_guarantee.purchase_guarantee_action"
        )
        action["domain"] = [("request_id", "=", self.id)]
        action["context"] = {
            "default_reference": "purchase.request,%s" % (str(self.id),),
            "default_analytic_distribution": self.analytic_distribution
        }
        return action
