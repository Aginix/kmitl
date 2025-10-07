# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseAssetBatchLine(models.Model):
    _name = 'purchase.asset.batch.line'
    _inherit = "analytic.mixin"
    _description = 'PurchaseAssetBatchLine'

    name = fields.Char(
        string="Name",
        required=True,
        tracking=True
    )

    sequence = fields.Integer(
        default=1
    )
    
    batch_id = fields.Many2one(
        related='account.asset.batch',
        required=True,
        index=True
    )

    account_fiscal_year_id = fields.Many2one(
        related='batch_id.account_fiscal_year_id'
    )

    purchase_id = fields.Many2one(
        related='purchase.order'
    )

    gpsc_id = fields.Many2one(
        string="GPSC Number",
        related='procurement.gpsc',
        required=True,
        tracking=True
    )

    department_id = fields.Many2one(
        related='batch_id.department_id'
    )

    profile_id = fields.Many2one(
        string="Asset Profile",
        related='account.asset.profile',
        required=True,
        tracking=True
    )

    amount = fields.Integer(
        string="Amount",
        required=True,
        tracking=True
    )

    location = fields.Char(
        string="Location",
    )

    price_per_unit = fields.Float(
        required=True,
        tracking=True
    )

    amount_total = fields.Float(
        string = "Total",
        computed="_compute_amount_total",
        tracking=True
    )

    notes = fields.Text()

    @api.depends("amount", "price_per_unit")
    def _compute_amount_total(self):
        for line in self:
            line.amount_total = line.amount * line.price_per_unit