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
        default=lambda self: _('New'),
        tracking=True
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
        default=lambda self: self.env['stock.picking.type'].search([('code', '=', 'outgoing')], limit=1),
        tracking=True
    )
    location_id = fields.Many2one(
        'stock.location',
        string='From Location',
        required=True,
        default=lambda self: self.env['stock.location'].search([('complete_name', '=', 'WH/Stock')], limit=1),
        tracking=True
    )
    location_dest_id = fields.Many2one(
        'stock.location',
        string='To Location',
        required=True,
        default=lambda self: self.env['stock.location'].search([('usage', '=', 'customer')], limit=1),
        tracking=True
    )
    request_date = fields.Date(
        default=fields.Date.today,
        tracking=True,
        copy=False
    )
    user_id = fields.Many2one(
        'res.users',
        default=lambda self: self.env.user,
        tracking=True,
        readonly=True,
        copy=False
    )
    requested_by = fields.Many2one(
        'res.partner',
        default=lambda self: self.env.user,
        tracking=True
    )
    request_line_ids = fields.One2many(
        'stock.request.line',
        'request_id', 
        string='Lines'
    )
    picking_id = fields.Many2one(
        'stock.picking',
        string='Picking'
    )
    is_editable = fields.Boolean(
        string="Is Editable",
        compute="_compute_is_editable",
        store=False
    )

    @api.model
    def create(self, vals):
        if vals.get('name') in [False, _('New')]:
            vals['name'] = _('New')
        return super().create(vals)

    def action_submitted(self):
        for rec in self:
            if rec.name == _('New'):
                rec.name = self.env['ir.sequence'].next_by_code('stock.request.seq') or _('New')
            rec.state = 'submitted'

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
            'partner_id': self.requested_by.id,
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
    
    def copy(self, default=None):
        default = dict(default or {})
        default['name'] = _('New')
        default['state'] = 'draft'
        default['picking_id'] = False
        return super().copy(default)
    
    @api.depends('state')
    def _compute_is_editable(self):
        for rec in self:
            rec.is_editable = rec.state == 'draft'


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
        domain="[('type', '=', 'product')]",
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
    valuation_layer_id = fields.Many2one(
        'stock.valuation.layer',
        string='Valuation Layer',
        compute='_compute_valuation_layer',
        store=False
    )
    price_unit = fields.Float(
        string='Unit Price',
        compute='_compute_price_from_valuation',
        store=False
    )
    
    total_price = fields.Float(
        string='Total Price',
        compute='_compute_total_price_from_valuation',
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

    @api.depends('product_id', 'request_id.picking_id')
    def _compute_valuation_layer(self):
        for line in self:
            if not line.product_id or not line.request_id.picking_id:
                line.valuation_layer_id = False
                continue

            moves = line.request_id.picking_id.move_ids_without_package.filtered(
                lambda m: m.product_id == line.product_id
            )
            
            if not moves:
                line.valuation_layer_id = False
                continue

            valuation_layer = self.env['stock.valuation.layer'].search([
                ('stock_move_id', 'in', moves.ids)
            ], order='create_date asc', limit=1)
            
            line.valuation_layer_id = valuation_layer if valuation_layer else False

    @api.depends('valuation_layer_id', 'qty_done')
    def _compute_price_from_valuation(self):
        for line in self:
            if line.valuation_layer_id and line.valuation_layer_id.quantity != 0:
                line.price_unit = abs(line.valuation_layer_id.value / line.valuation_layer_id.quantity)
            else:
                line.price_unit = 0.0

    @api.depends('valuation_layer_id', 'qty_done')
    def _compute_total_price_from_valuation(self):
        for line in self:
            if line.valuation_layer_id:
                if line.valuation_layer_id.quantity != 0:
                    ratio = line.qty_done / abs(line.valuation_layer_id.quantity)
                    line.total_price = abs(line.valuation_layer_id.value) * ratio
                else:
                    line.total_price = 0.0
            else:
                line.total_price = 0.0