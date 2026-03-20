# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class WorkAcceptance(models.Model):
    _name = 'work.acceptance'
    _inherit = ['work.acceptance', 'thai.date.mixin']

    evaluation_result_ids = fields.One2many(
        groups="purchase_work_acceptance_evaluation.group_enable_eval_on_wa"
    )

    requested_delivery_date = fields.Date(
        string="Requested Delivery Date",
        tracking=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    def action_view_purchase_order(self):
        self.ensure_one()
        if not self.purchase_id:
            return

        return {
            'name': _('Purchase Order'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'res_id': self.purchase_id.id,
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'current',
            'context': self.env.context,
        }
