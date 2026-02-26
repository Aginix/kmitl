# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountAssetBatch(models.Model):
    _name = 'account.asset.batch'
    _inherit = ['analytic.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = 'AccountAssetBatch'

    name = fields.Char(
        string="Document name",
        tracking=True,
        required=True
    )

    date = fields.Date(
        string="Date",
        tracking=True,
        default=fields.Date.context_today,
    )

    account_fiscal_year_id = fields.Many2one(
        "account.fiscal.year",
        related='purchase_id.account_fiscal_year_id',
        required=True,
        tracking=True,
        string="Fiscal year",
    )

    operating_unit_id = fields.Many2one(
        "operating.unit",
        string="Operating Unit",
    )

    purchase_id = fields.Many2one(
        "purchase.order"
    )

    contract_number = fields.Char(
        related='purchase_id.contract_number',
        string="Contract Number"
    )

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self:self.env.company,
    )

    notes = fields.Text(
        string="Note",
        tracking=True
    )

    state = fields.Selection(
        [("draft", "Draft"), ("done", "Done")],
        string="State",
        default="draft",
        tracking=True
    )

    line_ids = fields.One2many(
        "account.asset.batch.line",
        "batch_id",
        string="Lines"
    )

    department_id = fields.Many2one(
        "hr.department",
        string="Department",
        related="purchase_id.department_id"
    )

    asset_count = fields.Integer(
        string="Assets",
        compute="_compute_asset_count",
    )

    is_editable = fields.Boolean(
        string="Is Editable",
        compute="_compute_is_editable",
        store=False
    )

    currency_id = fields.Many2one(
        'res.currency',
        string="Currency",
        related='company_id.currency_id',
        store=True,
        readonly=True
    )

    total_amount = fields.Monetary(
        string="Total",
        compute="_compute_total_amount",
        store=True,
        currency_field='currency_id',
    )

    source_of_asset = fields.Selection(
        [
            ("procurement", "Procurement"),
            ("donation", "Donation"),
            ("transfer", "Transfer"),

        ],
        string="Source of asset",
        tracking=True,
    )
    received_from_agency = fields.Char(
        string="received from agency",
        tracking=True,
    )

    @api.onchange('purchase_id')
    def _onchange_purchase_id_set_source(self):
        if self.purchase_id:
            self.source_of_asset = 'procurement'

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if record.purchase_id:
                record.source_of_asset = 'procurement'
        return records

    @api.depends('line_ids.amount_total')
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = sum(rec.line_ids.mapped('amount_total'))

    @api.depends('state')
    def _compute_is_editable(self):
        for rec in self:
            rec.is_editable = rec.state == 'draft'

    def _compute_asset_count(self):
        for batch in self:
            batch.asset_count = self.env["account.asset"].search_count([
                ("batch_id", "=", batch.id)
            ])

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        purchase_id = self.env.context.get("default_purchase_id")
        if purchase_id:
            purchase = self.env["purchase.order"].browse(purchase_id)
            if purchase.department_id and purchase.department_id.operating_unit_id:
                res["operating_unit_id"] = purchase.department_id.operating_unit_id.id
        return res

    def action_register_assets(self):
        for batch in self:
            if not batch.line_ids:
                raise ValidationError(_("Cannot register assets without any lines."))

            if any(line.amount <= 0 for line in batch.line_ids):
                raise ValidationError(_("Some lines have zero amount. Please correct them before proceeding."))

            for line in batch.line_ids:
                for _ in range(line.amount):
                    asset = self.env["account.asset"].create({
                        "name": line.name,
                        "analytic_distribution": batch.purchase_id.analytic_distribution,
                        "date_start": batch.date,
                        "account_fiscal_year_id": batch.account_fiscal_year_id.id,
                        "operating_unit_id": batch.operating_unit_id.id,
                        "department_id": batch.department_id.id,
                        "purchase_id": batch.purchase_id.id,
                        "gpsc_id": line.gpsc_id.id,
                        "profile_id": line.profile_id.id,
                        "purchase_value": line.price_per_unit,
                        "batch_line_id": line.id,
                        "batch_id": batch.id,
                    })
            batch.state = "done"

    def action_open_asset_items(self):
        self.ensure_one()
        return {
            "name": _("Assets"),
            "type": "ir.actions.act_window",
            "res_model": "account.asset",
            "view_mode": "tree,form",
            "domain": [("batch_id", "=", self.id)],
            "context": {
                "default_batch_id": self.id
            },
        }
