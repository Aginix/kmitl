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
        default='New',
        readonly=True
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ('requested', "Requested"),
            ("confirmed", "Confirmed"),
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
    request_line_ids = fields.One2many(
        'stock.request.line', 
        'request_id', string='Lines'
    )
    picking_id = fields.Many2one(
        'stock.picking',
        string='Picking'
    )

    def action_requested(self):
        if self.picking_id:
            self.picking_id.button_validate()
        self.state = 'done'

    def action_confirm(self):
        StockPicking = self.env['stock.picking']
        StockMove = self.env['stock.move']

        for request in self:
            picking = StockPicking.create({
                'picking_type_id': request.picking_type_id.id,
                'location_id': request.location_id.id,
                'location_dest_id': request.location_dest_id.id,
                'origin': request.name,
            })

            for line in request.request_line_ids:
                StockMove.create({
                    'name': line.product_id.display_name,
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.quantity,
                    'product_uom': line.product_uom_id.id,
                    'location_id': request.location_id.id,
                    'location_dest_id': request.location_dest_id.id,
                    'picking_id': picking.id,
                })

            request.picking_id = picking.id
            request.state = 'confirmed'

    def action_done(self):
        if self.picking_id:
            self.picking_id.button_validate()
        self.state = 'done'


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
