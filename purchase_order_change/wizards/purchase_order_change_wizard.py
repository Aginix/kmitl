# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseOrderChangeWizard(models.TransientModel):
    _name = 'purchase.order.change.wizard'
    _description = _('PurchaseOrderChangeWizard')

    purchase_id = fields.Many2one("purchase.order", string="Purchase Order")
    fines_rate = fields.Monetary(string="Fines Rate")
    fines_late = fields.Monetary(string="Fines Amount")
    late_days = fields.Integer(string="Late Days")
    supervision_cost = fields.Monetary(string="Supervision Cost")
    currency_id = fields.Many2one(
        "res.currency",
        related="purchase_id.currency_id",
        readonly=True
    )

    def action_save_changes(self):
        self.ensure_one()
        po = self.purchase_id.sudo()

        po.write({
            "fines_rate": self.fines_rate,
            "fines_late": self.fines_late,
            "late_days": self.late_days,
            "supervision_cost": self.supervision_cost,
        })

        return {"type": "ir.actions.act_window_close"}
