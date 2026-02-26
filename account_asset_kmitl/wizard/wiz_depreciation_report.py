# -*- coding: utf-8 -*-
from odoo import fields, models


class WizDepreciationReport(models.TransientModel):
    _name = "wiz.depreciation.report"
    _description = "Depreciation Report Wizard"

    profile_id = fields.Many2one(
        "account.asset.profile",
        string="ประเภทครุภัณฑ์/สินทรัพย์",
    )
    source_of_asset = fields.Selection(
        [
            ("procurement", "จัดซื้อจัดจ้าง"),
            ("donation", "บริจาค"),
            ("transfer", "รับโอน"),
        ],
        string="วิธีการได้มา",
    )
    department_id = fields.Many2one(
        "hr.department",
        string="หน่วยงาน",
    )
    account_fiscal_year_id = fields.Many2one(
        "account.fiscal.year",
        string="ปีงบประมาณ",
    )
    date_from = fields.Date(string="วันที่เริ่มต้น")
    date_to = fields.Date(string="วันที่สิ้นสุด")

    def action_view_report(self):
        # Placeholder – OWL report จะ implement ทีหลัง
        return {"type": "ir.actions.act_window_close"}
