# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .formula import validate_formula


class BudgetRevenueReportLine(models.Model):
    """A configured row (indicator) of the Budget-vs-Actual-Revenue report.

    The report is the flat, ``sequence``-ordered list of these rows. Each
    ``line``/``total`` row carries two free-text formulas -- a budget formula
    (``B[...]`` over revenue budget codes) and an actual formula (``A[...]``
    over GL income accounts) -- which the report compute evaluates per period.
    ``header`` rows are titles only and carry no formulas or figures. There is
    no parent-child nesting: a total row sums via its own formula (e.g.
    ``B['4%']``), not by aggregating other rows.
    """

    _name = "budget.revenue.report.line"
    _description = "Budget Revenue Comparison Report Line"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    name = fields.Char(string="ตัวชี้วัด", required=True, translate=True)
    row_type = fields.Selection(
        selection=[
            ("header", "หัวข้อ"),
            ("line", "รายการ"),
            ("total", "รวม"),
        ],
        string="ประเภทแถว",
        required=True,
        default="line",
        help=(
            "หัวข้อ = แถวชื่อกลุ่ม ไม่มีค่า; "
            "รายการ = แถวตัวชี้วัดปกติ มีสูตร; "
            "รวม = แถวผลรวม (เน้นตัวหนา) คำนวณจากสูตรของตัวเอง"
        ),
    )
    budget_formula = fields.Char(
        string="สูตรงบประมาณรายรับ",
        help=(
            "สูตรฝั่งงบประมาณ อ้างอิงรหัสงบประมาณรายรับด้วย B['<รหัส>'] เช่น "
            "B['41%'] (ทุกรหัสที่ขึ้นต้น 41) รองรับ + - * / และวงเล็บ"
        ),
    )
    actual_formula = fields.Char(
        string="สูตรรายรับจริง (CoA)",
        help=(
            "สูตรฝั่งบัญชี อ้างอิงผังบัญชีรายได้ด้วย A['<ตัวเลือก>'] เช่น "
            "A['income'] (ตาม account_type) หรือ A['41%'] (ตามรหัสบัญชี) "
            "รองรับ + - * / และวงเล็บ; ค่ารายรับเป็นบวกอัตโนมัติ"
        ),
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    active = fields.Boolean(default=True)

    @api.onchange("row_type")
    def _onchange_row_type_clear_formulas(self):
        """A header row carries no figures, so clear its formulas when the row
        is switched to ``header`` (mirrors the Odoo convention of clearing the
        inactive companion inputs of a mode selector)."""
        if self.row_type == "header":
            self.budget_formula = False
            self.actual_formula = False

    @api.constrains("row_type", "budget_formula", "actual_formula")
    def _check_formulas(self):
        """Reject formulas that do not compile / dry-run, so a typo surfaces at
        configuration time rather than blanking a figure on the report."""
        for line in self:
            if line.row_type == "header":
                continue
            for label, formula in (
                (_("budget formula"), line.budget_formula),
                (_("actual formula"), line.actual_formula),
            ):
                error = validate_formula(formula)
                if error:
                    raise ValidationError(
                        _(
                            "Invalid %(label)s on row '%(name)s':\n"
                            "    %(formula)s\n%(error)s",
                            label=label,
                            name=line.name or "",
                            formula=formula,
                            error=error,
                        )
                    )
