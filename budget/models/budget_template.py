import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.osv import expression

_logger = logging.getLogger(__name__)


class BudgetTemplate(models.Model):
    _name = "budget.template"
    _description = "Budget Template"

    name = fields.Char()
    date_range_fy_id = fields.Many2one(
        comodel_name="account.fiscal.year",
        string="Fiscal year",
        search="_search_date_range_fy",
    )
    note = fields.Text("Internal Notes", tracking=True)
    budget_type = fields.Selection(
        [("revenue", "Revenue"), ("expense", "Expense")],
        required=True,
        default="expense",
    )
    line_ids = fields.One2many(
        comodel_name="budget.template.line",
        inverse_name="template_id",
    )

    @api.model
    def _search_date_range_fy(self, operator, value):
        if operator in ("=", "!=", "in", "not in"):
            date_range_domain = [("id", operator, value)]
        else:
            date_range_domain = [("name", operator, value)]

        date_ranges = self.env["account.fiscal.year"].search(date_range_domain)

        domain = [("id", "=", -1)]
        for date_range in date_ranges:
            domain = expression.OR(
                [
                    domain,
                    [
                        "&",
                        ("date", ">=", date_range.date_from),
                        ("date", "<=", date_range.date_to),
                        "|",
                        ("company_id", "=", False),
                        ("company_id", "=", date_range.company_id.id),
                    ],
                ]
            )
        return domain


class BudgetTemplateLine(models.Model):
    _name = "budget.template.line"
    _description = "Budget Template Lines"
    _parent_store = True
    _order = "sequence"

    template_id = fields.Many2one(
        comodel_name="budget.template",
        index=True,
        ondelete="cascade",
        readonly=True,
    )

    def _default_sequence(self):
        """
        TODO: จะต้องแก้ให้ดึงค่า sequence จากเฉพาะกลุ่ม parent_id ของตัวเองเท่านั้น
        """
        return (self.search([], order="sequence desc", limit=1).sequence or 0) + 1

    code = fields.Char("รหัสงบประมาณ", required=True, tracking=True, copy=False)
    name = fields.Char("ชื่อรายการ", required=True, tracking=True)
    sequence = fields.Integer(default=_default_sequence)

    parent_id = fields.Many2one(
        "budget.template.line", string="Parent", index=True, ondelete="cascade"
    )
    child_ids = fields.One2many("budget.template.line", "parent_id", string="Childs")
    parent_path = fields.Char(index=True, unaccent=False)
    budget_type = fields.Selection(
        related="template_id.budget_type", readonly=True, store=True
    )

    _sql_constraints = [
        (
            "unique_budget_template_line",
            "unique (template_id, code)",
            _("Budget indicator must be unique"),
        )
    ]

    @api.constrains("parent_id")
    def _check_parent_id(self):
        if not self._check_recursion():
            raise ValidationError(
                _("You cannot create recursive budget template line.")
            )
