# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class DisbursementRequest(models.Model):
    _inherit = 'disbursement.request'

    reference = fields.Reference(
        selection_add=[('purchase.order', 'Purchase Order')],
        ondelete={'purchase.order': 'set null'},
    )

    purchase_id = fields.Many2one(
        comodel_name="purchase.order",
        string="Purchase Order",
        compute="_compute_reference_fields",
        store=True,
        index=True,
        tracking=True,
    )

    @api.depends("reference")
    def _compute_reference_fields(self):
        super()._compute_reference_fields()
        for rec in self:
            if rec.reference and rec.reference._name == 'purchase.order':
                rec.purchase_id = rec.reference
            else:
                rec.purchase_id = False

    def _get_return_source(self):
        """A PO-linked DR returns to its purchase order for correction. (A DR
        that also has a Work Acceptance is routed to the WA by the WA bridge,
        which overrides this and wins via the module dependency order.)"""
        return self.purchase_id or super()._get_return_source()

    def _compute_analytic(self):
        """Merge analytic_distribution from first PO line when reference is a PO."""
        super()._compute_analytic()
        for rec in self:
            if rec.reference and rec.reference._name == 'purchase.order':
                po = rec.reference
                for line in po.order_line:
                    if line.analytic_distribution:
                        rec.analytic_distribution = line.analytic_distribution
                        break

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
