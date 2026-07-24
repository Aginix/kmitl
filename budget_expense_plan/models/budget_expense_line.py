# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .formula import validate_formula


class BudgetExpenseLine(models.Model):
    """Budget Line (รายการงบ) -- one plannable *column*, owned by a Template
    (ADR-0005). A label + its Category (one of the five expense roots of
    ``budget.account``) + an ``expr`` that curates the ``budget.account`` codes
    whose consume feeds the column. Living under the Template means duplicating
    the Template for a new fiscal year copies the budget lines too.
    """

    _name = "budget.expense.line"
    _description = "Expense Plan Budget Line (รายการงบ)"
    _order = "template_id, category_id, sequence, id"

    template_id = fields.Many2one(
        comodel_name="budget.expense.template",
        string="แม่แบบ",
        required=True,
        ondelete="cascade",
        index=True,
    )
    name = fields.Char(string="รายการงบ", required=True, translate=True)
    sequence = fields.Integer(default=10)
    category_id = fields.Many2one(
        comodel_name="budget.account",
        string="หมวดงบรายจ่าย",
        required=True,
        domain="[('parent_id', '=', False), ('budget_type', '=', 'expense')]",
        help="หมวดงบรายจ่าย 1 ใน 5 (ราก) เช่น 51000 งบบุคลากร, 52000 งบดำเนินงาน",
    )
    expr = fields.Char(
        string="สูตรดึงผลเบิกจ่าย",
        help=(
            "สูตรดึงผลเบิกจ่ายจริง อ้างอิงรหัสงบประมาณด้วย A['<รหัส>'] เช่น "
            "A['52400%'] (ทุกรหัสที่ขึ้นต้น 52400) หรือ "
            "A['5101010038'] + A['5101010040'] รองรับ + - * / และวงเล็บ"
        ),
    )
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(related="template_id.company_id", store=True)

    @api.constrains("expr")
    def _check_expr(self):
        """Reject an ``expr`` that does not compile / dry-run, so a typo
        surfaces at configuration time rather than blanking a figure."""
        for line in self:
            error = validate_formula(line.expr)
            if error:
                raise ValidationError(
                    _(
                        "สูตรของรายการงบ '%(name)s' ไม่ถูกต้อง:\n"
                        "    %(expr)s\n%(error)s",
                        name=line.name or "",
                        expr=line.expr or "",
                        error=error,
                    )
                )
