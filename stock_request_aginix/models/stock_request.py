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
            ('requested', "Requested"),
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
        required=True
    )
    location_id = fields.Many2one(
        'stock.location', 
        string='From Location', 
        required=True
    )
    location_dest_id = fields.Many2one(
        'stock.location', 
        string='To Location', 
        required=True
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

    def action_requested(self):
        self.state = 'requested'

    def action_approved(self):
        self.state = 'approved'

    def action_done(self):
        self.state = 'done'


    def action_create_picking(self):
        self.ensure_one()

        StockPicking = self.env['stock.picking']
        StockMove = self.env['stock.move']

        picking = StockPicking.create({
            'picking_type_id': self.picking_type_id.id,
            'location_id': self.location_id.id,
            'location_dest_id': self.location_dest_id.id,
            'origin': self.name,
        })

        for line in self.request_line_ids:
            StockMove.create({
                'name': line.product_id.display_name,
                'product_id': line.product_id.id,
                'product_uom_qty': line.quantity,
                'product_uom': line.product_uom_id.id,
                'location_id': self.location_id.id,
                'location_dest_id': self.location_dest_id.id,
                'picking_id': picking.id,
            })

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
    description = fields.Text(
        string="Description",
        store=True,
        readonly=False,
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
    qty_in_progress = fields.Float(
        string="Quantity In Progress",
        compute="_compute_progress",
        store=False
    )
    picking_state = fields.Selection(
        related='request_id.picking_id.state',
        string="Picking State",
        store=False,
        readonly=True
    )

    @api.depends('request_id.picking_id.move_ids_without_package')
    def _compute_progress(self):
        for line in self:
            done = 0.0
            in_progress = 0.0
            moves = line.request_id.picking_id.move_ids_without_package.filtered(
                lambda m: m.product_id == line.product_id
            )
            for move in moves:
                done += move.quantity_done
                if move.state not in ['done', 'cancel']:
                    in_progress += (move.product_uom_qty - move.quantity_done)

            line.qty_done = done
            line.qty_in_progress = in_progress
