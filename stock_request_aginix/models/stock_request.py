# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class StockRequest(models.Model):
    _name = 'stock.request'
    _description = 'Stock Request'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(
        string="Reference",
        required=True,
        readonly=True,
        default=lambda self: _('New')
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ('submitted', "Submitted"),
            ("approved", "Approved"),
            ("done", "Done"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        copy=False,
        default="draft",
        index=True,
        readonly=True,
        tracking=True,
    )
    picking_type_id = fields.Many2one(
        'stock.picking.type',
        string="Picking Type",
        required=True,
        default=lambda self: self.env['stock.picking.type'].search([('code', '=', 'stock_request')], limit=1)
    )
    location_id = fields.Many2one(
        'stock.location',
        string='From Location',
        required=True,
        default=lambda self: self.env['stock.location'].search([('complete_name', '=', 'WH/Stock')], limit=1)
    )
    location_dest_id = fields.Many2one(
        'stock.location',
        string='To Location',
        required=True,
        default=lambda self: self.env['stock.location'].search([('usage', '=', 'customer')], limit=1)
    )
    request_date = fields.Datetime(
        default=fields.Datetime.now
    )
    user_id = fields.Many2one(
        'res.users',
        default=lambda self: self.env.user
    )
    responsible_id = fields.Many2one(
        'res.users',
        default=lambda self: self.env.user
    )
    request_line_ids = fields.One2many(
        'stock.request.line',
        'request_id', string='Lines'
    )
    picking_id = fields.Many2one(
        'stock.picking',
        string='Picking'
    )

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('stock.request.seq') or _('New')
        return super().create(vals)

    def action_submitted(self):
        self.state = 'submitted'

    def action_approved(self):
        self.state = 'approved'

    def action_done(self):
        self.state = 'done'

    def action_cancel(self):
        self.state = 'cancel'

    def action_reset(self):
        self.state = 'draft'

    def _prepare_picking_vals(self):
        self.ensure_one()
        return {
            'picking_type_id': self.picking_type_id.id,
            'location_id': self.location_id.id,
            'location_dest_id': self.location_dest_id.id,
            'origin': self.name,
        }
    
    def _prepare_move_vals(self, line, picking):
        return {
            'name': line.product_id.display_name or line.name or '/',
            'product_id': line.product_id.id,
            'product_uom_qty': line.quantity,
            'product_uom': line.product_uom_id.id,
            'location_id': self.location_id.id,
            'location_dest_id': self.location_dest_id.id,
            'picking_id': picking.id,
            'origin': self.name,
        }
    
    def action_create_picking(self):
        self.ensure_one()
        stock_picking = self.env['stock.picking']
        stock_move = self.env['stock.move']
        picking_vals = self._prepare_picking_vals()
        picking = stock_picking.create(picking_vals)
        
        for line in self.request_line_ids:
            move_vals = self._prepare_move_vals(line, picking)
            stock_move.create(move_vals)
            
        self.picking_id = picking.id
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Picking'),
            'res_model': 'stock.picking',
            'view_mode': 'form',
            'res_id': picking.id,
            'target': 'current',
        }
    
    def action_view_picking(self):
        self.ensure_one()
        if not self.picking_id:
            raise UserError(_("No Picking found."))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Picking'),
            'res_model': 'stock.picking',
            'view_mode': 'form',
            'res_id': self.picking_id.id,
            'target': 'current',
        }


class StockRequestLine(models.Model):
    _name = 'stock.request.line'
    _description = 'Stock Request Line'

    request_id = fields.Many2one(
        'stock.request',
        required=True,
        ondelete='cascade'
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True
    )
    quantity = fields.Float(
        string='Quantity',
        required=True
    )
    product_uom_id = fields.Many2one(
        'uom.uom',
        string='UoM',
        required=True,
        default=lambda self: self.env.ref('uom.product_uom_unit')
    )
    qty_done = fields.Float(
        string="Quantity Done",
        compute="_compute_progress",
        store=False
    )

    @api.depends('request_id.picking_id.move_ids_without_package')
    def _compute_progress(self):
        for line in self:
            done = 0.0
            moves = line.request_id.picking_id.move_ids_without_package.filtered(
                lambda m: m.product_id == line.product_id
            )
            for move in moves:
                done += move.quantity_done

            line.qty_done = done
