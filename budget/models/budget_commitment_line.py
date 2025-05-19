import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class BudgetCommitmentLine(models.Model):
    _name = "budget.commitment.line"
    _description = "Budget Commitment Line"
    _inherit = ["analytic.distribution.mixin"]

    commitment_id = fields.Many2one(
        comodel_name="budget.commitment",
        string="Budget Commitment",
        required=True,
        readonly=True,
        index=True,
        auto_join=True,
        ondelete="cascade",
    )
    date = fields.Date(related="commitment_id.date")
    account_id = fields.Many2one(comodel_name="budget.template.line", store=True, compute="_compute_account_id")
    code = fields.Char("รหัสงบประมาณ", related="template_line_id.code", store=True)
    name = fields.Char("ชื่อรายการ", related="template_line_id.name", store=True)
    template_id = fields.Many2one(related="commitment_id.template_id", store=True)
    template_line_id = fields.Many2one(
        comodel_name="budget.template.line",
        index=True,
        domain="[('template_id', '=', template_id)]",
    )
    budget_type = fields.Selection(
        related="template_line_id.template_id.budget_type", store=True, readonly=True
    )
    amount = fields.Float(
        required=True,
        digits="Budget Precision",
        help="Amount",
        store=True,
        compute="_compute_amount_credit_debit"
    )
    credit = fields.Float(
        readonly=True,
        digits="Budget Precision",
        store=True,
        compute="_compute_amount_credit_debit"
    )
    debit = fields.Float(
        readonly=True,
        digits="Budget Precision",
        store=True,
        compute="_compute_amount_credit_debit"
    )
    company_id = fields.Many2one(related="commitment_id.company_id", store=True)
    note = fields.Text()

    # === Parent fields === #
    name = fields.Char(
        related="commitment_id.name", store=True, index="btree", readonly=True
    )
    date_range_fy_id = fields.Many2one(
        related="commitment_id.date_range_fy_id", store=True
    )
    parent_state = fields.Selection(related="commitment_id.state", store=True)
    source_analytic_id = fields.Many2one(
        related="commitment_id.source_analytic_id", store=True, readonly=True
    )
    department_analytic_id = fields.Many2one(
        related="commitment_id.department_analytic_id", store=True, readonly=True
    )

    @api.depends("amount")
    def _compute_amount_credit_debit(self):
        for record in self:
            if record.amount >= 0:
                record.debit = record.amount
                record.credit = 0
            else:
                record.credit = record.amount
                record.debit = 0

    @api.depends("template_line_id")
    def _compute_account_id(self):
        for record in self:
            record.account_id = record.template_line_id
