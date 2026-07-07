# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountAssetBatch(models.Model):
    _name = 'account.asset.batch'
    _inherit = ['analytic.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = 'AccountAssetBatch'

    _analytic_keys = {
        "sources": "source_analytic_id",
        "departments": "department_analytic_id",
        "funds": "fund_analytic_id",
        "activities": "activity_analytic_id",
    }

    name = fields.Char(
        string="Document No.",
        tracking=True,
    )

    date = fields.Date(
        string="Acquisition Date",
        tracking=True,
        default=fields.Date.context_today,
    )

    account_fiscal_year_id = fields.Many2one(
        "account.fiscal.year",
        store=True,
        readonly=False,
        required=True,
        tracking=True,
        string="Fiscal year",
    )

    operating_unit_id = fields.Many2one(
        "operating.unit",
        string="Operating Unit",
        default=lambda self: self.env["res.users"].operating_unit_default_get(
            self.env.user.id
        ),
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
        store=True,
        readonly=False,
        default=lambda self: self.env.user.employee_id.department_id,
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
        default=lambda self: self.env.context.get('default_source_of_asset'),
    )
    
    received_from_agency = fields.Many2one(
        "res.users",
        string="received from agency",
        tracking=True,
    )

    partner_id = fields.Many2one(
        "res.partner",
        string="Partner",
        tracking=True,
    )

    source_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="แหล่งเงิน",
        compute="_compute_analytic_id",
        inverse=lambda self: self._update_analytic_distribution("sources"),
        store=True,
        readonly=False,
        domain=[("root_plan_id.code", "=", "sources")],
    )

    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="ส่วนงาน",
        compute="_compute_analytic_id",
        inverse=lambda self: self._update_analytic_distribution("departments"),
        store=True,
        readonly=False,
        domain=[("root_plan_id.code", "=", "departments")],
    )

    fund_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="กองทุน",
        compute="_compute_analytic_id",
        inverse=lambda self: self._update_analytic_distribution("funds"),
        store=True,
        readonly=False,
        domain=[("root_plan_id.code", "=", "funds")],
    )

    activity_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="ด้าน/แผนงาน/กิจกรรม",
        compute="_compute_analytic_id",
        inverse=lambda self: self._update_analytic_distribution("activities"),
        store=True,
        readonly=False,
        domain=[("root_plan_id.code", "=", "activities")],
    )

    @api.onchange('purchase_id')
    def _onchange_purchase_id_set_source(self):
        if self.purchase_id:
            self.source_of_asset = 'procurement'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                fy_id = self.env["account.fiscal.year"].browse(vals.get("account_fiscal_year_id"))
                fiscal_year = fy_id.name if fy_id else str(fields.Date.today().year)

                yearly_code = f"asset.batch.{fiscal_year}"

                seq = self.env['ir.sequence'].sudo().search(
                    [('code', '=', yearly_code)], limit=1
                )
                if not seq:
                    seq = self.env['ir.sequence'].sudo().create({
                        'name': f"Asset Batch {fiscal_year}",
                        'code': yearly_code,
                        'prefix': f"ASSET/{fiscal_year}/",
                        'padding': 4,
                        'number_next': 1,
                        'number_increment': 1,
                        'company_id': False,
                    })

                vals['name'] = seq.next_by_code(yearly_code) or 'New'

            if vals.get('purchase_id'):
                vals['source_of_asset'] = 'procurement'

        return super().create(vals_list)

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
            if purchase.operating_unit_id:
                res["operating_unit_id"] = purchase.operating_unit_id.id
            res["partner_id"] = purchase.partner_id.id
            res["analytic_distribution"] = self._asset_analytic_distribution(
                purchase.analytic_distribution
            )
            # Populate the convenience dimension fields directly so they display
            # on the fresh form (the stored compute from analytic_distribution
            # does not reliably fire for a new record).
            res.update({
                "source_analytic_id": purchase.source_analytic_id.id,
                "department_analytic_id": purchase.department_analytic_id.id,
                "fund_analytic_id": purchase.fund_analytic_id.id,
                "activity_analytic_id": purchase.activity_analytic_id.id,
            })
        return res

    def _asset_analytic_distribution(self, raw_dist):
        """Filter an analytic_distribution to the plan codes supported by
        account.asset (sources / departments / funds / activities)."""
        raw_dist = raw_dist or {}
        if not raw_dist:
            return False
        asset_keys = set(self.env["account.asset"]._analytic_keys)
        accounts = self.env["account.analytic.account"].browse(
            [int(k) for k in raw_dist]
        )
        return {
            str(aa.id): raw_dist[str(aa.id)]
            for aa in accounts
            if aa.plan_id.code in asset_keys
        } or False

    def action_register_assets(self):
        for batch in self:
            if not batch.line_ids:
                raise ValidationError(_("Cannot register assets without any lines."))

            if any(line.amount <= 0 for line in batch.line_ids):
                raise ValidationError(_("Some lines have zero amount. Please correct them before proceeding."))

            # Filter analytic_distribution to plan codes supported by account.asset
            raw_dist = (
                batch.purchase_id.analytic_distribution
                if batch.purchase_id
                else batch.analytic_distribution
            )
            analytic_distribution = batch._asset_analytic_distribution(raw_dist)

            for line in batch.line_ids:
                for _ in range(line.amount):
                    asset = self.env["account.asset"].create({
                        "name": line.name,
                        "analytic_distribution": analytic_distribution,
                        "date_start": batch.date,
                        "account_fiscal_year_id": batch.account_fiscal_year_id.id,
                        "operating_unit_id": batch.operating_unit_id.id,
                        "department_id": batch.department_id.id,
                        "purchase_id": batch.purchase_id.id if batch.purchase_id else False,
                        "partner_id": batch.partner_id.id,
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
