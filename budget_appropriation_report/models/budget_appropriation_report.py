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

    READONLY_STATES = {
        "confirmed": [("readonly", True)],
        "done": [("readonly", True)],
    }

    name = fields.Char(
        string="ชื่อรายงาน",
        required=True,
        tracking=True,
        readonly=False,
        states=READONLY_STATES,
    )
    account_fiscal_year_id = fields.Many2one(
        comodel_name="account.fiscal.year",
        string="ปีงบประมาณ",
        required=True,
        tracking=True,
        readonly=False,
        states=READONLY_STATES,
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
        readonly=True,
    )
    note = fields.Text(
        string="หมายเหตุ",
        tracking=True,
        readonly=False,
        states=READONLY_STATES,
    )
    appropriation_ids = fields.Many2many(
        comodel_name="budget.appropriation",
        string="รายการจัดสรรงบประมาณ",
        tracking=True,
        readonly=False,
        states=READONLY_STATES,
    )
    council_meeting_no = fields.Char(
        string="ครั้งที่ประชุม",
        help="เช่น 9/2567",
        tracking=True,
        readonly=False,
        states=READONLY_STATES,
    )
    council_meeting_date = fields.Date(
        string="วันที่มติ",
        tracking=True,
        readonly=False,
        states=READONLY_STATES,
    )
    appropriation_count = fields.Integer(
        string="จำนวนรายการ",
        compute="_compute_appropriation_count",
    )

    @api.depends("appropriation_ids")
    def _compute_appropriation_count(self):
        for record in self:
            record.appropriation_count = len(record.appropriation_ids)

    def action_confirm(self):
        self.write({"state": "confirmed"})

    def action_done(self):
        self.write({"state": "done"})

    def action_draft(self):
        self.write({"state": "draft"})

    def action_open_report(self):
        """Open the report in a new blank page."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": f"/budget_appropriation_report/{self.id}/html",
            "target": "new",
        }

    def action_print_pdf(self):
        """Print the PDF report."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": f"/budget_appropriation_report/{self.id}/pdf",
            "target": "new",
        }

    def action_view_appropriations(self):
        """Open list of appropriations linked to this report."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("รายการจัดสรรงบประมาณ"),
            "res_model": "budget.appropriation",
            "view_mode": "tree,form",
            "domain": [("id", "in", self.appropriation_ids.ids)],
            "context": {"default_account_fiscal_year_id": self.account_fiscal_year_id.id},
        }
