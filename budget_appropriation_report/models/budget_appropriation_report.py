# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class BudgetAppropriationReport(models.Model):
    """
    Budget Appropriation Report - Group appropriations for council presentation.

    Business Purpose:
        Groups budget appropriations into a report package for presenting
        to the institute council meeting for approval.
    """

    _name = "budget.appropriation.report"
    _description = "Budget Appropriation Report"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc, id desc"

    name = fields.Char(
        string="ชื่อรายงาน",
        required=True,
        tracking=True,
    )
    account_fiscal_year_id = fields.Many2one(
        comodel_name="account.fiscal.year",
        string="ปีงบประมาณ",
        required=True,
        tracking=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("done", "Done"),
        ],
        string="สถานะ",
        required=True,
        default="draft",
        tracking=True,
    )
    note = fields.Text(
        string="หมายเหตุ",
        tracking=True,
    )
    appropriation_ids = fields.Many2many(
        comodel_name="budget.appropriation",
        string="รายการจัดสรรงบประมาณ",
        tracking=True,
    )
    council_meeting_no = fields.Char(
        string="ครั้งที่ประชุม",
        help="เช่น 9/2567",
        tracking=True,
    )
    council_meeting_date = fields.Date(
        string="วันที่มติ",
        tracking=True,
    )
