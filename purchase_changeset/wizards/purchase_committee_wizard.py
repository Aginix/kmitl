# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseCommitteeWizard(models.TransientModel):
    _name = 'purchase.committee.wizard'
    _description = _('PurchaseCommitteeWizard')

    purchase_id = fields.Many2one(
        comodel_name="purchase.order",
        string="Purchase Request",
        ondelete="cascade",
        index=True,
    )
    changeset_id = fields.Many2one(
        comodel_name="changeset",
        string="Purchase Request",
        ondelete="cascade",
        index=True,
    )
    partner_ref = fields.Char('Vendor Reference', copy=False,
        help="Reference of the sales order or bid sent by the vendor. "
             "It's used to do the matching when you receive the "
             "products as this reference is usually written on the "
             "delivery order sent by your vendor.")

    @api.model
    def action_open_wizard(self, purchase_id):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase Committee Wizard',
            'res_model': 'purchase.committee.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_purchase_id': purchase_id},
        }

    def action_confirm(self):

        for wizard in self:
            wizard.changeset_id.create({"wizard_id": wizard.id})
            wizard.purchase_id.write({'partner_ref': wizard.partner_ref})

        return {'type': 'ir.actions.act_window_close'}

