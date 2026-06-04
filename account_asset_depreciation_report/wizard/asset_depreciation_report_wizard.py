# -*- coding: utf-8 -*-
import base64

from odoo import _, api, fields, models


class AssetDepreciationReportWizard(models.TransientModel):
    _name = "asset.depreciation.report.wizard"
    _description = "Asset Depreciation Report Wizard"

    date = fields.Date(
        string="Date",
        required=True,
        default=fields.Date.today,
    )
    account_fiscal_year_id = fields.Many2one(
        "account.fiscal.year",
        string="Fiscal Year",
        compute="_compute_account_fiscal_year_id",
        store=True,
        readonly=True,
    )
    profile_id = fields.Many2one(
        "account.asset.profile",
        string="Asset Type",
    )
    source_of_asset = fields.Selection(
        [
            ("procurement", "Procurement"),
            ("donation", "Donation"),
            ("transfer", "Transfer"),
        ],
        string="Source of Asset",
    )
    source_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Funding Source",
        domain=[("root_plan_id.code", "=", "sources")],
    )
    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Department",
        domain=[("root_plan_id.code", "=", "departments")],
    )
    data = fields.Binary(string="Report", readonly=True)
    filename = fields.Char(string="Filename", readonly=True)

    @api.depends("date")
    def _compute_account_fiscal_year_id(self):
        for rec in self:
            if rec.date:
                fy = self.env["account.fiscal.year"].search(
                    [("date_from", "<=", rec.date), ("date_to", ">=", rec.date)],
                    limit=1,
                )
                rec.account_fiscal_year_id = fy
            else:
                rec.account_fiscal_year_id = False

    def _get_assets(self):
        domain = [("state", "in", ["open", "close"])]
        if self.profile_id:
            domain.append(("profile_id", "=", self.profile_id.id))
        if self.department_analytic_id:
            domain.append(("department_analytic_id", "=", self.department_analytic_id.id))
        if self.source_analytic_id:
            domain.append(("source_analytic_id", "=", self.source_analytic_id.id))

        assets = self.env["account.asset"].search(domain, order="number, id")

        fy = self.account_fiscal_year_id
        if fy:
            assets = assets.filtered(
                lambda a: any(
                    line.type == "depreciate"
                    and fy.date_from <= line.line_date <= fy.date_to
                    for line in a.depreciation_line_ids
                )
            )
        return assets

    def action_generate_report(self):
        self.ensure_one()
        report_model = self.env["report.asset.depreciation.xlsx"]
        xlsx_data = report_model.generate_xlsx(self)
        filename = "asset_depreciation_report.xlsx"
        self.write({"data": base64.b64encode(xlsx_data), "filename": filename})
        return {
            "type": "ir.actions.client",
            "tag": "asset_report_download",
            "params": {
                "url": f"/web/content/asset.depreciation.report.wizard/{self.id}/data/{filename}?download=true",
                "filename": filename,
            },
        }
