# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseOrderChange(models.Model):
    _name = 'purchase.order.change'
    _description = 'Purchase Order Change'

    number = fields.Integer(string='Number')
    date = fields.Date(string='Date', default=fields.Date.context_today)
    change_type = fields.Selection(selection=[('none', 'None'), ('impact', 'Impact')])
    section_ids = fields.Many2many(comodel_name="purchase.change.section")
    state = fields.Selection(selection=[("draft", "Draft"), ("done", "Done")] , default="draft")
    purchase_id = fields.Many2one(comodel_name="purchase.order")
    change_field_ids = fields.One2many(
        comodel_name='purchase.order.change.field',
        inverse_name='change_id',
        string='Change Fields'
    )

    @api.model
    def create(self, vals):
        if vals.get('number', 'New') in (False, 'New'):
            vals['number'] = self.env['ir.sequence'].next_by_code('purchase.order.change') or 'New'
        return super().create(vals)

    def action_done(self):
        for record in self:
            record.state = 'done'

    def action_next(self):
        self.ensure_one()

        return {
            "name": "Change Purchase Order",
            "type": "ir.actions.act_window",
            "res_model": "purchase.order.change.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_change_id": self.id,
                "default_purchase_id": self.purchase_id.id,
                "default_fines_rate": self.purchase_id.fines_rate,
                "default_fines_late": self.purchase_id.fines_late,
                "default_late_days": self.purchase_id.late_days,
                "default_supervision_cost": self.purchase_id.supervision_cost,
            },
        }
