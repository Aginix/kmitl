# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .formula import validate_formula


class BudgetExpenseLine(models.Model):
    """Budget Line (รายการงบ) -- one plannable *column* of the expense plan.

    A label + its Category (one of the five expense roots of ``budget.account``)
    + an ``expr`` that curates the ``budget.account`` codes whose consume feeds
    the column. It is NOT a ``budget.account``; it references one or more codes
    through the ``A['<code>']`` formula so a single column can pool several
    codes (e.g. ค่าจ้างพนักงาน = A['5101010038'] + A['5101010040']).
    """

    _name = "budget.expense.line"
    _description = "Expense Plan Budget Line (รายการงบ)"
    _order = "category_id, sequence, id"

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
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

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
