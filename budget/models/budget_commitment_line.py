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
    )
    credit = fields.Float(
        readonly=True,
        digits="Budget Precision",
    )
    debit = fields.Float(
        readonly=True,
        digits="Budget Precision",
    )

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
    def _compute_amount(self):
        pass
