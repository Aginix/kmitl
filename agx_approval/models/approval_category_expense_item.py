from odoo import fields, models


class ApprovalCategoryExpenseItem(models.Model):
    """รายการค่าใช้จ่ายย่อย — a named kind of spending owned by one category,
    never shared across categories (ADR-0010). Retired by archiving: past
    requests name it. One ``is_other`` item per category stands for อื่น ๆ
    (the requester types what it is); it is managed by the category's
    ``allow_other_expense`` flag and hidden from the category's item list."""

    _name = "approval.category.expense.item"
    _description = "Approval Category Expense Item"
    _order = "is_other, sequence, id"

    name = fields.Char(string="ชื่อรายการ", required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    category_id = fields.Many2one(
        "approval.category",
        string="ประเภทค่าใช้จ่าย",
        required=True,
        ondelete="cascade",
        index=True,
    )
    is_other = fields.Boolean(
        string="อื่น ๆ (ระบุ)",
        readonly=True,
        help="รายการพิเศษ 'อื่น ๆ' ของประเภทนี้ — ผู้ขอพิมพ์ชื่อรายการเอง",
    )
