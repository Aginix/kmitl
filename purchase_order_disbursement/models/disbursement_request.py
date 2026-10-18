# -*- coding: utf-8 -*-
from odoo import _, fields, models
from odoo.exceptions import UserError


class DisbursementRequest(models.Model):
    _inherit = 'disbursement.request'

    purchase_id = fields.Many2one(
        comodel_name="purchase.order",
        string="Purchase Order",
        readonly=True,
        copy=False,
        index=True,
        tracking=True,
        ondelete="set null",
    )

    def _get_source_document(self):
        return self.purchase_id or super()._get_source_document()

    def _get_return_source(self):
        """A PO-linked DR returns to its purchase order for correction. (A DR
        that also has a Work Acceptance is routed to the WA by the WA bridge,
        which overrides this and wins via the module dependency order.)"""
        return self.purchase_id or super()._get_return_source()

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
