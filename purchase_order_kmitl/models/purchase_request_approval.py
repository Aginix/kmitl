# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PurchaseRequestApproval(models.Model):
    _inherit = 'purchase.request.approval'

    order_id = fields.Many2one(
        "purchase.order",
        string="Purchase Orders"
    )
    hide_create_po_button = fields.Boolean(compute="_compute_hide_create_po_button")

    @api.depends('state', 'order_id')
    def _compute_hide_create_po_button(self):
        for rec in self:
            show = rec.state == 'approved' and not rec.order_id
            rec.hide_create_po_button = not show

    def make_purchase_order(self):
        self.ensure_one()

        if self.state != 'approved':
            raise UserError("This PR2 is not ready for PO. Please approve first.")

        if not self.vendor:
            raise UserError("Vendor is required.")

        order_lines = []
        for line in self.line_ids:
            if not line.product_id or not line.product_qty:
                raise UserError("Please fill all required line data.")
            order_lines.append((0, 0, {
                'product_id': line.product_id.id,
                'name': line.description or line.product_id.display_name,
                'product_qty': line.product_qty,
                'price_unit': line.price_unit,
                'taxes_id': [(6, 0, line.taxes_id.ids)],
                'product_uom': line.product_id.uom_po_id.id,
            }))

        order = self.env['purchase.order'].create({
            'department_id': self.env.user.employee_id.department_id.id,
            'partner_id': self.vendor.id,
            'order_line': order_lines,
            'origin': self.name,
            'contract_type' : self.contract_type,
            'contract_start_date': self.start_date,
            'contract_end_date': self.end_date,
            'purchase_request_name': self.purchase_request_name,
            'request_id': self.request_id.id,
            'approval_id': self.id,
        })
        self.order_id = order.id
        self.state = 'approved'

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'res_id': order.id,
            'view_mode': 'form',
            'target': 'current',
        }
