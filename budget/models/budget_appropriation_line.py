import logging

from odoo import api, fields, models
from odoo.osv import expression

_logger = logging.getLogger(__name__)


class BudgetAppropriationLine(models.Model):
    _name = "budget.appropriation.line"
    _description = "Budget Appropriation Line"
    _inherit = ["analytic.distribution.mixin", "mail.thread"]

    appropriation_id = fields.Many2one(
        comodel_name="budget.appropriation",
        string="Budget Appropriation",
        required=True,
        readonly=True,
        index=True,
        auto_join=True,
        ondelete="cascade",
    )
    code = fields.Char("รหัสงบประมาณ", related="template_line_id.code", store=True)
    name = fields.Char("ชื่อรายการ", related="template_line_id.name", store=True)
    template_id = fields.Many2one(
        related="appropriation_id.template_id", store=True, readonly=True
    )
    template_line_id = fields.Many2one(
        comodel_name="budget.template.line",
        index=True,
        domain=[("budgetable", "=", True)]
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
    note = fields.Char(tracking=True)

    # === Parent fields === #
    department_analytic_id = fields.Many2one(
        related="appropriation_id.department_analytic_id",
        store=True,
        readonly=True,
        string="ส่วนงาน",
    )
    name = fields.Char(
        related="appropriation_id.name", store=True, index="btree", readonly=True
    )
    date_range_fy_id = fields.Many2one(
        related="appropriation_id.date_range_fy_id", store=True
    )
    parent_state = fields.Selection(related="appropriation_id.state", store=True)
    source_analytic_id = fields.Many2one(
        related="appropriation_id.source_analytic_id", store=True
    )

    @api.depends("amount")
    def _compute_amount(self):
        pass
