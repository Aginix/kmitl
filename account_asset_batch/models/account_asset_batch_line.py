# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountAssetBatchLine(models.Model):
    _name = 'account.asset.batch.line'
    _inherit = ['analytic.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = 'AccountAssetBatchLine'

    name = fields.Char(
        string="Name",
        store=True,
        tracking=True,
    )

    sequence = fields.Integer(
        default=1
    )

    batch_id = fields.Many2one(
        "account.asset.batch",
        required=True,
        index=True
    )

    account_fiscal_year_id = fields.Many2one(
        related='batch_id.account_fiscal_year_id',
        string="Fiscal year",
    )

    purchase_id = fields.Many2one(
        "purchase.order"
    )

    gpsc_id = fields.Many2one(
        "procurement.gpsc",
        string="GPSC Id",
        required=True,
        tracking=True
    )

    operating_unit_id = fields.Many2one(
        "operating.unit",
        related="batch_id.operating_unit_id",
    )

    profile_id = fields.Many2one(
        "account.asset.profile",
        string="Asset Profile",
        required=True,
        tracking=True
    )

    amount = fields.Integer(
        string="Amount",
        required=True,
        tracking=True
    )

    price_per_unit = fields.Float(
        required=True,
        tracking=True
    )

    amount_total = fields.Float(
        string = "Total",
        compute="_compute_amount_total",
        tracking=True
    )

    notes = fields.Text()

    is_editable = fields.Boolean(
        related='batch_id.is_editable',
        string="Is Editable",
        store=False
    )

    @api.constrains("amount")
    def _check_amount_positive(self):
        for record in self:
            if record.amount <= 0:
                raise ValidationError(_("Amount must be greater than zero."))

    @api.depends("amount", "price_per_unit")
    def _compute_amount_total(self):
        for rec in self:
            rec.amount_total = rec.amount * rec.price_per_unit

    def unlink(self):
        for line in self:
            assets = self.env["account.asset"].search([("batch_line_id", "=", line.id)])
            if assets:
                raise UserError(_("Cannot delete a line already linked to assets."))
        return super().unlink()
