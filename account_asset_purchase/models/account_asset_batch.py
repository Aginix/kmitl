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
        related='accouint.fiscal.year',
        required=True,
        tracking=True,
    )

    department_id = fields.Many2one(
        related='hr.department',
        required=True,
        tracking=True,
    )

    purchase_id = fields.Many2one(
        related='purchase.order'
    )

    company_id = fields.Many2one(
        related='res.company',
        required=True,
        default=lambda self:self.env.comany,
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

    def action_register_assets(self):
        Asset = self.env["account.asset"]
        for batch in self:
            for line in batch.line_ids:
                for _ in range(line.amount):
                    Asset.create({
                        "name": line.name,
                        "analytic_distribution": line.analytic_distribution,
                        "account_fiscal_year_id": batch.account_fiscal_year_id.id,
                        "department_id": batch.department_id.id,
                        "purchase_id": batch.purchase_id.id,
                        "gpsc_id": line.gpsc_id.id,
                        "profile_id": line.profile_id.id,
                        "original_value": line.price_per_unit,
                        "batch_line_id": line.id,
                        "batch_id": batch.id,
                    })
            batch.state = "done"