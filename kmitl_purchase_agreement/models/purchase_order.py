# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    agreement_ids = fields.One2many(
        'agreement', 'purchase_order_id', string="Agreements"
    )

    agreement_count = fields.Integer(
        compute="_compute_agreement_count",
    )

    @api.depends("agreement_ids")
    def _compute_agreement_count(self):
        for rec in self:
            rec.agreement_count = len(rec.agreement_ids)

    def action_view_agreement(self):
        action = (
            self.env.ref("agreement_legal.agreement_operations_agreement")
            .sudo()
            .read()[0]
        )
        agreements = self.agreement_ids
        if len(agreements) > 1:
            action["domain"] = [("id", "in", agreements.ids)]
        elif agreements:
            action["views"] = [
                (self.env.ref("agreement_legal.partner_agreement_form_view").id, "form")
            ]
            action["res_id"] = agreements.id
        return action

    def action_create_agreement_from_po(self):
        self.ensure_one()
        agreement = self.env['agreement'].create({
            'name': f'Agreement for {self.name}',
            'partner_id': self.partner_id.id,
            'purchase_order_id': self.id,
            'company_id': self.company_id.id,
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'agreement',
            'view_mode': 'form',
            'res_id': agreement.id,
            'target': 'current',
        }