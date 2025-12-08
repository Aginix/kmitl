# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    change_ids = fields.One2many(
        comodel_name='purchase.order.change',
        inverse_name='purchase_id',
        string='Purchase Order Changes'
    )

    def action_open_purchase_order_change(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase Order Change',
            'res_model': 'purchase.order.change',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_purchase_id': self.id,
                'default_date': fields.Date.today(),
            },
        }

    def action_save_purchase_order_change(self):
        self.ensure_one()

        change_id = self.env.context.get('change_id')
        change = self.env['purchase.order.change'].browse(change_id)

        ChangeField = self.env['purchase.order.change.field'].sudo()

        track_fields = {
            'fines_rate': 'อัตราค่าปรับ',
            'fines_late': 'ค่าปรับล่าช้า',
            'late_days': 'จำนวนวันล่าช้า',
            'supervision_cost': 'ค่าควบคุมงาน',
        }

        for field_name, label in track_fields.items():
            old_value = str(self[field_name] or '')
            new_value = str(self.env.context.get(f'default_{field_name}', self[field_name]) or '')

            if old_value != new_value:

                setattr(self.sudo(), field_name, new_value)

                field_id = self.env['ir.model.fields'].search([
                    ('model', '=', 'purchase.order'),
                    ('name', '=', field_name)
                ], limit=1)

                ChangeField.create({
                    'change_id': change.id,
                    'field_id': field_id.id,
                    'field_name': label,
                    'old_value': old_value,
                    'new_value': new_value,
                })

        return {
            'type': 'ir.actions.act_window_close'
        }
