from odoo import api, fields, models, tools, _


class ApprovalCategory(models.Model):

    _name = "approval.category"
    _description = "Approval Category"

    name = fields.Char(
        string="Name",
        required=True
    )

    image = fields.Binary(
        string="Image"
    )

    group_id = fields.Many2one(
        string="Request Group",
        comodel_name="approval.category.group",
        required=True
    )

    active = fields.Boolean(
        string="Active",
        default=True
    )

    sequence = fields.Integer(
        string="Sequence"
    )

    default_description = fields.Text(
        string="Default Description",
        default=False,
    )

    has_period = fields.Boolean(
        string="Has Period",
        default=False,
        required=True
    )

    has_city = fields.Boolean(
        string="Has City",
        default=False,
        required=True
    )

    has_country_id = fields.Boolean(
        string="Has Country",
        default=False,
        required=True
    )

    allowed_product_ids = fields.Many2many(
        string="Allowed Expenses",
        comodel_name="product.product",
    )

    allow_internal_partner = fields.Boolean(
        string="Allow Internal Personnel",
        help="Allow selecting internal personnel (บุคลากรภายใน) as the payee "
        "on request lines of this category.",
    )

    allow_external_partner = fields.Boolean(
        string="Allow External Person",
        help="Allow selecting external persons (บุคคลภายนอก) — companies and "
        "others — as the payee on request lines of this category.",
    )

    allow_student_partner = fields.Boolean(
        string="Allow Student",
        help="Allow selecting students (นักศึกษา) as the payee on request "
        "lines of this category.",
    )

    budget_account_id = fields.Many2one(
        "budget.account",
        string="Budget Account",
        domain=[("budgetable", "=", True), ("budget_type", "=", "expense")],
    )

    activity_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="กิจกรรม",
        domain=[("root_plan_id.code", "=", "activities")],
    )

    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="ส่วนงาน",
        domain=[("root_plan_id.code", "=", "departments")],
    )

    fund_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="กองทุน",
        domain=[("root_plan_id.code", "=", "funds")],
    )

    source_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="แหล่งเงิน",
        domain=[("root_plan_id.code", "=", "sources")],
    )

    def create_request(self):
        self.ensure_one()
        # If category uses sequence, set next sequence as name
        # (if not, set category name as default name).
        return {
            "type": "ir.actions.act_window",
            "res_model": "approval.request",
            "views": [[False, "form"]],
            "context": {
                'form_view_initial_mode': 'edit',
                'default_category_id': self.id,
            },
        }
