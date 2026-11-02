from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError


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

    # รายการค่าใช้จ่ายย่อย (ADR-0010): owned by this category, never shared.
    # Unticked, a request carries one Expense (a bare amount); ticked, the
    # requester itemizes against these items (and อื่น ๆ when allowed).
    has_expense_items = fields.Boolean(
        string="มีรายการค่าใช้จ่ายย่อย",
        default=False,
        help="ติ๊กเพื่อให้ผู้ขอแจกแจงค่าใช้จ่ายเป็นหลายบรรทัด โดยเลือกจากรายการ"
        "ค่าใช้จ่ายย่อยของประเภทนี้ — ถ้าไม่ติ๊ก ผู้ขอกรอกจำนวนเงินก้อนเดียว",
    )
    expense_item_ids = fields.One2many(
        "approval.category.expense.item",
        "category_id",
        string="รายการค่าใช้จ่ายย่อย",
        domain=[("is_other", "=", False)],
        context={"active_test": False},
    )
    allow_other_expense = fields.Boolean(
        string="อนุญาตรายการ อื่น ๆ (ระบุ)",
        default=True,
        help="ให้ผู้ขอเลือก 'อื่น ๆ' แล้วพิมพ์ชื่อรายการเองได้ เมื่อไม่มีในรายการ",
    )

    @api.constrains("has_expense_items", "allow_other_expense", "expense_item_ids")
    def _check_expense_items(self):
        for rec in self:
            if (
                rec.has_expense_items
                and not rec.allow_other_expense
                and not rec.expense_item_ids.filtered("active")
            ):
                raise ValidationError(
                    _(
                        "ประเภทค่าใช้จ่ายที่มีรายการค่าใช้จ่ายย่อย (%s) ต้องมีรายการ"
                        "อย่างน้อย 1 รายการ หรืออนุญาตรายการ อื่น ๆ"
                    )
                    % rec.name
                )

    def _other_expense_item(self):
        """The category's อื่น ๆ item, archived ones included."""
        self.ensure_one()
        return (
            self.env["approval.category.expense.item"]
            .with_context(active_test=False)
            .search([("category_id", "=", self.id), ("is_other", "=", True)], limit=1)
        )

    def _sync_other_expense_item(self):
        """Keep exactly one อื่น ๆ item per category, active only while the
        category itemizes and allows it."""
        for rec in self:
            wanted = rec.has_expense_items and rec.allow_other_expense
            item = rec._other_expense_item()
            if item:
                if item.active != wanted:
                    item.active = wanted
            elif wanted:
                item.create(
                    {
                        "name": _("อื่น ๆ"),
                        "category_id": rec.id,
                        "is_other": True,
                    }
                )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._sync_other_expense_item()
        return records

    def write(self, vals):
        res = super().write(vals)
        if {"has_expense_items", "allow_other_expense"} & set(vals):
            self._sync_other_expense_item()
        return res

    allowed_partner_type_ids = fields.Many2many(
        "res.partner.type",
        string="Allowed Partner Types",
        help="Partner types (ประเภทคู่ค้า) selectable as a participant "
        "(รายชื่อ) on requests of this category. Leave empty to allow any "
        "type.",
    )

    budget_account_id = fields.Many2one(
        "budget.account",
        string="Budget Account",
        domain=[
            ("budgetable", "=", True),
            ("budget_type", "=", "expense"),
            ("approval_ok", "=", True),
        ],
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
