# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class DisbursementRequest(models.Model):
    _inherit = 'disbursement.request'

    purchase_id = fields.Many2one(
        comodel_name="purchase.order",
        string="Purchase Order",
        ondelete="set null",
        index=True,
        tracking=True,
    )

    def action_view_purchase_order(self):
        self.ensure_one()
        if not self.purchase_id:
            raise UserError(_('No Purchase Order linked to this request.'))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Purchase Order'),
            'res_model': 'purchase.order',
            'res_id': self.purchase_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
