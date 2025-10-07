# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountAssetBatch(models.Model):
    _name = 'account.asset.batch'
    _inherit = "analytic.mixin"
    _description = 'AccountAssetBatch'

    name = fields.Char(
        string="Document name",
        tracking=True,
    )

    date = fields.Date(
        string="Date",
        tracking=True,
    )

    account_fiscal_year_id = fields.Many2one(
        "account.fiscal.year",
        related='purchase_id.date_range_fy_id',
        required=True,
        tracking=True,
    )

    operating_unit_id = fields.Many2one(
        "operating.unit",
        related='purchase_id.operating_unit_id',
        string="Operating Unit",
    )

    purchase_id = fields.Many2one(
        "purchase.order"
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
    )

    line_ids = fields.One2many(
        "account.asset.batch.line",
        "batch_id",
        string="Lines"
    )

    def action_register_assets(self):
        asset = self.env["account.asset"]
        for batch in self:
            for line in batch.line_ids:
                for _ in range(line.amount):
                    asset.create({
                        "name": line.name,
                        "analytic_distribution": line.analytic_distribution,
                        "date_start": batch.date,
                        "account_fiscal_year_id": batch.account_fiscal_year_id.id,
                        "operating_unit_id": batch.operating_unit_id.id,
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