# -*- coding: utf-8 -*-
from odoo import _, api, fields, models, Command
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

        order = self.env['purchase.order'].create(self._prepare_purchase_order_vals())
        self.order_id = order.id
        self.state = 'approved'

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'res_id': order.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _prepare_purchase_order_vals(self):
        return {
            'department_id': self.env.user.employee_id.department_id.id,
            'partner_id': self.vendor.id,
            'order_line': [Command.create(line._prepare_purchase_order_line_vals()) for line in self.line_ids],
            'origin': self.name,
            'contract_type': self.contract_type,
            'contract_start_date': self.start_date,
            'contract_end_date': self.end_date,
            # 'description': self.description,
            'request_id': self.request_id.id,
            'request_approval_id': self.id,
        }


class PurchaseRequestApprovalLine(models.Model):
    _inherit = 'purchase.request.approval.line'

    def _prepare_purchase_order_line_vals(self):
        if not self.product_id or not self.product_qty:
            raise UserError("Please fill all required line data.")
        return {
            'product_id': self.product_id.id,
            'name': self.description or self.product_id.display_name,
            'product_qty': self.product_qty,
            'price_unit': self.price_unit,
            'taxes_id': [(6, 0, self.taxes_id.ids)],
            'product_uom': self.product_id.uom_po_id.id,
        }
